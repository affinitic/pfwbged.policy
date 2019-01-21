from Products.CMFCore.utils import getToolByName
from plone import api


def update_role_mappings(context):
    wf_tool = getToolByName(context, 'portal_workflow')
    wf_tool.updateRoleMappings()


def publish_document_subfolders(context):
    portal = api.portal.get()
    if 'documents' in portal:
        portal_catalog = api.portal.get_tool('portal_catalog')
        folder_path = '/'.join(portal['documents'].getPhysicalPath())
        query = {'path': {
            'query': folder_path},
            'review_state': 'private'}
        results = portal_catalog.searchResults(query)
        for brain in results:
            subfolder = brain.getObject()
            api.content.transition(
                obj=subfolder,
                transition="publish"
            )
