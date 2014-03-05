from five import grok
from zope.interface import Interface

from plone import api

from Products.CMFCore.utils import getToolByName

from ..interfaces import IFoldersFolder

class FoldersView(grok.View):
    grok.context(IFoldersFolder)
    grok.name('edm_folder_listing')
    grok.require('zope2.View')

    template = grok.PageTemplateFile('templates/folders_view.pt')

    def document_types(self):
        return 'pfwbgedfolder'
