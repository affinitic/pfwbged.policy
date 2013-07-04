from five import grok
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.component import queryMultiAdapter
from zope.i18nmessageid import MessageFactory
from zope.interface import Interface
from zope.intid.interfaces import IIntIds
from zope.publisher.interfaces.browser import IDefaultBrowserLayer

from plone import api
from plone.app.content.browser.folderfactories import _allowedTypes
from plone.app.contentmenu import menu, interfaces

from Products.CMFPlone.interfaces.constrains import IConstrainTypes
from Products.CMFCore.utils import getToolByName

from collective.dms.basecontent.dmsdocument import IDmsDocument
from collective.task.content.information import IInformation
from collective.task.content.opinion import IOpinion

from . import _


PMF = MessageFactory('plone')

add_actions_mapping = {'dmsmainfile': _(u"Create a new version"),
                       'information': _(u'Send for information'),
                       }



def get_wf_action_title(action, context):
    """Get workflow action title"""
    if action['id'] == 'mark-as-done':
        if IInformation.providedBy(context):
            return _(u"Mark document as read")
        elif IOpinion.providedBy(context):
            version = context.target.to_object.Title()
            return _(u"Return opinion about ${version}",
                     mapping={'version': version})
    return action['title']


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

            if action['id'] in ('submit', 'ask_opinion'):
                cssClass += " overlay-form-reload"

            description = ''

            transition = action.get('transition', None)
            if transition is not None:
                description = transition.description

            title = get_wf_action_title(action, context)

            if IOpinion.providedBy(context) and action['id'] == 'mark-as-done':
                actionUrl = context.absolute_url()
                cssClass = 'overlay-comment-form'

            if action['allowed']:
                results.append({
                    'title': title,
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
                result['extra']['class'] += ' overlay-form-reload'
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
                'title': PMF(u'default_page_folder',
                    default=u'Add item to default page'),
                'description':
                    PMF(u'desc_default_page_folder',
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

    def getActionsForObject(self, context, request, is_subobject=False):
        """Get other actions"""
        results = []

        context_state = getMultiAdapter((context, request),
            name='plone_context_state')

        if is_subobject:
            # only take portal_type actions
            ttool = api.portal.get_tool("portal_types")
            editActions = ttool.listActionInfos(object=context,
                                                category='object_buttons',
                                                max=-1)
        else:
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

    def getWorkflowActionsForType(self, context, request, portal_type):
        """Get workflow actions for a portal type"""
        catalog = api.portal.get_tool('portal_catalog')
        actions = []
        container_path = '/'.join(context.getPhysicalPath())
        brains = catalog.searchResults({'path': container_path,
                                        'portal_type': portal_type})
        for brain in brains:
            obj = brain.getObject()
            actions.extend(self.getWorkflowActionsForObject(obj, request))
        # actions on content redirect to document after transition
        for action in actions:
            action['action'] = action['action'].replace("content_status_modify",
                                                       "redirect_to_dmsdocument")
        return actions

    def getMenuItems(self, context, request):
        actions = []
        actions.extend(self.getWorkflowActionsForObject(context, request))

        fsmi = menu.FactoriesSubMenuItem(context, request)
        if fsmi.available():
            actions.extend(self.getAddActionsForObject(context, request))

        actions.extend(self.getActionsForObject(context, request))

        catalog = api.portal.get_tool('portal_catalog')

        if IDmsDocument.providedBy(context):
            for item in context.listFolderContents():
                actions.extend(self.getActionsForObject(item, request, is_subobject=True))

            # wf actions on versions
            actions.extend(self.getWorkflowActionsForType(context, request, 'dmsmainfile'))

            # wf actions on tasks
            actions.extend(self.getWorkflowActionsForType(context, request, 'task'))

            # wf actions on opinions
            actions.extend(self.getWorkflowActionsForType(context, request, 'opinion'))

            # wf actions on informations
            actions.extend(self.getWorkflowActionsForType(context, request, 'information'))

        return actions
