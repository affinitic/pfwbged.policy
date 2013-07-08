# -*- coding: utf-8 -*-
import os
from zope.interface import alsoProvides

from plone import api
from Products.CMFPlone.interfaces.constrains import ISelectableConstrainTypes
from plone.app.dexterity.behaviors import constrains
from plone.dexterity.interfaces import IDexterityContainer

from eea.facetednavigation.interfaces import (
    IFacetedNavigable,
    IDisableSmartFacets,
    IHidePloneLeftColumn,
    IHidePloneRightColumn)

from . import _


def isNotCurrentProfile(context):
    return context.readDataFile("pfwbgedpolicy_marker.txt") is None


def setup_constrains(container, allowed_types):
    behavior = ISelectableConstrainTypes(container)
    behavior.setConstrainTypesMode(constrains.ENABLED)
    behavior.setImmediatelyAddableTypes(allowed_types)
    return True


def get_collection_query(type, role):
    """Return query to build collection for a given type and role"""
    current_user = api.user.get_current().getId()
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
              u'o': u'plone.app.querystring.operation.selection.is',
              u'v': current_user,
              },
            ]


def create_tasks_collections(context):
    """Create collections for tasks, informations, validations, opinions"""
    # parameters that are the same for all types of 'tasks'
    sort_on = u'modified'
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
        api.content.create(container=container,
                           type="Collection",
                           id=id,
                           title=_(u"Tasks that I asked for"),
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
        api.content.create(container=container,
                           type="Collection",
                           id=id,
                           title=_(u"My tasks"),
                           sort_on=sort_on,
                           sort_reversed=sort_reversed,
                           limit=limit,
                           item_count=item_count,
                           query=query,
                           )
    # informations
    type = u'information'
    role = u'enquirer'
    id = '%s-%s' % (type, role)
    if id not in container:
        query = get_collection_query(type, role)
        api.content.create(container=container,
                           type="Collection",
                           id=id,
                           title=_(u"Informations that I have sent"),
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
        api.content.create(container=container,
                           type="Collection",
                           id=id,
                           title=_(u"Documents to read"),
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
        api.content.create(container=container,
                           type="Collection",
                           id=id,
                           title=_(u"Opinion applications that I have made"),
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
        api.content.create(container=container,
                           type="Collection",
                           id=id,
                           title=_(u"Opinion applications to which I must answer"),
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
        api.content.create(container=container,
                           type="Collection",
                           id=id,
                           title=_(u"Validation applications that I have made"),
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
        api.content.create(container=container,
                           type="Collection",
                           id=id,
                           title=_(u"Validation applications to which I must answer"),
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

    if 'documents' not in portal:
        portal.invokeFactory('Folder', 'documents', title="Documents")
    #setup_constrains(portal['courriers'], ['dmsincomingmail', 'dmsoutgoingmail'])

    # create information, task, opinion, validation collections
    create_tasks_collections(context)
