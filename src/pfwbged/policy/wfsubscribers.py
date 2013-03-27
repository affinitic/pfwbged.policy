from five import grok

from zope.container.interfaces import INameChooser
from plone import api

from Products.DCWorkflow.interfaces import IAfterTransitionEvent

from collective.dms.mailcontent.dmsmail import IDmsIncomingMail


@grok.subscribe(IDmsIncomingMail, IAfterTransitionEvent)
def incoming_mail_attributed(context, event):
    """Launched when a mail is attributed to some groups or users"""
    if event.transition is not None and event.transition.id == 'to_process':
        already_in_charge = [task.responsible for task in context.objectValues('task')]
        treating_groups = set(context.treating_groups) - set(already_in_charge)
        # create a task for each group which has not already a task for this mail
        chooser = INameChooser(context)
        for group_name in treating_groups:
            params = {'responsible': [group_name], 'title': 'Process mail',}
            newid = chooser.chooseName('process-mail', context)
            context.invokeFactory('task', newid, **params)

