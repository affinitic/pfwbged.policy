# -*- coding: utf-8 -*-
from plone import api
from Products.CMFPlone.interfaces.constrains import ISelectableConstrainTypes
from plone.app.dexterity.behaviors import constrains


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
        portal.Members.setExcludeFromNav(True)
        portal.Members.reindexObject()

    if 'courriers' not in portal:
        portal.invokeFactory('Folder', 'courriers', title="Courriers",)

    setup_constrains(portal['courriers'], ['dmsincomingmail', 'dmsoutgoingmail'])

    if 'service-informatique' not in portal:
        portal.invokeFactory('workspace', 'service-informatique', title="Service informatique",)

    # grant Contributor role to all Authenticated Users
    api.group.grant_roles(groupname='AuthenticatedUsers', roles=['Contributor'])
