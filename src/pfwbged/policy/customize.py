from zope.interface import implements
from zope.component import adapts, queryUtility

from plone.directives.form.value import default_value
from plone.directives.form.value import widget_label

from plone.app.portlets.interfaces import IDefaultDashboard
from plone.app.portlets import portlets
from Products.PluggableAuthService.interfaces.authservice import IPropertiedUser

from collective.dms.basecontent.dmsdocument import IDmsDocument

import pfwbged.theme.folderlinks


from . import _


@widget_label(field=IDmsDocument['treating_groups'])
def change_treating_groups_label(data):
    return _(u"Can edit")


@widget_label(field=IDmsDocument['recipient_groups'])
def change_recipent_groups_label(data):
    return _(u"Can view")


class DefaultDashboard(object):
    """Default dashboard"""

    implements(IDefaultDashboard)
    adapts(IPropertiedUser)

    def __init__(self, principal):
        self.principal = principal

    def __call__(self):
        folderlinks_portlet = pfwbged.theme.folderlinks.Assignment()
        folderlinks_portlet.name = _('Folders')
        tasks_portlet = pfwbged.collection.portlet.Assignment()
        tasks_portlet.header = _('My Tasks')
        tasks_portlet.target_collection = 'Members/task-responsible'
        return {
            'plone.dashboard1': (folderlinks_portlet,),
            'plone.dashboard2': (tasks_portlet,),
            'plone.dashboard3': (),
            'plone.dashboard4': (),
        }
