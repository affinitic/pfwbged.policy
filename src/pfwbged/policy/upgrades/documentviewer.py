import logging
import os
import transaction

from BTrees.OOBTree import OOBTree
from DateTime import DateTime
from Products.CMFCore.utils import getToolByName
from collective.documentviewer.convert import saveFileToBlob
from collective.documentviewer.settings import Settings
from collective.documentviewer.settings import GlobalSettings
from plone import api


logger = logging.getLogger('pfwbged.policy')


def commit_transaction(msg):
    logger.info(msg)
    transaction.get().note(msg)
    transaction.commit()


def migrate_documentviewer_files_to_blobs(context):
    portal = api.portal.get()
    file_storage_root_folder = GlobalSettings(portal).storage_location
    catalog = getToolByName(context, 'portal_catalog')
    modified_counter = 0

    for brain in catalog(portal_type='dmsmainfile', sort_on='created'):
        obj = brain.getObject()
        settings = Settings(obj)
        if settings.storage_type == 'File' and not getattr(settings, 'blob_files'):
            if migrate_dmsfile_to_blobs(settings, file_storage_root_folder):
                modified_counter += 1
        if modified_counter and modified_counter % 1000 == 0:
            commit_transaction('Committing after migrating {} files to blobs ...'.format(modified_counter))

    commit_transaction('Committing after last file migration ...')
    logger.info('{} files were migrated to blobs.'.format(modified_counter))


def migrate_dmsfile_to_blobs(settings, file_storage_root_folder):
    uid = settings.context.UID()
    dmsfile_base_folder = os.path.join(file_storage_root_folder, uid[0], uid[1], uid)
    if not os.path.exists(dmsfile_base_folder):
        logger.error("can't migrate DmsFile {} to blob - missing storage folder".format(uid))
        return
    blob_files = OOBTree()

    for size in ('large', 'normal', 'small'):
        dmsfile_size_folder = os.path.join(dmsfile_base_folder, size)
        if not os.path.exists(dmsfile_size_folder):
            logger.error("can't migrate DmsFile {0} to blob - missing size folder: {1}".format(uid, dmsfile_size_folder))
            return
        for filename in os.listdir(dmsfile_size_folder):
            filepath = os.path.join(dmsfile_size_folder, filename)
            filename = '%s/%s' % (size, filename)
            blob_files[filename] = saveFileToBlob(filepath)

    settings.blob_files = blob_files
    settings.storage_type = 'Blob'
    settings.last_updated = DateTime().ISO8601()

    return True
