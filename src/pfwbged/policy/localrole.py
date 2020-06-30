# -*- coding: utf-8 -*-

from borg.localrole.interfaces import ILocalRoleProvider
from plone import api
from zope.interface import implements


class LocalRoleAdapter(object):
    implements(ILocalRoleProvider)

    def __init__(self, context):
        self.context = context

    @property
    def accepted_group(self):
        try:
            return api.portal.get_registry_record('pfwbged.mail_reader_group')
        except api.exc.InvalidParameterError:
            return ''

    def getRoles(self, principal):
        """Grant permission for principal"""
        if principal == self.accepted_group:
            return ('Reader',)
        else:
            return ()

    def getAllRoles(self):
        """Grant permissions"""
        return [(self.accepted_group, ('Reader',))]
