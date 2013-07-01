from five import grok
from zope.component import getMultiAdapter
from zope.component import queryMultiAdapter
from zope.interface import Interface
from zope.publisher.interfaces.browser import IDefaultBrowserLayer

from plone import api
from plone.app.content.browser.folderfactories import _allowedTypes
from plone.app.contentmenu import menu, interfaces

from Products.CMFPlone.interfaces.constrains import IConstrainTypes
from Products.CMFCore.utils import getToolByName

from . import _


add_actions_mapping = {'dmsmainfile': _(u"Create a new version"),
                       'information': _(u'Send for information'),
                       #'opinion': _(u'Ask opinion'),
                       #'task': _(u'Ask treatment'),
                       #'validation': _(u'Ask validation'),
                       }


class ActionsSubMenuItem(grok.MultiAdapter, menu.ActionsSubMenuItem):
    grok.adapts(Interface, IDefaultBrowserLayer)
    grok.name('plone.contentmenu.actions')
    grok.provides(interfaces.IContentMenuItem)

    def available(self):
        return False


class FactoriesSubMenuItem(grok.MultiAdapter, menu.FactoriesSubMenuItem):
    grok.adapts(Interface, IDefaultBrowserLayer)
    grok.name('plone.contentmenu.factories')
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

    def available(self):
        """Menu is always visible"""
        return True

    def action(self):
        return self.context.absolute_url() + '/content_status_history'


class CustomMenu(menu.WorkflowMenu):
    """Custom menu : actions, workflow and factories menu, all in one"""

    def getWorkflowActionsForObject(self, context, request):
        """Get transitions actions"""
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

    def getAddActionsForObject(self, context, request):
        """Get add items actions"""
        factories_view = getMultiAdapter((context, request),
                                         name='folder_factories')

        haveMore = False
        include = None

        addContext = factories_view.add_context()
        allowedTypes = _allowedTypes(request, addContext)

        constraints = IConstrainTypes(addContext, None)
        if constraints is not None:
            include = constraints.getImmediatelyAddableTypes()
            if len(include) < len(allowedTypes):
                haveMore = True

        results = []
        _results = factories_view.addable_types(include=include)
        for result in _results:
            if result['id'] in ('dmsmainfile', 'information'):
                result['extra']['class'] += ' pfwb-overlay-form-reload'
                result['title'] = add_actions_mapping[result['id']]
            elif result['id'] in ('validation', 'opinion', 'task'):
                continue
            else:
                result['title'] = _(u"Add ${title}", mapping={"title": result['title']})
            results.append(result)

#        if haveMore:
#            url = '%s/folder_factories' % (addContext.absolute_url(),)
#            results.append({
#                'title': _(u'folder_add_more', default=u'More\u2026'),
#                'description': _(u'Show all available content types'),
#                'action': url,
#                'selected': False,
#                'icon': None,
#                'extra': {
#                    'id': 'plone-contentmenu-more',
#                    'separator': None,
#                    'class': ''},
#                'submenu': None,
#            })
#
#        constraints = ISelectableConstrainTypes(addContext, None)
#        if constraints is not None:
#            if constraints.canSetConstrainTypes() and \
#                    constraints.getDefaultAddableTypes():
#                url = '%s/folder_constraintypes_form' % (
#                    addContext.absolute_url(),)
#                results.append({
#                    'title': _(u'folder_add_settings',
#                        default=u'Restrictions\u2026'),
#                    'description':
#                        _(u'title_configure_addable_content_types',
#                            default=u'Configure which content types can be '
#                                    u'added here'),
#                    'action': url,
#                    'selected': False,
#                    'icon': None,
#                    'extra': {
#                        'id': 'plone-contentmenu-settings',
#                        'separator': None,
#                        'class': ''},
#                    'submenu': None,
#                    })

        # Also add a menu item to add items to the default page
        context_state = getMultiAdapter((context, request),
                                        name='plone_context_state')
        if context_state.is_structural_folder() and context_state.is_default_page():
            results.append({
                'title': _(u'default_page_folder',
                    default=u'Add item to default page'),
                'description':
                    _(u'desc_default_page_folder',
                        default=u'If the default page is also a folder, '
                                u'add items to it from here.'),
                'action': context.absolute_url() + '/@@folder_factories',
                'selected': False,
                'icon': None,
                'extra': {
                    'id': 'plone-contentmenu-add-to-default-page',
                    'separator': None,
                    'class': ''},
                'submenu': None,
                })

        return results


    def getActionsForObject(self, context, request):
        """Get other actions"""
        results = []

        context_state = getMultiAdapter((context, request),
            name='plone_context_state')
        editActions = context_state.actions('object_buttons')
        if not editActions:
            return results

        actionicons = getToolByName(context, 'portal_actionicons')
        portal_url = getToolByName(context, 'portal_url')()

        for action in editActions:
            if action['allowed']:
                aid = action['id']
                cssClass = 'actionicon-object_buttons-%s' % aid
                icon = action.get('icon', None)
                if not icon:
                    # allow fallback to action icons tool
                    icon = actionicons.queryActionIcon('object_buttons', aid)
                    if icon:
                        icon = '%s/%s' % (portal_url, icon)

                results.append({
                    'title': action['title'],
                    'description': '',
                    'action': action['url'],
                    'selected': False,
                    'icon': icon,
                    'extra': {'id': 'plone-contentmenu-actions-' + aid,
                              'separator': None,
                              'class': cssClass},
                    'submenu': None,
                })
        return results

    def getMenuItems(self, context, request):
        results = []
        results.extend(self.getWorkflowActionsForObject(context, request))
        results.extend(self.getAddActionsForObject(context, request))
        results.extend(self.getActionsForObject(context, request))

        for obj in context.listFolderContents():
            results.extend(self.getWorkflowActionsForObject(obj, request))

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
