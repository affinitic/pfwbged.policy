from five import grok
from plone.app.contentmenu import menu, interfaces
from zope.interface import Interface
from zope.component import queryMultiAdapter
from zope.publisher.interfaces.browser import IDefaultBrowserLayer

from Products.CMFCore.utils import getToolByName

from . import _


class ActionsSubMenuItem(grok.MultiAdapter, menu.ActionsSubMenuItem):
    grok.adapts(Interface, IDefaultBrowserLayer)
    grok.name('plone.contentmenu.actions')
    grok.provides(interfaces.IContentMenuItem)

    def available(self):
        return False


class WorkflowSubMenuItem(grok.MultiAdapter, menu.WorkflowSubMenuItem):
    grok.adapts(Interface, IDefaultBrowserLayer)
    grok.name('plone.contentmenu.workflow')
    grok.provides(interfaces.IContentMenuItem)

    title = _(u'Actions')

    def _currentStateTitle(self):
        return u""


class WorkflowMenu(menu.WorkflowMenu):
    def getMenuItemsForObject(self, context, request):
        results = []

        locking_info = queryMultiAdapter((context, request),
                                         name='plone_lock_info')
        if locking_info and locking_info.is_locked_for_current_user():
            return []

        wf_tool = getToolByName(context, 'portal_workflow')
        workflowActions = wf_tool.listActionInfos(object=context)

        for action in workflowActions:
            if action['category'] != 'workflow':
                continue

            cssClass = 'kssIgnore'
            actionUrl = action['url']
            if actionUrl == "":
                actionUrl = '%s/content_status_modify?workflow_action=%s' % (
                    context.absolute_url(), action['id'])
                cssClass = ''

            description = ''

            transition = action.get('transition', None)
            if transition is not None:
                description = transition.description


            if action['allowed']:
                results.append({
                    'title': action['title'],
                    'description': description,
                    'action': actionUrl,
                    'selected': False,
                    'icon': None,
                    'extra': {
                        'id': 'workflow-transition-%s' % action['id'],
                        'separator': None,
                        'class': cssClass},
                    'submenu': None,
                })
        return results

    def getMenuItems(self, context, request):
        results = []
        results.extend(self.getMenuItemsForObject(context, request))
#        for obj in context.values():
#            results.extend(self.getMenuItemsForObject(obj, request))

#        url = context.absolute_url()

#        results.append({
#            'title': 'valider avis',
#            'description': '',
#            'action': url + '/monavis/change_state',
#            'selected': False,
#            'icon': None,
#            'extra': {'id': 'workflow-transition-monavis',
#                      'separator': None,
#                      'class': ''},
#            'submenu': None,
#        })
        return results
