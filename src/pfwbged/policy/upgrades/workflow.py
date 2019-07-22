from Acquisition import aq_base
from Persistence import PersistentMapping
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
            subfolder.reindexObject(idxs=['review_state'])


def overrideStatusOf(wf_id, ob, old_status, new_status):
    """Update a particular status in an object's workflow history,
       e.g. dict returned by wf_tool.getStatusOf.
       Derived from wf_tool.setStatusOf."""
    wfh = None
    has_history = 0
    if hasattr(aq_base(ob), 'workflow_history'):
        history = ob.workflow_history
        if history is not None:
            has_history = 1
            wfh = history.get(wf_id, None)
            if wfh is not None:
                wfh = list(wfh)
    if not wfh:
        wfh = []
    if old_status in wfh:
        position = wfh.index(old_status)
        wfh[position] = new_status
    if not has_history:
        ob.workflow_history = PersistentMapping()
    ob.workflow_history[wf_id] = tuple(wfh)


def update_refused_version_state(context):
    """Set refused versions to refused state (instead of draft)."""
    portal = api.portal.get()
    if 'documents' in portal:
        portal_catalog = api.portal.get_tool('portal_catalog')
        portal_workflow = api.portal.get_tool('portal_workflow')
        wf_id = portal_workflow.getChainFor('dmsmainfile')[0]
        wf_def = portal_workflow.getWorkflowById(wf_id)

        folder_path = '/'.join(portal['documents'].getPhysicalPath())
        query = {'path': {
            'query': folder_path},
            'portal_type': 'dmsmainfile',
            'review_state': 'draft'}
        results = portal_catalog.unrestrictedSearchResults(query)
        for brain in results:
            version = brain.getObject()
            old_state = portal_workflow.getStatusOf(wf_id, version)
            if old_state and old_state.get('action') == 'refuse':
                new_state = old_state.copy()
                new_state.update({'review_state': 'refused'})
                overrideStatusOf(wf_id, version, old_state, new_state)
                wf_def.updateRoleMappingsFor(version)
                version.reindexObject(idxs=['allowedRolesAndUsers', 'review_state'])


def refresh_workflow_permissions(context, workflow_id):
    portal_workflow = api.portal.get_tool('portal_workflow')
    portal_catalog = api.portal.get_tool('portal_catalog')
    workflow = portal_workflow.getWorkflowById(workflow_id)
    portal = api.portal.get()
    folder_path = '/'.join(portal['documents'].getPhysicalPath())

    for dx_type, wf_ids in portal_workflow._chains_by_type.items():
        if workflow_id in wf_ids:
            query = {'path': {
                'query': folder_path},
                'portal_type': dx_type}
            results = portal_catalog.unrestrictedSearchResults(query)
            for brain in results:
                obj = brain.getObject()
                workflow.updateRoleMappingsFor(obj)
                obj.reindexObjectSecurity()
                obj.reindexObject(idxs=['allowedRolesAndUsers'])


def incomingmail_deletion_permissions(context):
    refresh_workflow_permissions(context, "incomingmail_workflow")
