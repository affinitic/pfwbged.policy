from Products.CMFCore.utils import getToolByName
from pfwbged.policy.setuphandlers import setup_constrains
from plone import api


def setup_constrains_on_documents_folder():
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


def refresh_documents_addable_types(context):
    context.runImportStepFromProfile('profile-pfwbged.basecontent:default',
                                     'typeinfo')
    context.runImportStepFromProfile('profile-pfwbged.folder:default',
                                     'typeinfo')
    context.runImportStepFromProfile('profile-pfwbged.policy:default',
                                     'workflow')

    setup_constrains_on_documents_folder()


def remove_apf_content_types(context):
    context.runImportStepFromProfile('profile-pfwbged.basecontent:default',
                                     'typeinfo')
    context.runImportStepFromProfile('profile-pfwbged.folder:default',
                                     'typeinfo')
    context.runImportStepFromProfile('profile-pfwbged.policy:default',
                                     'workflow')
    context.runImportStepFromProfile('profile-pfwbged.policy:default',
                                     'rolemap')

    setup_constrains_on_documents_folder()
