from five import grok
from plone.dexterity.interfaces import IDexterityContainer

from collective.edm.listing.listingoptions import DefaultListingOptions
from collective.edm.listing.listingrights import DefaultListingRights


class Options(DefaultListingOptions, grok.View):
    grok.name("edmlistingoptions")
    grok.context(IDexterityContainer)
    grok.require('zope2.View')
    sort_mode = 'auto'
    default_sort_on = 'created'
    default_sort_order = 'reverse'
    allow_edit_popup = False

    def render(self):
        return u""


class Rights(DefaultListingRights, grok.View):
    grok.name("edmlistingrights")
    grok.context(IDexterityContainer)
    grok.require('zope2.View')

    def render(self):
        return u""

    def globally_can_copy(self, brains):
        return False

    def can_delete(self, brain):
        return False
