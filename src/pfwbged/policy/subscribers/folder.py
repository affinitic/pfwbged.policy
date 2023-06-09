import random

from five import grok
from zope import component

from Acquisition import aq_parent

from plone import api

from zope.app.intid.interfaces import IIntIds
from z3c.relationfield import RelationValue
from zope.lifecycleevent.interfaces import IObjectAddedEvent

from AccessControl.SecurityManagement import getSecurityManager
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import setSecurityManager
from zope.globalrequest import getRequest

from collective.dms.basecontent.dmsdocument import IDmsDocument
from pfwbged.folder.folder import IFolder

from ..interfaces import IDocumentsFolder
from .. import POOL_SIZE


@grok.subscribe(IFolder, IObjectAddedEvent)
@grok.subscribe(IDmsDocument, IObjectAddedEvent)
def move_to_proper_location(context, event):
    folder = context.getParentNode()
    if context.portal_type == 'pfwbgedfolder':
        if folder.id == 'Members' and aq_parent(folder).portal_type == 'Plone Site':
            # the folder is already in the right place, good
            return
        if folder.id == 'dossiers' and aq_parent(folder).portal_type == 'Plone Site':
            # the folder is already in the right place, good
            return

    # then move the document to the global pool folder
    clipboard = folder.manage_cutObjects([context.id])
    if context.portal_type == 'pfwbgedfolder':
        target_folder = api.portal.get().dossiers
    else:
        # for documents this is organized in subpools, pick one at random
        subfolder_id = '%04d' % random.randint(0, POOL_SIZE-1)
        target_folder = api.portal.get().documents[subfolder_id]

    # move the object using the admin security context, this allows permissions
    # to be kept intact on folders, instead of requiring "Delete objects",
    # which we do not one, because things shouldn't be removable by anybody but
    # the admin.
    admin_user = aq_parent(api.portal.get()).acl_users.getUserById('admin')
    old_security_manager = getSecurityManager()
    newSecurityManager(getRequest(), admin_user)
    result = target_folder.manage_pasteObjects(clipboard)
    setSecurityManager(old_security_manager)

    # makes sure original object is deleted
    try:
        folder.manage_delObjects([context.id])
    except AttributeError:
        pass

    new_url = target_folder.absolute_url() + '/' + result[0]['new_id']
    context.REQUEST.response.redirect(new_url, lock=True)

    new_context = target_folder[result[0]['new_id']]
    if IFolder.providedBy(folder):
        # add a link to classifying folder
        intids = component.getUtility(IIntIds)
        link = new_context.invokeFactory('pfwbgedlink', 'pfwbgedlink-0',
                folder=RelationValue(intids.getId(folder)))


    from document import create_task_after_creation
    create_task_after_creation(new_context, event)
