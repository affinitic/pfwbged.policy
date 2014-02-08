from five import grok
from zope.interface import Interface

from plone import api

from Products.CMFCore.utils import getToolByName

from ..interfaces import IDocumentsFolder
from ..interfaces import ISubpoolFolder

class DocumentsView(grok.View):
    grok.context(IDocumentsFolder)
    grok.name('edm_folder_listing')
    grok.require('zope2.View')

    template = grok.PageTemplateFile('templates/documents_view.pt')

    def document_types(self):
        portal = api.portal.get()
        typesTool = getToolByName(portal, 'portal_types')
        fti = typesTool.getTypeInfo('pfwbgedfolder')
        return ';'.join([x for x in fti.allowed_content_types if x not in ('pfwbgedfolder', 'pfwbgedlink',)])



class SubpoolView(grok.View):
    grok.context(ISubpoolFolder)
    grok.name('edm_folder_listing')
    grok.require('zope2.View')

    def __call__(self):
        new_url = self.context.absolute_url() + '/../'
        self.context.REQUEST.response.redirect(new_url, lock=True)

    def render(self):
        return self()
