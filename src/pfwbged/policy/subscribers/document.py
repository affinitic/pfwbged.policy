from Acquisition import aq_chain, aq_parent
from five import grok

from zc.relation.interfaces import ICatalog
from zope.container.interfaces import INameChooser
from zope.i18n import translate
from zope.component import getUtility
from zope.component.interfaces import ComponentLookupError
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent.interfaces import IObjectAddedEvent
from OFS.interfaces import IObjectWillBeRemovedEvent

from plone import api

from Products.DCWorkflow.interfaces import IAfterTransitionEvent

from collective.z3cform.rolefield.field import LocalRolesToPrincipalsDataManager

from collective.dms.basecontent.dmsdocument import IDmsDocument
from collective.task.content.task import IBaseTask, ITask
from collective.task.content.validation import IValidation
from collective.task.interfaces import IBaseTask
from collective.dms.basecontent.dmsfile import IDmsFile

from pfwbged.basecontent.behaviors import IPfwbDocument
from pfwbged.policy import _


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
            new_recipients = tuple(frozenset(document.recipient_groups) | frozenset(context.responsible))
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
@grok.subscribe(IPfwbDocument, IObjectAddedEvent)
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
        if document.portal_type == 'dmsoutgoingmail' and state == 'writing':
            api.content.transition(obj=document, transition='finish')
            document.reindexObject(idxs=['review_state'])
        elif IPfwbDocument.providedBy(document) and has_pfwbgeddocument_workflow(document):
            if state == 'processing':
                api.content.transition(obj=document, transition='process')
                document.reindexObject(idxs=['review_state'])
            elif state == "assigning":
                tasks = portal_catalog.unrestrictedSearchResults(portal_type='task',
                                                                 path='/'.join(document.getPhysicalPath()))
                for brain in tasks:
                    task = brain._unrestrictedGetObject()
                    if api.content.get_state(obj=task) == 'todo':
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


@grok.subscribe(IPfwbDocument, IAfterTransitionEvent)
def document_is_processed(context, event):
    """When document is processed, close all tasks"""
    portal_catalog = api.portal.get_tool('portal_catalog')
    if has_pfwbgeddocument_workflow(context) and event.new_state.id not in ('processing',):
        tasks = portal_catalog.unrestrictedSearchResults(portal_type='task',
                                                         path='/'.join(context.getPhysicalPath()))
        for brain in tasks:
            task = brain._unrestrictedGetObject()
            if api.content.get_state(obj=task) == 'in-progress':
                api.content.transition(obj=task, transition='mark-as-done')
                task.reindexObject(idxs=['review_state'])


@grok.subscribe(IPfwbDocument, IAfterTransitionEvent)
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
        if IPfwbDocument.providedBy(obj):
            document = obj
            break
    if not document:
        return

    for enquirer in (context.enquirer or []):
        member = context.portal_membership.getMemberById(responsible)
        if member:
            email_from = member.getProperty('email', None)
            if email_from:
                break
    else:
        email_from = api.user.get_current().email or 'admin@localhost'

    subject = '%s - %s' % (context.title, document.title)
    body = _("""You received a request for action in the GED.

Title: %(task_title)s

Document: %(document_title)s

Document Address: %(url)s

Deadline: %(deadline)s

Note:

%(note)s

""") % {'url': document.absolute_url(),
        'task_title': context.title,
        'document_title': document.title,
        'deadline': context.deadline,
        'note': context.note or '---'}

    for responsible in context.responsible:
        member = context.portal_membership.getMemberById(responsible)
        if not member:
            continue
        email = member.getProperty('email', None)
        context.MailHost.send(body, email, email_from, subject)
