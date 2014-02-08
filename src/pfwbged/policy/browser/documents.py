from five import grok
from zope.interface import Interface

from plone import api

from Products.CMFCore.utils import getToolByName

from ..interfaces import IDocumentsFolder

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
