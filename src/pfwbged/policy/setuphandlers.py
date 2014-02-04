# -*- coding: utf-8 -*-
import os
from zope.interface import alsoProvides

from plone import api
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.interfaces.constrains import ISelectableConstrainTypes
from plone.app.dexterity.behaviors import constrains
from plone.dexterity.interfaces import IDexterityContainer

from eea.facetednavigation.interfaces import (
    IFacetedNavigable,
    IDisableSmartFacets,
    IHidePloneLeftColumn,
    IHidePloneRightColumn)


def isNotCurrentProfile(context):
    return context.readDataFile("pfwbgedpolicy_marker.txt") is None


def setup_constrains(container, allowed_types):
    behavior = ISelectableConstrainTypes(container)
    behavior.setConstrainTypesMode(constrains.ENABLED)
    behavior.setImmediatelyAddableTypes(allowed_types)
    return True


def get_collection_query(type, role):
    """Return query to build collection for a given type and role"""
    mapping = {'information': {'enquirer': [u'todo', u'done'],
                               'responsible': [u'todo', u'done']},
               'opinion': {'enquirer': [u'todo', u'done'],
                           'responsible': [u'todo', u'done']},
               'task': {'enquirer': [u'abandoned', u'attributed', u'done',
                                     u'in-progress', u'refusal-requested', u'todo'],
                        'responsible': [u'abandoned', u'attributed', u'done',
                                        u'in-progress', u'refusal-requested', u'todo'],},
               'validation': {'enquirer': [u'todo', u'validated', u'refused'],
                              'responsible': [u'todo', u'validated', u'refused'],},
               }
    return [{u'i': u'portal_type',
              u'o': u'plone.app.querystring.operation.selection.is',
              u'v': [type]},
             {u'i': u'review_state',
              u'o': u'plone.app.querystring.operation.selection.is',
              u'v': mapping[type][role]},
             {u'i': role,
              u'o': u'plone.app.querystring.operation.string.currentUser',
              },
            ]


def create_tasks_collections(context):
    """Create collections for tasks, informations, validations, opinions"""
    # parameters that are the same for all types of 'tasks'
    sort_on = u'deadline'
    sort_reversed = True
    limit = 200
    item_count = 20
    portal = api.portal.get()
    container = portal.Members
    # tasks
    type = u'task'
    role = u'enquirer'
    id = '%s-%s' % (type, role)
    if id not in container:
        query = get_collection_query(type, role)
        collection = api.content.create(container=container,
                           type="pfwbgedcollection",
                           id=id,
                           title=u"Tâches que j'ai demandées",
                           sort_on=sort_on,
                           sort_reversed=sort_reversed,
                           limit=limit,
                           item_count=item_count,
                           query=query,
                           )
    role = u'responsible'
    id = '%s-%s' % (type, role)
    if id not in container:
        query = get_collection_query(type, role)
        collection = api.content.create(container=container,
                           type="pfwbgedcollection",
                           id=id,
                           title=u"Mes tâches",
                           sort_on=sort_on,
                           sort_reversed=sort_reversed,
                           limit=limit,
                           item_count=item_count,
                           query=query,
                           )
    # opinions
    type = u'opinion'
    role = u'enquirer'
    id = '%s-%s' % (type, role)
    if id not in container:
        query = get_collection_query(type, role)
        collection = api.content.create(container=container,
                           type="pfwbgedcollection",
                           id=id,
                           title=u"Demandes d'avis que j'ai faites",
                           sort_on=sort_on,
                           sort_reversed=sort_reversed,
                           limit=limit,
                           item_count=item_count,
                           query=query,
                           )
    role = u'responsible'
    id = '%s-%s' % (type, role)
    if id not in container:
        query = get_collection_query(type, role)
        collection = api.content.create(container=container,
                           type="pfwbgedcollection",
                           id=id,
                           title=u"Demandes d'avis auxquelles je dois répondre",
                           sort_on=sort_on,
                           sort_reversed=sort_reversed,
                           limit=limit,
                           item_count=item_count,
                           query=query,
                           )
    # validations
    type = u'validation'
    role = u'enquirer'
    id = '%s-%s' % (type, role)
    if id not in container:
        query = get_collection_query(type, role)
        collection = api.content.create(container=container,
                           type="pfwbgedcollection",
                           id=id,
                           title=u"Demandes de validation que j'ai faites",
                           sort_on=sort_on,
                           sort_reversed=sort_reversed,
                           limit=limit,
                           item_count=item_count,
                           query=query,
                           )
    role = u'responsible'
    id = '%s-%s' % (type, role)
    if id not in container:
        query = get_collection_query(type, role)
        collection = api.content.create(container=container,
                           type="pfwbgedcollection",
                           id=id,
                           title=u"Demandes de validation auxquelles je dois répondre",
                           sort_on=sort_on,
                           sort_reversed=sort_reversed,
                           limit=limit,
                           item_count=item_count,
                           query=query,
                           )
    # informations
    sort_on = u'created'
    type = u'information'
    role = u'enquirer'
    id = '%s-%s' % (type, role)
    if id not in container:
        query = get_collection_query(type, role)
        collection = api.content.create(container=container,
                           type="pfwbgedcollection",
                           id=id,
                           title=u"Documents que j'ai transmis pour information",
                           sort_on=sort_on,
                           sort_reversed=sort_reversed,
                           limit=limit,
                           item_count=item_count,
                           query=query,
                           )
    role = u'responsible'
    id = '%s-%s' % (type, role)
    if id not in container:
        query = get_collection_query(type, role)
        collection = api.content.create(container=container,
                           type="pfwbgedcollection",
                           id=id,
                           title=u"À lire",
                           sort_on=sort_on,
                           sort_reversed=sort_reversed,
                           limit=limit,
                           item_count=item_count,
                           query=query,
                           )


def post_install(context):
    """Post install script"""
    if isNotCurrentProfile(context): return
    portal = context.getSite()

    # Remove dummy content
    if 'front-page' in portal:
        portal.manage_delObjects(['front-page'])
    if 'news' in portal:
        portal.manage_delObjects(['news'])
    if 'events' in portal:
        portal.manage_delObjects(['events'])
    if 'Members' not in portal:
        portal.invokeFactory('Folder', 'Members', title="Membres")
        portal.Members.exclude_from_nav = True
        portal.Members.reindexObject()
    if not IDexterityContainer.providedBy(portal.Members):
        del portal['Members']
        portal.invokeFactory('Folder', 'Members', title="Membres")
        portal.Members.exclude_from_nav = True
        portal.Members.reindexObject()
        # enable user folders
        portal.portal_membership.memberareaCreationFlag = True

    if 'annuaire' not in portal:
        portal.invokeFactory('directory', 'annuaire', title="Annuaire")
        annuaire = portal.annuaire
        annuaire.organization_levels = [{'token': u'service', 'name': u'Service'},
                                        {'token': u'departement', 'name': u'D\xe9partement'}]
        annuaire.organization_types = [{'token': u'entreprise', 'name': u'Entreprise'},
                                       {'token': u'mairie', 'name': u'Mairie'}]
        annuaire.position_types = [{'token': u'chef', 'name': u'Chef'},
                                   {'token': u'sous-chef', 'name': u'Sous-chef'},
                                   {'token': u'gerant', 'name': u'G\xe9rant'}]
        annuaire = portal.annuaire
        alsoProvides(annuaire, IFacetedNavigable)
        alsoProvides(annuaire, IDisableSmartFacets)
        alsoProvides(annuaire, IHidePloneLeftColumn)
        alsoProvides(annuaire, IHidePloneRightColumn)
        annuaire.unrestrictedTraverse('@@faceted_exportimport').import_xml(
                import_file=open(os.path.dirname(__file__) + '/annuaire-faceted.xml'))
    portal.portal_types.directory.global_allow = False

    if 'documents' not in portal:
        portal.invokeFactory('Folder', 'documents', title="Documents")

    # configure document types that can be added to the /documents folder, the
    # list of allowed types is extracted from pfwbgedfolder type, so they
    # always match.
    typesTool = getToolByName(portal, 'portal_types')
    fti = typesTool.getTypeInfo('pfwbgedfolder')
    setup_constrains(portal['documents'],
            [x for x in fti.allowed_content_types if x not in (
                'pfwbgedfolder', 'pfwbgedlink',)])

    if 'dossiers' not in portal:
        portal.invokeFactory('Folder', 'dossiers', title="Dossiers")
    setup_constrains(portal['dossiers'], ['pfwbgedfolder'])

    # everyone can see annuaire, documents, and dossiers
    if api.content.get_state(portal['annuaire']) == 'private':
        api.content.transition(obj=portal['annuaire'], transition="publish")
        portal['annuaire'].reindexObject(idxs=['review_state'])
    if api.content.get_state(portal['documents']) == 'private':
        api.content.transition(obj=portal['documents'], transition="publish")
        portal['documents'].reindexObject(idxs=['review_state'])
    if api.content.get_state(portal['dossiers']) == 'private':
        api.content.transition(obj=portal['dossiers'], transition="publish")
        portal['dossiers'].reindexObject(idxs=['review_state'])
    if api.content.get_state(portal['Members']) == 'private':
        api.content.transition(obj=portal['Members'], transition="publish")
        portal['Members'].reindexObject(idxs=['review_state'])

    # create information, task, opinion, validation collections
    create_tasks_collections(context)

    # configure external editor
    portal.externaleditor_enabled_types = ['File', 'dmsmainfile']
    portal.ext_editor = True
    portal.portal_actions.document_actions.extedit.visible = False

    # configure portal_membership to use pfwbged.folder for user folders
    portal.portal_membership.memberarea_type = 'pfwbgedfolder'
