# -*- coding: utf-8 -*-
from plone import api
from Products.CMFPlone.interfaces.constrains import ISelectableConstrainTypes
from plone.app.dexterity.behaviors import constrains
from plone.dexterity.interfaces import IDexterityContainer


def isNotCurrentProfile(context):
    return context.readDataFile("pfwbgedpolicy_marker.txt") is None


def setup_constrains(container, allowed_types):
    behavior = ISelectableConstrainTypes(container)
    behavior.setConstrainTypesMode(constrains.ENABLED)
    behavior.setImmediatelyAddableTypes(allowed_types)
    return True


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
    if 'Members' in portal:
        if not IDexterityContainer.providedBy(portal.Members):
            del portal['Members']
            portal.invokeFactory('Folder', 'Members', title="Membres")

#        portal.Members.setExcludeFromNav(True)
#        portal.Members.excludeFromNav = True
#        portal.Members.reindexObject()

    if 'annuaire' not in portal:
        portal.invokeFactory('directory', 'annuaire', title="Annuaire")
        portal.annuaire.organization_levels = [{'token': u'service', 'name': u'Service'},
                                               {'token': u'departement', 'name': u'D\xe9partement'}]
        portal.annuaire.organization_types = [{'token': u'entreprise', 'name': u'Entreprise'},
                                              {'token': u'mairie', 'name': u'Mairie'}]
        portal.annuaire.position_types = [{'token': u'chef', 'name': u'Chef'},
                                          {'token': u'sous-chef', 'name': u'Sous-chef'},
                                          {'token': u'gerant', 'name': u'G\xe9rant'}]

    if 'courriers' not in portal:
        portal.invokeFactory('Folder', 'courriers', title="Courriers")

    setup_constrains(portal['courriers'], ['dmsincomingmail', 'dmsoutgoingmail'])

    if 'service-informatique' not in portal:
        portal.invokeFactory('workspace', 'service-informatique', title="Service informatique")

    # grant Contributor role to all Authenticated Users
    api.group.grant_roles(groupname='AuthenticatedUsers', roles=['Contributor'])
