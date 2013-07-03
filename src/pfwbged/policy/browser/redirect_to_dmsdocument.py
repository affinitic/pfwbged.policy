from five import grok
from Acquisition import aq_parent

from plone import api

from Products.CMFCore.interfaces import IContentish

from collective.dms.basecontent.dmsdocument import IDmsDocument


class NoDmsDocumentFound(Exception):
    """No DmsDocument found"""


class RedirectToDmsDocument(grok.View):
    """View that redirect to the document
    Make transition before redirection if workflow_action in request
    """
    grok.name('redirect_to_dmsdocument')
    grok.context(IContentish)
    grok.require("zope2.View")

    def find_document(self):
        """Find the first IDmsDocument in the acquisition chain"""
        parent = self.context
        while not IDmsDocument.providedBy(parent):
            parent = aq_parent(parent)
            if parent is None:
                raise NoDmsDocumentFound
        return parent

    def render(self):
        transition = self.request.get('workflow_action')
        if transition is not None:
            api.content.transition(self.context, transition)
        try:
            document = self.find_document()
            self.request.response.redirect(document.absolute_url())
        except NoDmsDocumentFound:
            self.request.response.redirect(self.context.absolute_url())
        return ""
