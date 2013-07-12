from Acquisition import aq_parent

from five import grok

from plone import api

from collective.dms.mailcontent.dmsmail import IDmsIncomingMail
from collective.task.content.task import ITask


class NoIDmsIncomingMailFound(Exception):
    """No IDmsIncomingMail found"""


class CreateOutgoingMail(grok.View):

    grok.name("create_outgoing_mail")
    grok.context(ITask)
    grok.require("zope2.View")

    def find_incomingmail(self):
        """Find the first IDmsIncomingMail in the acquisition chain"""
        parent = self.context
        while not IDmsIncomingMail.providedBy(parent):
            parent = aq_parent(parent)
            if parent is None:
                raise NoIDmsIncomingMailFound
        return parent

    def render(self):
        task = self.context
        incomingmail = self.find_incomingmail()
        container_path = '/'.join(incomingmail.getPhysicalPath())
        catalog = api.portal.get_tool("portal_catalog")
        brains = catalog.searchResults({"portal_type": "task",
                                        "path": container_path,
                                        "review_state": "in-progress"})

        values = {}
        values['title'] = "Re: " + incomingmail.title
        values['recipients'] = '/'.join(incomingmail.sender.to_object.getPhysicalPath())
        values['in_reply_to'] = '/'.join(incomingmail.getPhysicalPath())
        values['treating_groups'] = task.responsible[0]
        values['related_task'] = task.getId()
        values_url = """
form.widgets.IDublinCore.title=%(title)s&
form.widgets.recipients:list=%(recipients)s&
form.widgets.in_reply_to:list=%(in_reply_to)s&
form.widgets.IRelatedTask.related_task=%(related_task)s&
form.widgets.treating_groups=%(treating_groups)s""" % values
        folder_url = incomingmail.getParentNode().absolute_url()
        url = folder_url+"/++add++dmsoutgoingmail?"+values_url
        self.request.response.redirect(url)
