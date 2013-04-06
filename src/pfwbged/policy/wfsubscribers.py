import datetime

from five import grok

from zope.container.interfaces import INameChooser
from plone import api

from Products.DCWorkflow.interfaces import IAfterTransitionEvent

from collective.dms.mailcontent.dmsmail import IDmsIncomingMail,\
    IDmsOutgoingMail
from zope.lifecycleevent.interfaces import IObjectCreatedEvent
from collective.dms.basecontent.dmsfile import IDmsFile

from pfwbged.policy import _


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
                      'title': _(u'Process mail'),
                      'deadline': deadline,
                      }
            newid = chooser.chooseName('process-mail', context)
            context.invokeFactory('task', newid, **params)
            task = context[newid]
            #datamanager = LocalRolesToPrincipalsDataManager(task, ITask['responsible'])
            #datamanager.set((group_name,))
            # manually sets Editor role to responsible user or group :-(
            task.manage_setLocalRoles(group_name, ['Editor',])


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
        version_notes = portal_catalog.searchResults(portal_type='dmsmainfile')
        # make obsolete other versions
        for version_brain in version_notes:
            version = version_brain.getObject()
            if api.content.get_state(obj=version) == 'validated':
                api.content.transition(obj=version, transition='obsolete')
