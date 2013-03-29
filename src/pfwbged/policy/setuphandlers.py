# -*- coding: utf-8 -*-
from plone import api


def isNotCurrentProfile(context):
    return context.readDataFile("pfwbgedpolicy_marker.txt") is None


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

    # grant Contributor role to all Authenticated Users
    api.group.grant_roles(groupname='AuthenticatedUsers', roles=['Contributor'])
