import datetime

from Acquisition import aq_chain, aq_parent

from five import grok

from zope.container.interfaces import INameChooser
from zope.i18n import translate
from zope.lifecycleevent.interfaces import IObjectCreatedEvent,\
    IObjectModifiedEvent
from zope.interface import alsoProvides

from plone import api

from Products.DCWorkflow.interfaces import IAfterTransitionEvent

from collective.dms.mailcontent.dmsmail import IDmsIncomingMail,\
    IDmsOutgoingMail
from collective.dms.basecontent.dmsfile import IDmsFile
from collective.task.content.task import ITask
from collective.z3cform.rolefield.field import LocalRolesToPrincipalsDataManager

from pfwbged.policy import _
from pfwbged.policy.interfaces import IIncomingMailAttributed


def create_tasks(container, groups, deadline):
    """Create 'process mail' tasks for a list of groups or users"""
    chooser = INameChooser(container)
    for group_name in groups:
        params = {'responsible': [],
                  'title': translate(_(u'Process mail'),
                                     context=container.REQUEST),
                  'deadline': deadline,
                  }
        newid = chooser.chooseName('process-mail', container)
        container.invokeFactory('task', newid, **params)
        task = container[newid]
        alsoProvides(task, IIncomingMailAttributed)
        datamanager = LocalRolesToPrincipalsDataManager(task, ITask['responsible'])
        datamanager.set((group_name,))


def get_tasks(obj):
    """Get all "first level" tasks related to obj"""
    catalog = api.portal.get_tool('portal_catalog')
    container_path = '/'.join(obj.getPhysicalPath())
    tasks = catalog.searchResults({'path': {'query': container_path},
                                   'portal_type': 'task'})
    return tasks


@grok.subscribe(IDmsIncomingMail, IAfterTransitionEvent)
def incoming_mail_attributed(context, event):
    """Launched when a mail is attributed to some groups or users"""
    if event.transition is not None and event.transition.id == 'to_process':
        # first, copy treated_by and in_copy into treating_groups and recipient_groups
        treating_groups = list(frozenset(context.treating_groups + context.treated_by))
        treating_dm = LocalRolesToPrincipalsDataManager(context, IDmsIncomingMail['treating_groups'])
        treating_dm.set(treating_groups)
        recipient_groups = list(frozenset(context.recipient_groups + context.in_copy))
        recipient_dm = LocalRolesToPrincipalsDataManager(context, IDmsIncomingMail['recipient_groups'])
        recipient_dm.set(recipient_groups)

        already_in_charge = []
        for task in context.objectValues('task'):
            already_in_charge.extend(task.responsible)
        new_treating_groups = frozenset(context.treating_groups) - frozenset(already_in_charge)
        # create a task for each group which has not already a task for this mail
        create_tasks(context, new_treating_groups, context.deadline)


@grok.subscribe(IDmsIncomingMail, IObjectModifiedEvent)
def incoming_mail_modified(context, event):
    current_state = api.content.get_state(context)
    if current_state not in ['registering', 'assigning', 'noaction']:
        new_treating = frozenset(context.treated_by) - frozenset(context.treating_groups)
        treating_groups = context.treating_groups + list(new_treating)
        treating_dm = LocalRolesToPrincipalsDataManager(context, IDmsIncomingMail['treating_groups'])
        treating_dm.set(treating_groups)
        new_recipients = frozenset(context.in_copy) - frozenset(context.recipient_groups)
        recipient_groups = context.recipient_groups + list(new_recipients)
        recipient_dm = LocalRolesToPrincipalsDataManager(context, IDmsIncomingMail['recipient_groups'])
        recipient_dm.set(recipient_groups)
        create_tasks(context, new_treating, context.deadline)


@grok.subscribe(IDmsOutgoingMail, IObjectCreatedEvent)
def outgoing_mail_created(context, event):
    """Set Editor role on the mail to the creator of the outgoing mail"""
    creator = api.user.get_current()
    api.user.grant_roles(user=creator, roles=['Editor'], obj=context)


@grok.subscribe(IDmsOutgoingMail, IAfterTransitionEvent)
def outgoingmail_sent(context, event):
    """Launched when outgoing mail is sent.
    Mark as done task from incoming mail.
    """
    if event.new_state.id == 'sent':
        if not context.in_reply_to:
            return

        incomingmail = context.in_reply_to[0].to_object
        if incomingmail.portal_type != 'dmsincomingmail':
            return

        if context.related_task is not None:
            for ref in context.related_task:
                task = ref.to_object
                if api.content.get_state(obj=task) == 'in-progress':
                    api.content.transition(obj=task, transition='mark-as-done')


@grok.subscribe(IDmsFile, IAfterTransitionEvent)
def version_note_finished(context, event):
    """Launched when version note is finished"""
    if event.new_state.id == 'finished':
        context.reindexObject(idxs=['review_state'])
        portal_catalog = api.portal.get_tool('portal_catalog')
        document = context.getParentNode()
        # if parent is an outgoing mail, change its state to ready_to_send
        if document.portal_type == 'dmsoutgoingmail' and api.content.get_state(obj=document) == 'writing':
            api.content.transition(obj=document, transition='finish')
        version_notes = portal_catalog.searchResults(portal_type='dmsmainfile',
                path='/'.join(document.getPhysicalPath()))
        # make obsolete other versions
        for version_brain in version_notes:
            version = version_brain.getObject()
            if api.content.get_state(obj=version) in ('draft', 'pending', 'validated'):
                api.content.transition(obj=version, transition='obsolete')


@grok.subscribe(ITask, IAfterTransitionEvent)
def task_done(context, event):
    """Launched when task is done or abandoned.
    Mark incoming mail as answered if all related tasks are done or abandoned
    (a task has to be done at least).
    """
    if event.new_state.id in ['abandoned', 'done']:
        first_task = context
        # go up in the acquisition chain to find the first task (i.e. the one which is just below the incoming mail)
        for obj in aq_chain(context):
            obj = aq_parent(obj)
            if IDmsIncomingMail.providedBy(obj):
                break
            first_task = obj

        if (not IDmsIncomingMail.providedBy(obj) or
            not IIncomingMailAttributed.providedBy(first_task)):
            return

        incomingmail = obj

        # the mail is marked as answered only if all tasks are done or abandoned and one task is done
        one_task_done = False
        tasks = get_tasks(incomingmail)
        for brain in tasks:
            task = brain.getObject()
            state = api.content.get_state(task)
            if state not in ('abandoned', 'done'):
                return
            elif state == 'done':
                one_task_done = True

        if one_task_done and api.content.get_state(obj=incomingmail) == 'processing':
            api.content.transition(obj=incomingmail, transition='answer')
