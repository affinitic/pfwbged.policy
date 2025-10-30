# -*- coding: utf-8 -*-
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from plone import api
from plone.app.registry.browser import controlpanel
from z3c.form import form
from zope import schema
from zope.interface import Interface
from pfwbged.policy import _


class IPfwbgedControlPanel(Interface):
    """Schema for PFWB GED Settings control panel (currently empty)"""
    # Add future settings here


class PfwbgedControlPanelEditForm(controlpanel.RegistryEditForm):
    """PFWB GED Settings control panel form"""
    schema = IPfwbgedControlPanel
    label = _(u"PFWB GED Settings")
    description = _(u"Configure PFWB GED settings")


class PfwbgedControlPanel(controlpanel.ControlPanelFormWrapper):
    """Control panel view with custom template"""
    form = PfwbgedControlPanelEditForm
    index = ViewPageTemplateFile('templates/controlpanel.pt')

    def rename_group_url(self):
        """URL to the group renaming tool"""
        return "{}/@@rename-group".format(api.portal.get().absolute_url())
