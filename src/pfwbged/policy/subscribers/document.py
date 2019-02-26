import logging
import datetime

from Acquisition import aq_chain, aq_parent
from five import grok
from DateTime import DateTime

from zc.relation.interfaces import ICatalog
from zope.container.interfaces import INameChooser
from zope.i18n import translate, negotiate
from zope.component import getUtility
from zope.component.interfaces import ComponentLookupError
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent.interfaces import IObjectAddedEvent, IObjectModifiedEvent
from OFS.interfaces import IObjectWillBeRemovedEvent
from zope.annotation.interfaces import IAnnotations

from plone import api
from plone.stringinterp.adapters import _recursiveGetMembersFromIds

from Products.DCWorkflow.interfaces import IAfterTransitionEvent
from plone.app.discussion.interfaces import ICommentingTool, IConversation

from collective.z3cform.rolefield.field import LocalRolesToPrincipalsDataManager

from collective.dms.basecontent.dmsdocument import IDmsDocument
from collective.dms.basecontent.source import PrincipalSource
from collective.task.content.task import IBaseTask, ITask
from collective.task.content.validation import IValidation
from collective.task.content.information import IInformation
from collective.task.interfaces import IBaseTask
from collective.dms.basecontent.dmsfile import IDmsFile, IDmsAppendixFile
from pfwbged.folder.folder import IFolder

from pfwbged.basecontent.behaviors import IPfwbDocument
from pfwbged.policy import _

from mail import changeWorkflowState


try:
    from plone.app.async.interfaces import IAsyncService
except ImportError:
    IAsyncService = None


def has_pfwbgeddocument_workflow(obj):
    wtool = api.portal.get_tool('portal_workflow')
    return 'pfwbgeddocument_workflow' in wtool.getChainFor(obj)


def has_incomingmail_workflow(obj):
    wtool = api.portal.get_tool('portal_workflow')
    chain = wtool.getChainFor(obj)
    if 'incomingmail_workflow' in chain:
        return True
    if 'incomingapfmail_workflow' in chain:
        return True
    return False


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
    elif event.transition.id == 'cancel-validation':
        for ref in catalog.findRelations(query):
            validation = ref.from_object
            if api.content.get_state(validation) == 'validated':
                api.content.transition(validation, 'cancel-validation')
                validation.reindexObject(idxs=['review_state'])
    elif event.transition.id == 'cancel-refusal':
        for ref in catalog.findRelations(query):
            validation = ref.from_object
            if api.content.get_state(validation) == 'refused':
                api.content.transition(validation, 'cancel-refusal')
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
        try:
            api.content.transition(obj=document, transition='to_process')
        except api.exc.InvalidParameterError:
            pass
        else:
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
    elif event.transition and event.transition.id == 'return-responsibility':
        obj = aq_parent(context)
        if not IPfwbDocument.providedBy(obj):
            return
        # only applies to "other documents"
        if not has_pfwbgeddocument_workflow(obj):
            return
        document = obj
        api.content.transition(obj=document, transition='back_to_assigning')
        document.reindexObject(idxs=['review_state'])


def transition_tasks(obj, types, status, transition):
    portal_catalog = api.portal.get_tool('portal_catalog')
    tasks = portal_catalog.unrestrictedSearchResults(
            portal_type=types, path='/'.join(obj.getPhysicalPath()))
    for brain in tasks:
        task = brain._unrestrictedGetObject()
        if api.content.get_state(obj=task) == status:
            print 'changing task', task
            with api.env.adopt_user('admin'):
                api.content.transition(obj=task, transition=transition)
            task.reindexObject(idxs=['review_state'])


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
            elif state == "assigning":
                transition_tasks(document, types=('task'), status='todo', transition='take-responsibility')
                # the document is now in processing state because the task is in progress
                api.content.transition(obj=document, transition='process')
                document.reindexObject(idxs=['review_state'])

        if not has_incomingmail_workflow(document):
            # for all documents (but not incoming mails), we transition all
            # todo tasks to abandon.
            transition_tasks(obj=document, status='todo',
                    transition='abandon',
                    types=('opinion', 'validation', 'task',))
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
def document_is_finished(context, event):
    """When document is done for, abandon all tasks"""
    portal_catalog = api.portal.get_tool('portal_catalog')
    if event.new_state.id not in ('considered', 'noaction', 'sent'):
        return
    if has_incomingmail_workflow(context):
        return
    print 'document_is_finished'
    transition_tasks(obj=context, status='todo',
            transition='abandon',
            types=('task', 'opinion', 'validation'))


@grok.subscribe(IDmsDocument, IAfterTransitionEvent)
def document_is_reopened(context, event):
    """When a document is reoponed, create a new task"""
    if has_pfwbgeddocument_workflow(context) and event.transition is not None and event.new_state.id == 'assigning':

        # Task responsibility has just been returned
        if event.old_state.id == 'processing':
            return

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


def email_notification_of_tasks_sync(context, event, document, absolute_url, target_language=None):
    """Notify recipients of new tasks by email"""
    log = logging.getLogger('pfwbged.policy')
    log.info('sending notifications')
    document.reindexObject(idxs=['allowedRolesAndUsers'])

    for enquirer in (context.enquirer or []):
        member = context.portal_membership.getMemberById(enquirer)
        if member:
            email_from = member.getProperty('email', None)
            if email_from:
                break
    else:
        email_from = api.user.get_current().email or api.portal.get().getProperty('email_from_address') or 'admin@localhost'

    responsible_labels = []
    for responsible in (context.responsible or []):
        try:
            responsible_labels.append(
                    PrincipalSource(context).getTerm(responsible).title)
        except LookupError:
            pass
    responsible_label = ', '.join(responsible_labels)

    kwargs = {'target_language': target_language}
    subject = '%s - %s' % (context.title, document.title)
    body = translate(_('You received a request for action in the GED.'), **kwargs)

    if responsible_label:
        body += '\n\n' + translate(_('Assigned to: %s'), **kwargs) % responsible_label

    body += '\n\n' + \
            translate(_('Title: %s'), **kwargs) % context.title + \
            '\n\n' + \
            translate(_('Document: %s'), **kwargs) % document.title + \
            '\n\n' + \
            translate(_('Document Address: %s'), **kwargs) % absolute_url + \
            '\n\n'
    try:
        body += translate(_('Deadline: %s'), **kwargs) % context.deadline + '\n\n'
    except AttributeError:
        pass

    if context.note:
        body += translate(_('Note:'), **kwargs) + '\n\n' + context.note

    body += '\n\n\n-- \n' + translate(_('Sent by GED'), **kwargs)
    body = body.encode('utf-8')

    log.info('sending notifications to %r' % context.responsible)
    members = []
    for member in _recursiveGetMembersFromIds(api.portal.get(), (context.responsible or [])):
        email = member.getProperty('email', None)
        if not email:
            continue
        try:
            context.MailHost.send(body, email, email_from, subject, charset='utf-8')
        except Exception as e:
            # do not abort transaction in case of email error
            log = logging.getLogger('pfwbged.policy')
            log.exception(e)


@grok.subscribe(IBaseTask, IObjectAddedEvent)
def email_notification_of_tasks(context, event):
    # go up in the acquisition chain to find the document, this cannot be done
    # in the async job as absolute_url() needs the request object to give a
    # correct result
    document = None
    for obj in aq_chain(context):
        obj = aq_parent(obj)
        if IDmsDocument.providedBy(obj):
            document = obj
            break
    if not document:
        return
    absolute_url = document.absolute_url()

    # request is also required to get the target language
    target_language = negotiate(context.REQUEST)

    kwargs = {
        'context': context,
        'event': event,
        'document': document,
        'absolute_url': absolute_url,
        'target_language': target_language
    }

    if IAsyncService is None:
        return email_notification_of_tasks_sync(**kwargs)
    async = getUtility(IAsyncService)
    log = logging.getLogger('pfwbged.policy')
    log.info('sending notifications async')
    job = async.queueJob(email_notification_of_tasks_sync, **kwargs)


@grok.subscribe(IValidation, IAfterTransitionEvent)
def email_notification_of_validation_reversal(context, event):
    """Notify a validation requester when their previously validated
     (or refused) request has returned to pending state"""
    if not event.transition:
        return
    elif event.transition.id == 'cancel-validation':
        comment = translate(_('A previously validated version has returned to waiting validation'), context=context.REQUEST)
    elif event.transition.id == 'cancel-refusal':
        comment = translate(_('A previously refused version has returned to waiting validation'), context=context.REQUEST)
    else:
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

    email_from = api.user.get_current().email or api.portal.get().getProperty('email_from_address') or 'admin@localhost'

    subject = '%s - %s' % (context.title, document.title)

    body = comment + \
            '\n\n' + \
            translate(_('Title: %s'), context=context.REQUEST) % context.title + \
            '\n\n' + \
            translate(_('Document: %s'), context=context.REQUEST) % document.title + \
            '\n\n' + \
            translate(_('Document Address: %s'), context=context.REQUEST) % document.absolute_url()

    body += '\n\n\n-- \n' + translate(_('Sent by GED'))
    body = body.encode('utf-8')

    try:
        context.MailHost.send(body, email_enquirer, email_from, subject, charset='utf-8')
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

    email_from = api.user.get_current().email or api.portal.get().getProperty('email_from_address') or 'admin@localhost'

    subject = '%s - %s' % (context.title, document.title)

    body = translate(_('A validation request has been refused'), context=context.REQUEST) + \
            '\n\n' + \
            translate(_('Title: %s'), context=context.REQUEST) % context.title + \
            '\n\n' + \
            translate(_('Document: %s'), context=context.REQUEST) % document.title + \
            '\n\n' + \
            translate(_('Document Address: %s'), context=context.REQUEST) % document.absolute_url() + \
            '\n\n'

    conversation = IConversation(context)
    if conversation and conversation.getComments():
        last_comment = list(conversation.getComments())[-1]
        if (datetime.datetime.utcnow() - last_comment.creation_date).seconds < 120:
            # comment less than two minutes ago, include it.
            body += translate(_('Note:'), context=context.REQUEST) + '\n\n' + last_comment.text

    body += '\n\n\n-- \n' + translate(_('Sent by GED'))
    body = body.encode('utf-8')

    try:
        context.MailHost.send(body, email_enquirer, email_from, subject, charset='utf-8')
    except Exception as e:
        # do not abort transaction in case of email error
        log = logging.getLogger('pfwbged.policy')
        log.exception(e)


@grok.subscribe(ITask, IObjectWillBeRemovedEvent)
def email_notification_of_canceled_subtask(context, event):
    document = None
    for obj in aq_chain(context):
        obj = aq_parent(obj)
        if IDmsDocument.providedBy(obj):
            document = obj
            break
    if not document:
        return
    absolute_url = document.absolute_url()

    recipient_emails = []
    for recipient in _recursiveGetMembersFromIds(api.portal.get(), (context.responsible or [])):
        email = recipient.getProperty('email', None)
        if email:
            recipient_emails.append(email)

    if not recipient_emails:
        return

    email_from = api.user.get_current().email or api.portal.get().getProperty(
        'email_from_address') or 'admin@localhost'

    subject = '%s - %s' % (context.title, document.title)

    body = translate(_('One of your tasks has been cancelled'), context=context.REQUEST) + \
        '\n\n' + \
        translate(_('Title: %s'), context=context.REQUEST) % context.title + \
        '\n\n' + \
        translate(_('Document: %s'), context=context.REQUEST) % document.title + \
        '\n\n' + \
        translate(_('Document Address: %s'), context=context.REQUEST) % document.absolute_url() + \
        '\n\n\n\n-- \n' + \
        translate(_('Sent by GED'))
    body = body.encode('utf-8')

    for recipient_email in recipient_emails:
        try:
            context.MailHost.send(body, recipient_email, email_from, subject, charset='utf-8')
        except Exception as e:
            # do not abort transaction in case of email error
            log = logging.getLogger('pfwbged.policy')
            log.exception(e)


@grok.subscribe(IInformation, IObjectWillBeRemovedEvent)
def email_notification_of_canceled_information(context, event):
    document = None
    for obj in aq_chain(context):
        obj = aq_parent(obj)
        if IDmsDocument.providedBy(obj):
            document = obj
            break
    if not document:
        return
    absolute_url = document.absolute_url()

    responsible = context.responsible[0]
    principal = api.user.get(responsible)
    recipient_email = principal.getProperty('email') if principal else None
    if recipient_email:

        email_from = api.user.get_current().email or api.portal.get().getProperty(
            'email_from_address') or 'admin@localhost'

        subject = '%s - %s' % (context.title, document.title)

        body = translate(_('One document is not mentioned for your information anymore'), context=context.REQUEST) + \
            '\n\n' + \
            translate(_('Title: %s'), context=context.REQUEST) % context.title + \
            '\n\n' + \
            translate(_('Document: %s'), context=context.REQUEST) % document.title + \
            '\n\n' + \
            translate(_('Document Address: %s'), context=context.REQUEST) % document.absolute_url() + \
            '\n\n\n\n-- \n' + \
            translate(_('Sent by GED'))
        body = body.encode('utf-8')

        try:
            context.MailHost.send(body, recipient_email, email_from, subject, charset='utf-8')
        except Exception as e:
            # do not abort transaction in case of email error
            log = logging.getLogger('pfwbged.policy')
            log.exception(e)


@grok.subscribe(IValidation, IObjectWillBeRemovedEvent)
def email_notification_of_canceled_validation(context, event):
    document = None
    for obj in aq_chain(context):
        obj = aq_parent(obj)
        if IDmsDocument.providedBy(obj):
            document = obj
            break
    if not document:
        return
    absolute_url = document.absolute_url()

    recipient_emails = []
    for recipient in _recursiveGetMembersFromIds(api.portal.get(), (context.responsible or [])):
        email = recipient.getProperty('email', None)
        if email:
            recipient_emails.append(email)

    if not recipient_emails:
        return

    for enquirer in (context.enquirer or []):
        member = context.portal_membership.getMemberById(enquirer)
        if member:
            email_from = member.getProperty('email', None)
            if email_from:
                break
    else:
        email_from = api.user.get_current().email or api.portal.get().getProperty('email_from_address') or 'admin@localhost'

    subject = '%s - %s' % (context.title, document.title)

    body = translate(_('A validation request previously sent to you has been deleted'), context=context.REQUEST) + \
           '\n\n' + \
           translate(_('Title: %s'), context=context.REQUEST) % context.title + \
           '\n\n' + \
           translate(_('Document: %s'), context=context.REQUEST) % document.title + \
           '\n\n' + \
           translate(_('Document Address: %s'), context=context.REQUEST) % document.absolute_url() + \
           '\n\n\n\n-- \n' + \
           translate(_('Sent by GED'))
    body = body.encode('utf-8')

    for recipient_email in recipient_emails:
        try:
            context.MailHost.send(body, recipient_email, email_from, subject, charset='utf-8')
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
            # assign it back as a change to the list won't trigger the
            # annotation to be saved on disk.
            annotations['pfwbged_history'] = annotations['pfwbged_history'][:]


@grok.subscribe(IFolder, IObjectAddedEvent)
@grok.subscribe(IDmsDocument, IObjectAddedEvent)
def set_owner_role_on_document(context, event):
    """Makes sure a new document gets its owner role set properly."""
    for creator in context.creators:
        context.manage_setLocalRoles(creator, ['Owner'])


@grok.subscribe(IBaseTask, IObjectAddedEvent)
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

    if not hasattr(document, 'treated_by') or not document.treated_by:
        return

    with api.env.adopt_user('admin'):
        for user_id in document.treated_by:
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


@grok.subscribe(IDmsAppendixFile, IObjectAddedEvent)
@grok.subscribe(IDmsFile, IObjectAddedEvent)
def set_permissions_on_files_on_add(context, event):
    '''Gives read access to a version/appendix for persons that are handling
       the document'''
    # go up in the acquisition chain to find the document
    document = None
    for obj in aq_chain(context):
        obj = aq_parent(obj)
        if IDmsDocument.providedBy(obj):
            document = obj
            break
    if not document:
        return

    if not hasattr(document, 'treated_by') or not document.treated_by:
        return

    with api.env.adopt_user('admin'):
        for user_id in document.treated_by:
            context.manage_addLocalRoles(user_id, ['Reader', 'Reviewer'])
            context.reindexObjectSecurity()
            context.reindexObject(idxs=['allowedRolesAndUsers'])

        document.reindexObject(idxs=['allowedRolesAndUsers'])
