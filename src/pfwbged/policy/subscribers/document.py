from Acquisition import aq_parent
from five import grok

from zc.relation.interfaces import ICatalog
from zope.component import getUtility
from zope.component.interfaces import ComponentLookupError
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent.interfaces import IObjectAddedEvent
from OFS.interfaces import IObjectWillBeRemovedEvent

from plone import api

from Products.DCWorkflow.interfaces import IAfterTransitionEvent

from collective.z3cform.rolefield.field import LocalRolesToPrincipalsDataManager

from collective.dms.basecontent.dmsdocument import IDmsDocument
from collective.task.content.task import ITask
from collective.task.content.validation import IValidation
from collective.task.interfaces import IBaseTask
from collective.dms.basecontent.dmsfile import IDmsFile


@grok.subscribe(IBaseTask, IObjectAddedEvent)
def set_role_on_document(context, event):
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
    intids = getUtility(IIntIds)
    catalog = getUtility(ICatalog)
    version_intid = intids.getId(context)
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
    """Delete validations and opinions when a version is deleted"""
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
