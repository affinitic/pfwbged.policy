from Acquisition import aq_chain, aq_parent

from five import grok

from zope.container.interfaces import INameChooser
from zope.i18n import translate
from zope.lifecycleevent.interfaces import IObjectAddedEvent
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
from pfwbged.basecontent.behaviors import IPfwbIncomingMail


def create_tasks(container, groups, deadline, note=""):
    """Create 'process mail' tasks for a list of groups or users.
    """
    chooser = INameChooser(container)
    for group_name in groups:
        params = {'responsible': [],
                  'title': translate(_(u'Process mail'),
                                     context=container.REQUEST),
                  'deadline': deadline,
                  'note': note,
                  }
        newid = chooser.chooseName('process-mail', container)
        container.invokeFactory('task', newid, **params)
        task = container[newid]
        alsoProvides(task, IIncomingMailAttributed)
        datamanager = LocalRolesToPrincipalsDataManager(task, ITask['responsible'])
        datamanager.set((group_name,))
        task.reindexObject()


def get_tasks(obj):
    """Get all "first level" tasks related to obj.
    """
    catalog = api.portal.get_tool('portal_catalog')
    container_path = '/'.join(obj.getPhysicalPath())
    tasks = catalog.searchResults({'path': {'query': container_path},
                                   'portal_type': 'task'})
    return tasks


def incoming_mail_attributed(context, comment):
    """Launched when a mail is attributed to some groups or users.
    """
    # first, copy treated_by and in_copy into treating_groups and recipient_groups
    treating_groups = list(frozenset((context.treating_groups or []) + (context.treated_by or [])))
    treating_dm = LocalRolesToPrincipalsDataManager(context, IDmsIncomingMail['treating_groups'])
    treating_dm.set(treating_groups)
    recipient_groups = list(frozenset((context.recipient_groups or []) + (context.in_copy or [])))
    recipient_dm = LocalRolesToPrincipalsDataManager(context, IDmsIncomingMail['recipient_groups'])
    recipient_dm.set(recipient_groups)
    context.reindexObjectSecurity()

    already_in_charge = []
    for task in context.objectValues('task'):
        already_in_charge.extend(task.responsible)
    new_treating_groups = frozenset(context.treating_groups or []) - frozenset(already_in_charge)
    # create a task for each group which has not already a task for this mail
    create_tasks(context, new_treating_groups, context.deadline, comment)

#
#@grok.subscribe(IPfwbIncomingMail, IObjectModifiedEvent)
#def incoming_mail_modified(context, event):
#    current_state = api.content.get_state(context)
#    if current_state not in ['registering', 'assigning', 'noaction']:
#        new_treating = frozenset(context.treated_by) - frozenset(context.treating_groups)
#        treating_groups = list(context.treating_groups) + list(new_treating)
#        treating_dm = LocalRolesToPrincipalsDataManager(context, IDmsIncomingMail['treating_groups'])
#        treating_dm.set(treating_groups)
#        new_recipients = frozenset(context.in_copy) - frozenset(context.recipient_groups)
#        recipient_groups = list(context.recipient_groups) + list(new_recipients)
#        recipient_dm = LocalRolesToPrincipalsDataManager(context, IDmsIncomingMail['recipient_groups'])
#        recipient_dm.set(recipient_groups)
#        context.reindexObjectSecurity()
#        create_tasks(context, new_treating, context.deadline)


@grok.subscribe(IDmsOutgoingMail, IObjectAddedEvent)
def outgoing_mail_created(context, event):
    """Set Editor role on the outgoing mail to its creator.
    """
    creator = api.user.get_current()
    api.user.grant_roles(user=creator, roles=['Editor'], obj=context)
    context.reindexObjectSecurity()


@grok.subscribe(IDmsIncomingMail, IObjectAddedEvent)
def incoming_mail_created(context, event):
    """Set Owner role on the incoming mail to its creator.
    """
    creator = api.user.get_current()
    api.user.grant_roles(user=creator, roles=['Owner'], obj=context)
    context.reindexObjectSecurity()


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
                    task.reindexObject(idxs=['review_state'])


@grok.subscribe(IDmsFile, IObjectAddedEvent)
def incoming_version_added(context, event):
    """A new version in an incoming mail is automatically finished.
    """
    if IDmsIncomingMail.providedBy(context.getParentNode()):
        api.content.transition(context, 'finish_without_validation')
        context.reindexObject(idxs=['review_state'])
        context.incomingmail = True
        context.__ac_local_roles_block__ = False
        context.reindexObjectSecurity()


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

        if one_task_done and api.content.get_state(obj=incomingmail) == 'processing' \
            and incomingmail.restrictedTraverse('@@can_answer')():
                api.content.transition(obj=incomingmail, transition='answer')
                incomingmail.reindexObject(idxs=['review_state'])
