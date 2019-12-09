from Products.CMFCore.utils import getToolByName
from pfwbged.policy.setuphandlers import setup_constrains
from plone import api


def refresh_documents_addable_types(context):
    context.runImportStepFromProfile('profile-pfwbged.basecontent:default',
                                     'typeinfo')
    context.runImportStepFromProfile('profile-pfwbged.folder:default',
                                     'typeinfo')
    context.runImportStepFromProfile('profile-pfwbged.policy:default',
                                     'workflow')

    portal = api.portal.get()
    types_tool = getToolByName(portal, 'portal_types')
    fti = types_tool.getTypeInfo('pfwbgedfolder')
    setup_constrains(
        portal['documents'],
        [
            x for x in fti.allowed_content_types
            if x not in ('pfwbgedfolder', 'pfwbgedlink',)
        ]
    )
