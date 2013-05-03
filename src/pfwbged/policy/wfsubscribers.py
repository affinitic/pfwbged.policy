import datetime

from Acquisition import aq_chain, aq_parent

from five import grok

from zope.container.interfaces import INameChooser
from zope.i18n import translate
from zope.lifecycleevent.interfaces import IObjectCreatedEvent
from zope.interface import alsoProvides

from plone import api

from Products.DCWorkflow.interfaces import IAfterTransitionEvent

from collective.dms.mailcontent.dmsmail import IDmsIncomingMail,\
    IDmsOutgoingMail
from collective.dms.basecontent.dmsfile import IDmsFile
from collective.task.content.task import ITask

from pfwbged.policy import _
from pfwbged.policy.interfaces import IIncomingMailAttributed


@grok.subscribe(IDmsIncomingMail, IAfterTransitionEvent)
def incoming_mail_attributed(context, event):
    """Launched when a mail is attributed to some groups or users"""
    if event.transition is not None and event.transition.id == 'to_process':
        already_in_charge = []
        for task in context.objectValues('task'):
            already_in_charge.extend(task.responsible)
        treating_groups = set(context.treating_groups) - set(already_in_charge)
        # create a task for each group which has not already a task for this mail
        chooser = INameChooser(context)
        deadline = datetime.date.today() + datetime.timedelta(days=context.deadline)
        for group_name in treating_groups:
            params = {'responsible': [group_name],
                      'title': translate(_(u'Process mail'),
                                         context=context.REQUEST),
                      'deadline': deadline,
                      }
            newid = chooser.chooseName('process-mail', context)
            context.invokeFactory('task', newid, **params)
            task = context[newid]
            alsoProvides(task, IIncomingMailAttributed)
            #datamanager = LocalRolesToPrincipalsDataManager(task, ITask['responsible'])
            #datamanager.set((group_name,))
            # manually sets Editor role to responsible user or group :-(
            task.manage_addLocalRoles(group_name, ['Editor',])
            task.reindexObjectSecurity()


@grok.subscribe(IDmsOutgoingMail, IObjectCreatedEvent)
def outgoing_mail_created(context, event):
    """Set Editor role on the mail to the creator of the outgoing mail"""
    creator = api.user.get_current()
    api.user.grant_roles(user=creator, roles=['Editor'], obj=context)


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
            if api.content.get_state(obj=version) == 'validated':
                api.content.transition(obj=version, transition='obsolete')


@grok.subscribe(IDmsOutgoingMail, IAfterTransitionEvent)
def outgoingmail_sent(context, event):
    """Launched when outgoing mail is sent.
    Mark as done task from incoming mail.
    """
    if event.new_state.id == 'sent':
        portal_catalog = api.portal.get_tool('portal_catalog')
        if not context.in_reply_to:
            return

        incomingmail = context.in_reply_to[0].to_object
        if incomingmail.portal_type != 'dmsincomingmail':
            return

        tasks = portal_catalog.searchResults(portal_type='task',
                path='/'.join(incomingmail.getPhysicalPath()),
                object_provides=IIncomingMailAttributed.__identifier__
                )
        for task_brain in tasks:
            task = task_brain.getObject()
            if api.content.get_state(obj=task) == 'in-progress':
                api.content.transition(obj=task, transition='mark-as-done')


@grok.subscribe(ITask, IAfterTransitionEvent)
def task_done(context, event):
    """Launched when task is done.
    Mark as answered incoming mail.
    """
    if event.new_state.id == 'done':
        first_task = context
        for obj in aq_chain(context):
            obj = aq_parent(obj)
            if IDmsIncomingMail.providedBy(obj):
                break

            first_task = obj

        if (not IDmsIncomingMail.providedBy(obj) or
            not IIncomingMailAttributed.providedBy(first_task)):
            return

        incomingmail = obj
        if api.content.get_state(obj=incomingmail) == 'processing':
            api.content.transition(obj=incomingmail, transition='answer')
