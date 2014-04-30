import logging

from Acquisition import aq_chain, aq_parent
from five import grok
from DateTime import DateTime

from zc.relation.interfaces import ICatalog
from zope.container.interfaces import INameChooser
from zope.i18n import translate
from zope.component import getUtility
from zope.component.interfaces import ComponentLookupError
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent.interfaces import IObjectAddedEvent, IObjectModifiedEvent
from OFS.interfaces import IObjectWillBeRemovedEvent
from zope.annotation.interfaces import IAnnotations

from plone import api

from Products.DCWorkflow.interfaces import IAfterTransitionEvent

from collective.z3cform.rolefield.field import LocalRolesToPrincipalsDataManager

from collective.dms.basecontent.dmsdocument import IDmsDocument
from collective.task.content.task import IBaseTask, ITask
from collective.task.content.validation import IValidation
from collective.task.interfaces import IBaseTask
from collective.dms.basecontent.dmsfile import IDmsFile
from pfwbged.folder.folder import IFolder

from pfwbged.basecontent.behaviors import IPfwbDocument
from pfwbged.policy import _

from mail import changeWorkflowState


def has_pfwbgeddocument_workflow(obj):
    wtool = api.portal.get_tool('portal_workflow')
    return 'pfwbgeddocument_workflow' in wtool.getChainFor(obj)


@grok.subscribe(IBaseTask, IObjectAddedEvent)
def set_role_on_document(context, event):
    """Add Reader role to document for the responsible of an
    information, opinion, validation.
    """
    # recipient_groups is the "Visible par" field
    if not ITask.providedBy(context):
        document = context.getParentNode()
        if IDmsDocument.providedBy(document):
            new_recipients = tuple(frozenset(document.recipient_groups or []) | frozenset(context.responsible or []))
            cansee_dm = LocalRolesToPrincipalsDataManager(document, IDmsDocument['recipient_groups'])
            cansee_dm.set(new_recipients)
            document.reindexObjectSecurity()
    # do we have to set Editor role on document for ITask ? (if so, remove something for IDmsMail ?)


@grok.subscribe(IDmsFile, IAfterTransitionEvent)
def change_validation_state(context, event):
    """If version state is draft, change validation state from todo to refused (transition refuse).
    If version state is validated, change validation state from todo to validated (transition validate).

    """
    intids = getUtility(IIntIds)
    catalog = getUtility(ICatalog)
    version_intid = intids.queryId(context)
    if version_intid is None:
        return
    query = {'to_id': version_intid,
             'from_interfaces_flattened': IValidation,
             'from_attribute': 'target'}
    if event.new_state.id == 'draft':
        for ref in catalog.findRelations(query):
            validation = ref.from_object
            if api.content.get_state(validation) == 'todo':
                api.content.transition(validation, 'refuse')
                validation.reindexObject(idxs=['review_state'])
    elif event.new_state.id == 'validated':
        for ref in catalog.findRelations(query):
            validation = ref.from_object
            if api.content.get_state(validation) == 'todo':
                api.content.transition(validation, 'validate')
                validation.reindexObject(idxs=['review_state'])


@grok.subscribe(IDmsFile, IObjectWillBeRemovedEvent)
def delete_tasks(context, event):
    """Delete validations and opinions when a version is deleted.
    """
    try:
        intids = getUtility(IIntIds)
    except ComponentLookupError:  # when we remove the Plone site
        return
    catalog = getUtility(ICatalog)
    version_intid = intids.getId(context)
    query = {'to_id': version_intid,
             'from_interfaces_flattened': IBaseTask,
             'from_attribute': 'target'}
    for rv in catalog.findRelations(query):
        obj = rv.from_object
        #obj.aq_parent.manage_delObjects([obj.getId()])  # we don't want to verify Delete object permission on object
        del aq_parent(obj)[obj.getId()]


@grok.subscribe(IDmsFile, IObjectAddedEvent)
def version_is_signed_at_creation(context, event):
    """If checkbox signed is checked, finish version without validation after creation"""
    if context.signed:
        api.content.transition(context, 'finish_without_validation')
        context.reindexObject(idxs=['review_state'])


### Workflow for other documents
# @grok.subscribe(IPfwbDocument, IObjectAddedEvent)
def create_task_after_creation(context, event):
    """Create a task attributed to creator after document creation"""
    # only applies to "other documents"
    if not has_pfwbgeddocument_workflow(context):
        return

    creator = context.Creator()
    params = {'responsible': [],
              'title': translate(_(u'Process document'),
                                 context=context.REQUEST),
              }
    task_id = context.invokeFactory('task', 'process-document', **params)
    task = context[task_id]
    datamanager = LocalRolesToPrincipalsDataManager(task, ITask['responsible'])
    datamanager.set((creator,))
    task.reindexObject()


@grok.subscribe(ITask, IAfterTransitionEvent)
def task_in_progress(context, event):
    """When a task change state, change parent state
    """
    if event.new_state.id == 'in-progress':
        # go up in the acquisition chain to find the first task (i.e. the one which is just below the document)
        for obj in aq_chain(context):
            obj = aq_parent(obj)
            if IPfwbDocument.providedBy(obj):
                break
        # only applies to "other documents"
        if not has_pfwbgeddocument_workflow(obj):
            return
        document = obj
        api.content.transition(obj=document, transition='to_process')
        document.reindexObject(idxs=['review_state'])
    elif event.new_state.id == 'abandoned':
        obj = aq_parent(context)
        if not IPfwbDocument.providedBy(obj):
            return
        # only applies to "other documents"
        if not has_pfwbgeddocument_workflow(obj):
            return
        document = obj
        api.content.transition(obj=document, transition='directly_noaction')
        document.reindexObject(idxs=['review_state'])


@grok.subscribe(IDmsFile, IAfterTransitionEvent)
def version_note_finished(context, event):
    """Launched when version note is finished.
    """
    if event.new_state.id == 'finished':
        context.reindexObject(idxs=['review_state'])
        portal_catalog = api.portal.get_tool('portal_catalog')
        document = context.getParentNode()
        state = api.content.get_state(obj=document)
        # if parent is an outgoing mail, change its state to ready_to_send
        if document.portal_type in ('dmsoutgoingmail', 'pfwb.apfoutgoingmail') and state == 'writing':
            with api.env.adopt_user('admin'):
                api.content.transition(obj=document, transition='finish')
            document.reindexObject(idxs=['review_state'])
        elif IPfwbDocument.providedBy(document) and has_pfwbgeddocument_workflow(document):
            if state == 'processing':
                with api.env.adopt_user('admin'):
                    api.content.transition(obj=document, transition='process')
                document.reindexObject(idxs=['review_state'])
            elif state == "assigning":
                tasks = portal_catalog.unrestrictedSearchResults(portal_type='task',
                                                                 path='/'.join(document.getPhysicalPath()))
                for brain in tasks:
                    task = brain._unrestrictedGetObject()
                    if api.content.get_state(obj=task) == 'todo':
                        with api.env.adopt_user('admin'):
                            api.content.transition(obj=task, transition='take-responsibility')
                        task.reindexObject(idxs=['review_state'])
                # the document is now in processing state because the task is in progress
                api.content.transition(obj=document, transition='process')
                document.reindexObject(idxs=['review_state'])

        version_notes = portal_catalog.unrestrictedSearchResults(portal_type='dmsmainfile',
                                                                 path='/'.join(document.getPhysicalPath()))
        # make obsolete other versions
        for version_brain in version_notes:
            version = version_brain._unrestrictedGetObject()
            if api.content.get_state(obj=version) in ('draft', 'pending', 'validated'):
                api.content.transition(obj=version, transition='obsolete')
                version.reindexObject(idxs=['review_state'])
        context.__ac_local_roles_block__ = False
        context.reindexObjectSecurity()


@grok.subscribe(IDmsDocument, IAfterTransitionEvent)
def document_is_processed(context, event):
    """When document is processed, close all tasks"""
    portal_catalog = api.portal.get_tool('portal_catalog')
    if has_pfwbgeddocument_workflow(context) and event.new_state.id not in ('processing',):
        tasks = portal_catalog.unrestrictedSearchResults(portal_type='task',
                                                         path='/'.join(context.getPhysicalPath()))
        for brain in tasks:
            task = brain._unrestrictedGetObject()
            if api.content.get_state(obj=task) == 'in-progress':
                with api.env.adopt_user('admin'):
                    api.content.transition(obj=task, transition='mark-as-done')
                task.reindexObject(idxs=['review_state'])


@grok.subscribe(IDmsDocument, IAfterTransitionEvent)
def document_is_reopened(context, event):
    """When a document is reoponed, create a new task"""
    if has_pfwbgeddocument_workflow(context) and event.transition is not None and event.new_state.id == 'assigning':
        creator = api.user.get_current().getId()
        params = {'responsible': [],
                  'title': translate(_(u'Process document'),
                                     context=context.REQUEST),
                  }
        chooser = INameChooser(context)
        task_id = chooser.chooseName('process-document', context)
        task_id = context.invokeFactory('task', task_id, **params)
        task = context[task_id]
        datamanager = LocalRolesToPrincipalsDataManager(task, ITask['responsible'])
        datamanager.set((creator,))
        task.reindexObject()


@grok.subscribe(IBaseTask, IObjectAddedEvent)
def email_notification_of_tasks(context, event):
    """Notify recipients of new tasks by email"""
    # go up in the acquisition chain to find the document
    document = None
    for obj in aq_chain(context):
        obj = aq_parent(obj)
        if IDmsDocument.providedBy(obj):
            document = obj
            break
    if not document:
        return
    document.reindexObject(idxs=['allowedRolesAndUsers'])

    for enquirer in (context.enquirer or []):
        member = context.portal_membership.getMemberById(enquirer)
        if member:
            email_from = member.getProperty('email', None)
            if email_from:
                break
    else:
        email_from = api.user.get_current().email or api.portal.get().getProperty('email_from_address')

    subject = '%s - %s' % (context.title, document.title)
    body = translate(_('You received a request for action in the GED.'), context=context.REQUEST) + \
            '\n\n' + \
            translate(_('Title: %s'), context=context.REQUEST) % context.title + \
            '\n\n' + \
            translate(_('Document: %s'), context=context.REQUEST) % document.title + \
            '\n\n' + \
            translate(_('Document Address: %s'), context=context.REQUEST) % document.absolute_url() + \
            '\n\n'
    try:
        body += translate(_('Deadline: %s'), context=context.REQUEST) % context.deadline + '\n\n'
    except AttributeError:
        pass

    if context.note:
        body += translate(_('Note:'), context=context.REQUEST) + '\n\n' + context.note

    body = body.encode('utf-8')

    for responsible in (context.responsible or ['plop']):
        member = context.portal_membership.getMemberById(responsible)
        if not member:
            continue
        email = member.getProperty('email', None)
        if not email:
            continue
        try:
            context.MailHost.send(body, email, email_from, subject, charset='utf-8')
        except Exception as e:
            # do not abort transaction in case of email error
            log = logging.getLogger('pfwbged.policy')
            log.exception(e)


@grok.subscribe(IValidation, IAfterTransitionEvent)
def email_notification_of_refused_task(context, event):
    if event.new_state.id != 'refused':
        return

    # go up in the acquisition chain to find the document
    document = None
    for obj in aq_chain(context):
        obj = aq_parent(obj)
        if IDmsDocument.providedBy(obj):
            document = obj
            break
    if not document:
        return

    email_enquirer = None
    for enquirer in (context.enquirer or []):
        member = context.portal_membership.getMemberById(enquirer)
        if member:
            email_enquirer = member.getProperty('email', None)
            if email_enquirer:
                break

    if not email_enquirer:
        return

    email_from = api.user.get_current().email or api.portal.get().getProperty('email_from_address')

    subject = '%s - %s' % (context.title, document.title)

    body = translate(_('A validation request has been refused'), context=context.REQUEST) + \
            '\n\n' + \
            translate(_('Title: %s'), context=context.REQUEST) % context.title + \
            '\n\n' + \
            translate(_('Document: %s'), context=context.REQUEST) % document.title + \
            '\n\n' + \
            translate(_('Document Address: %s'), context=context.REQUEST) % document.absolute_url() + \
            '\n\n'

    body = body.encode('utf-8')

    try:
        context.MailHost.send(body, email_enquirer, email_from, subject, charset='utf-8')
    except Exception as e:
        # do not abort transaction in case of email error
        log = logging.getLogger('pfwbged.policy')
        log.exception(e)



@grok.subscribe(IDmsDocument, IObjectModifiedEvent)
def log_some_history(context, event):
    for description in event.descriptions:
        if not hasattr(description, 'attributes'):
            continue
        for field in ('treated_by', 'treating_groups', 'recipient_groups'):
            if not field in description.attributes:
                continue
            annotations = IAnnotations(context)
            if not 'pfwbged_history' in annotations:
                annotations['pfwbged_history'] = []
            value = getattr(context, field)
            annotations['pfwbged_history'].append({'time': DateTime(),
                'action_id': 'pfwbged_field',
                'action': _('New value for %s: %s') % (field, ', '.join(value)),
                'actor_name': api.user.get_current().getId(),
                'attribute': field,
                'value': value,
                })


@grok.subscribe(IFolder, IObjectAddedEvent)
@grok.subscribe(IDmsDocument, IObjectAddedEvent)
def set_owner_role_on_document(context, event):
    """Makes sure a new document gets its owner role set properly."""
    for creator in context.creators:
        context.manage_setLocalRoles(creator, ['Owner'])


@grok.subscribe(ITask, IObjectAddedEvent)
@grok.subscribe(IValidation, IObjectAddedEvent)
def set_permissions_on_task_on_add(context, event):
    '''Gives read access to a task for persons that are handling the document'''
    # go up in the acquisition chain to find the document
    document = None
    for obj in aq_chain(context):
        obj = aq_parent(obj)
        if IDmsDocument.providedBy(obj):
            document = obj
            break
    if not document:
        return

    with api.env.adopt_user('admin'):
        for user_id, roles in document.get_local_roles():
            if 'Reader' in roles or 'Editor' in roles:
                context.manage_addLocalRoles(user_id, ['Reader'])
                context.reindexObjectSecurity()
                context.reindexObject(idxs=['allowedRolesAndUsers'])

        document.reindexObject(idxs=['allowedRolesAndUsers'])


# not enabled for now, see #4516
#@grok.subscribe(IDmsDocument, IObjectModifiedEvent)
def set_permissions_on_task_from_doc(context, event):
    portal_catalog = api.portal.get_tool('portal_catalog')
    tasks = portal_catalog.unrestrictedSearchResults(
            portal_type=['task', 'validation'],
            path='/'.join(context.getPhysicalPath()))
    if not tasks:
        return

    for description in event.descriptions:
        if not hasattr(description, 'attributes'):
            continue
        for field in ('treated_by', 'treating_groups', 'recipient_groups'):
            if field in description.attributes:
                break
        else:
            return

    with api.env.adopt_user('admin'):
        tasks = [x.getObject() for x in tasks]
        user_ids = []
        for user_id, roles in document.get_local_roles():
            if 'Reader' in roles or 'Editor' in roles:
                user_ids.append(user_id)

        for task in tasks:
            for task_user_id, task_roles in task.get_local_roles():
                if 'Reader' in task_roles and task_user_id not in user_ids:
                    task.manage_delLocalRoles([task_user_id])
            for user_id in user_ids:
                task.manage_addLocalRoles(user_id, ['Reader'])
            task.reindexObjectSecurity()
            task.reindexObject(idxs=['allowedRolesAndUsers'])
