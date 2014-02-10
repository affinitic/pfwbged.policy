import random

from five import grok
from zope import component

from Acquisition import aq_parent

from plone import api

from zope.app.intid.interfaces import IIntIds
from z3c.relationfield import RelationValue
from zope.lifecycleevent.interfaces import IObjectAddedEvent

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

    if IFolder.providedBy(folder):
        # add a link to classifying folder
        intids = component.getUtility(IIntIds)
        link = context.invokeFactory('pfwbgedlink', 'pfwbgedlink-0',
                folder=RelationValue(intids.getId(folder)))

    # then move the document to the global pool folder
    clipboard = folder.manage_cutObjects([context.id])
    if context.portal_type == 'pfwbgedfolder':
        target_folder = api.portal.get().dossiers
    else:
        # for documents this is organized in subpools, pick one at random
        subfolder_id = '%04d' % random.randint(0, POOL_SIZE-1)
        target_folder = api.portal.get().documents[subfolder_id]

    result = target_folder.manage_pasteObjects(clipboard)

    # makes sure original object is deleted
    try:
        folder.manage_delObjects([context.id])
    except AttributeError:
        pass

    new_url = target_folder.absolute_url() + '/' + result[0]['new_id']
    context.REQUEST.response.redirect(new_url, lock=True)
