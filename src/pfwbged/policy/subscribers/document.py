from five import grok

from zope.lifecycleevent.interfaces import IObjectAddedEvent

from collective.z3cform.rolefield.field import LocalRolesToPrincipalsDataManager

from collective.dms.basecontent.dmsdocument import IDmsDocument
from collective.task.content.task import ITask
from collective.task.interfaces import IBaseTask


@grok.subscribe(IBaseTask, IObjectAddedEvent)
def set_role_on_document(context, event):
    if not ITask.providedBy(context):
        document = context.getParentNode()
        cansee_dm = LocalRolesToPrincipalsDataManager(document, IDmsDocument['recipient_groups'])
        cansee_dm.set(tuple(context.responsible))
    # do we have to set Editor role on document for ITask ? (if so, remove something for IDmsMail ?)
