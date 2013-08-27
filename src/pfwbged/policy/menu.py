from five import grok
from zc.relation.interfaces import ICatalog
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
from collective.dms.basecontent.dmsfile import IDmsFile
from collective.task.behaviors import ITarget
from collective.task.content.validation import IValidation
from collective.task.content.information import IInformation
from collective.task.content.opinion import IOpinion
from collective.task.content.task import ITask

from . import _

IGNORE_ = _
PMF = MessageFactory('plone')

add_actions_mapping = {'dmsmainfile': _(u"Create a new version"),
                       'information': _(u'Send for information'),
                       'pfwbgedlink': _(u'File in a folder'),
                       }
dmsfile_wfactions_mapping = {'ask_opinion': _(u"Ask opinion about version ${version}"),
                             'submit': _(u"Ask validation about version ${version}"),
                             'validate': _(u"Validate version ${version}"),
                             'refuse': _(u"Refuse version ${version}"),
                             'finish': _(u"Finish version ${version}"),
                             'finish_without_validation': _(u"Finish version ${version}"),
                             }


def outgoingmail_created(task):
    """Return true if an outgoing mail has been created for this task"""
    intids = getUtility(IIntIds)
    catalog = getUtility(ICatalog)
    refs = []
    try:
        task_intid = intids.getId(task)
    except KeyError:
        pass
    else:
        for ref in catalog.findRelations({'to_id': task_intid,
                                          'from_attribute': 'related_task'}):
            refs.append(ref)
    return bool(refs)


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

            if action is workflowActions[0]:
                cssClass += ' first-workflow-action'

            description = ''

            if action['id'] in ('submit', 'ask_opinion', 'attribute'):
                cssClass += " overlay-form-reload"

            transition = action.get('transition', None)
            if transition is not None:
                description = transition.description

            if ITarget.providedBy(context):
                version = context.target.to_object.Title()

            if IInformation.providedBy(context):
                if action['id'] == 'mark-as-done':
                    title = _(u"Mark document as read")
            elif IOpinion.providedBy(context):
                if action['id'] == 'mark-as-done':
                    actionUrl = context.absolute_url()
                    cssClass = 'overlay-comment-form'
                    title = _(u"Return opinion about ${version}",
                              mapping={'version': version})
            elif ITask.providedBy(context):
                if action['id'] in ('ask-for-refusal',
                                    'accept-refusal',
                                    'refuse-refusal'):
                    cssClass = 'overlay-comment-form'
                title= action['title']
            elif IValidation.providedBy(context):
                action_name = action['title']
                title = _(u"${action} the version ${version}",
                          mapping={'action': action_name,
                                   'version': version})
            elif IDmsFile.providedBy(context):
                action_name = action['title']
                version = context.Title()
                title = dmsfile_wfactions_mapping[action['id']]
                title = IGNORE_(title, mapping={'version': version})
                cssClass += ' version-action version-id-%s' % context.id
            else:
                title = action['title']

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

        cssClass = ''

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
            if result['id'] == 'dmsmainfile':
                # don't add add action if there is already a finished version
                catalog = api.portal.get_tool('portal_catalog')
                container_path = '/'.join(context.getPhysicalPath())
                brains = catalog.searchResults({'path': container_path,
                                                'portal_type': 'dmsmainfile',
                                                'review_state': 'finished'})
                if brains:
                    continue
            elif result['id'] in ('validation', 'opinion', 'task'):
                continue

            if result['id'] in ('dmsmainfile', 'information', 'pfwbgedlink'):
                result['extra']['class'] += ' overlay-form-reload'
                result['title'] = add_actions_mapping[result['id']]
            elif result['id'] in ('dmsappendixfile'):
                result['extra']['class'] += ' overlay-form-reload'
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

        if results:
            results[0]['extra']['class'] += ' first-add-action'

        return results

    def getActionsForObject(self, context, request, is_subobject=False):
        """Get other actions"""
        results = []

        context_state = getMultiAdapter((context, request),
            name='plone_context_state')

        if is_subobject:
            # only take portal_type actions
            ttool = api.portal.get_tool("portal_types")
            _editActions = ttool.listActionInfos(object=context,
                                                category='object_buttons',
                                                max=-1)
            editActions = [action for action in _editActions if action['id'] != 'create_outgoing_mail' or not outgoingmail_created(context)]

        else:
            editActions = []
            _editActions = context_state.actions('object_buttons')
            editActions = [action for action in _editActions if action['id'] not in ('paste', 'cut', 'copy')]

        if not editActions:
            return results

        actionicons = getToolByName(context, 'portal_actionicons')
        portal_url = getToolByName(context, 'portal_url')()

        for action in editActions:
            cssClass = ""
            if action is editActions[0]:
                cssClass = "first-action"

            if action['id'] == 'create_signed_version':
                action['title'] = _(u"Create signed version for version ${version}",
                                    mapping={'version': context.Title()})
                cssClass += " overlay-form-reload"
            elif action['id'] == 'create_outgoing_mail':
                # make it overlay !
                cssClass += ' overlay-form-redirect'

            if action['allowed']:
                aid = action['id']
                cssClass += ' actionicon-object_buttons-%s' % aid
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
            container_path = '/'.join(context.getPhysicalPath())
            brains = catalog.searchResults({'path': {'query': container_path},
                'portal_type': ('dmsmainfile', 'opinion', 'task', 'validation', 'information')})

            for brain in brains:
                item = brain.getObject()
                actions.extend(self.getActionsForObject(item, request, is_subobject=True))

            # wf actions on versions
            actions.extend(self.getWorkflowActionsForType(context, request, 'dmsmainfile'))

            # wf actions on tasks
            actions.extend(self.getWorkflowActionsForType(context, request, 'task'))

            # wf actions on opinions
            actions.extend(self.getWorkflowActionsForType(context, request, 'opinion'))

            # wf actions on informations
            actions.extend(self.getWorkflowActionsForType(context, request, 'information'))

        for action in actions:
            if not action.get('icon'):
                action['extra']['class'] += ' no-icon'

        return actions
