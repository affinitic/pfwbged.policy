import sys, time

from Acquisition import aq_inner, aq_parent
from five import grok
from zc.relation.interfaces import ICatalog
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.component import queryMultiAdapter
from zope.i18nmessageid import MessageFactory
from zope.interface import Interface
from zope.intid.interfaces import IIntIds
from zope.publisher.interfaces.browser import IDefaultBrowserLayer

from AccessControl import Unauthorized

from plone import api
from plone.app.content.browser.folderfactories import _allowedTypes
from plone.app.contentmenu import menu, interfaces

from Products.CMFPlone.interfaces.constrains import IConstrainTypes
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.interfaces.siteroot import IPloneSiteRoot

from collective.dms.basecontent.dmsdocument import IDmsDocument
from collective.dms.basecontent.dmsfile import IDmsFile
from collective.task.behaviors import ITarget
from collective.task.content.validation import IValidation
from collective.task.content.information import IInformation
from collective.task.content.opinion import IOpinion
from collective.task.content.task import ITask
from collective.task.indexers import get_document
from pfwbged.basecontent.behaviors import IPfwbIncomingMail
from pfwbged.collection import ICollection

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
                             'finish_without_validation': _(u"Validate and finish version ${version}"),
                             'send_by_email': _(u"Send version ${version} by email"),
                             'send_with_docbow': _(u"Send version ${version} with PES"),
                             'restore_from_trash': _(u"Restore version ${version}"),
                             'back_to_draft': _(u"Cancel validate and finish ${version}"),
                             'cancel-validation': _(u"Cancel validation of ${version}"),
                             'cancel-refusal': _(u"Cancel refusal of ${version}"),
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


def is_linked_to_an_incoming_mail(task):
    document = get_document(task)
    return IPfwbIncomingMail.providedBy(document)


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

        if context.portal_type in ('pfwbgedfolder', 'Folder'):
            return []

        locking_info = queryMultiAdapter((context, request),
                                         name='plone_lock_info')
        if locking_info and locking_info.is_locked_for_current_user():
            return []

        wf_tool = getToolByName(context, 'portal_workflow')
        workflowActions = wf_tool.listActionInfos(object=context)

        if 'to_process' in [x.get('id') for x in workflowActions]:
            to_process_action = [x for x in workflowActions if x['id'] == 'to_process'][0]
            to_process_without_comment_action = to_process_action.copy()
            to_process_without_comment_action['url'] = '%s/@@to_process_without_comment' % context.absolute_url()
            to_process_without_comment_action['id'] = 'to_process_without_comment'
            idx = workflowActions.index(to_process_action)
            workflowActions.insert(idx, to_process_without_comment_action)
            to_process_action['title'] = _(u'To process (with comment)')

        if IDmsFile.providedBy(context) and context.file:
            workflowActions.append(
                    {'available': True,
                     'visible': True,
                     'allowed': True,
                     'link_target': None,
                     'id': 'send_by_email',
                     'category': 'workflow',
                     'title': 'Send by email',
                     'url': context.absolute_url() + '/@@send_by_email',
                     'icon': None})
            if request.cookies.get('docbow-user') == 'true':
                workflowActions.append(
                        {'available': True,
                         'visible': True,
                         'allowed': True,
                         'link_target': None,
                         'id': 'send_with_docbow',
                         'category': 'workflow',
                         'title': 'Send by email',
                         'url': context.absolute_url() + '/@@send_with_docbow',
                         'icon': None})

        for action in workflowActions:
            if action['category'] != 'workflow':
                continue

            # that action is already triggered when returning responsibility on a task
            if action['id'] == 'back_to_assigning' and IDmsDocument.providedBy(context) and api.content.get_state(context) == 'processing':
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

            if action['id'] in ('submit', 'ask_opinion', 'attribute',
                    'to_process', 'refuse', 'send_by_email', 'cancel-attribution'):
                cssClass += " overlay-form-reload"

            if action['id'] in ('send_with_docbow',):
                cssClass += " target-new-tab"

            transition = action.get('transition', None)
            if transition is not None:
                description = transition.description

            if ITarget.providedBy(context):
                version = context.target.to_object.Title()

            if IInformation.providedBy(context):
                if action['id'] == 'mark-as-done':
                    title = _(u"Mark document as read")
                elif action['id'] == 'abandon':
                    action['allowed'] = False
            elif IOpinion.providedBy(context):
                if action['id'] == 'mark-as-done':
                    actionUrl = context.absolute_url()
                    cssClass = 'overlay-comment-form'
                    title = _(u"Return opinion about ${version}",
                              mapping={'version': version})
                elif action['id'] == 'abandon':
                    action['allowed'] = False
            elif ITask.providedBy(context):
                if action['id'] in ('ask-for-refusal',
                                    'accept-refusal',
                                    'refuse-refusal'):
                    cssClass = 'overlay-comment-form'
                title= action['title']
            elif IValidation.providedBy(context):
                if action['id'] == 'abandon':
                    action['allowed'] = False
                else:
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
                cssClass += ' version-action-%s' % action['id']

                # special case to allow cancellation of validation requests:
                # back_to_draft is available from state pending,
                # but it must not be done directly by users.
                if action['id'] == 'back_to_draft' and \
                    api.content.get_state(context) == 'pending':
                    continue

                # limit cancelling actions to a version's rightful owner
                # guards are bypassed for Managers, so call them at least once
                action_guards = {
                    'cancel-refusal': 'can_cancel_refusal',
                    'cancel-validation': 'can_cancel_validation',
                }
                if action['id'] in action_guards:
                    view = queryMultiAdapter(
                        (context, request),
                        name=action_guards.get(action['id'])
                    )
                    if view and not view.render():
                        action['allowed'] = False

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
        is_portal = IPloneSiteRoot.providedBy(context)

        constraints = IConstrainTypes(addContext, None)
        if constraints is not None:
            include = constraints.getImmediatelyAddableTypes()
            if len(include) < len(allowedTypes):
                haveMore = True

        results = []
        _results = factories_view.addable_types(include=include)
        for result in _results:

            if is_portal and result['id'] not in ('Folder', 'dmsthesaurus'):
                # we only advertise thesaurus and folders at the root
                continue

            if not is_portal and result['id'] in ('Folder', 'dmsthesaurus'):
                # we only allow thesaurus and (native plone) folders at the
                # root
                continue

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
                # tasks cannot be added manually
                continue
            elif result['id'] in ('pfwbgedcollection',):
                # ditto for our custom collection objects
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
            editActions = [action for action in _editActions if
                    action['id'] not in ('create_outgoing_mail',
                        'send_by_email', 'send_with_docbow') or (
                    is_linked_to_an_incoming_mail(context) and not outgoingmail_created(context))]

        else:
            editActions = []
            _editActions = context_state.actions('object_buttons')
            editActions = [action for action in _editActions if action['id'] not in (
                'paste', 'cut', 'copy', 'rename')]

        if not editActions:
            return results

        actionicons = getToolByName(context, 'portal_actionicons')
        portal_url = getToolByName(context, 'portal_url')()

        for action in editActions:
            cssClass = ""
            if action is editActions[0]:
                cssClass = "first-action"

            if action['id'] == 'create_signed_version':
                parent_document = aq_parent(context)
                has_signed = False
                for key in parent_document.keys():
                    try:
                        has_signed = (parent_document.get(key).signed == True)
                    except (Unauthorized, AttributeError):
                        continue
                    if has_signed:
                        break
                if has_signed:
                    continue
                action['title'] = _(u"Create signed version for version ${version}",
                                    mapping={'version': context.Title()})
                cssClass += " overlay-form-reload"
            elif action['id'] == 'create_outgoing_mail':
                # make it overlay !
                cssClass += ' overlay-form-redirect'
            elif action['id'] == 'delete':
                cssClass += " overlay-form-redirect"

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

        if IDmsDocument.providedBy(context) and \
                context.listFolderContents(contentFilter={
                    'portal_type': 'information',
                    'Creator': api.user.get_current().id,
                }):
            results.append({
                'title': _(u'Cancel information'),
                'description': '',
                'action': context.absolute_url() + '/@@cancel_information',
                'selected': False,
                'icon': None,
                'extra': {'id': 'plone-contentmenu-actions-cancel-information',
                          'separator': None,
                          'class': 'no-icon overlay-form-reload link-overlay'},
                'submenu': None,
            })

        catalog = api.portal.get_tool('portal_catalog')
        container_path = '/'.join(context.getPhysicalPath())
        brains = catalog.searchResults({
            'path': container_path,
            'portal_type': 'validation',
            'review_state': 'todo',
            'Creator': api.user.get_current().id,
        })
        if IDmsDocument.providedBy(context) and brains:
            results.append({
                'title': _(u'Cancel validation request'),
                'description': '',
                'action': context.absolute_url() + '/@@cancel_validation',
                'selected': False,
                'icon': None,
                'extra': {'id': 'plone-contentmenu-actions-cancel-validation',
                          'separator': None,
                          'class': 'no-icon overlay-form-reload link-overlay'},
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

            if context.portal_type in ('pfwb.boarddecision',):
                # ideally this condition would be part of the task action
                # condition_expr, but that would require to get down from there
                # back to the document; it's much easier to just hide it from
                # here.
                actions = [x for x in actions if \
                        x.get('extra').get('id') != 'plone-contentmenu-actions-create_outgoing_mail']

        if ICollection.providedBy(context):
            # edition of collections is done inline, remove edit action but add
            # save and save as
            had_edit = [x for x in actions if x.get('extra', {}).get('id') == 'plone-contentmenu-actions-edit']
            actions = [x for x in actions if x.get('extra', {}).get('id') != 'plone-contentmenu-actions-edit']
            if had_edit:
                actions.append(
                    {'submenu': None, 'description': '', 'extra': {
                        'separator': None,
                        'id': 'plone-contentmenu-actions-save',
                        'class': ' actionicon-object_buttons-save'},
                        'selected': False,
                        'action': '#',
                        'title': _('Save'),
                        'icon': None})
                actions.append(
                    {'submenu': None, 'description': '', 'extra': {
                        'separator': None,
                        'id': 'plone-contentmenu-actions-saveas',
                        'class': ' actionicon-object_buttons-saveas'},
                        'selected': False,
                        'action': '#',
                        'title': _('Save As...'),
                        'icon': None})

        for action in actions:
            if not action.get('icon'):
                action['extra']['class'] += ' no-icon'

        return actions
