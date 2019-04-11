from five import grok
from plone.indexer import indexer
from plone import api
from Products.CMFCore.utils import getToolByName

from collective.dms.basecontent.dmsdocument import IDmsDocument

@indexer(IDmsDocument)
def has_final_unsigned_version(obj, **kw):
    result = False
    for child in reversed(obj.values()):
        if child.portal_type != 'dmsmainfile':
            continue
        if child.signed is True:
            return False
        try:
            result = (api.content.get_state(child) == 'finished')
        except:
            pass
    return result

grok.global_adapter(has_final_unsigned_version, name='has_final_unsigned_version')

@indexer(IDmsDocument)
def sender_as_text(obj, **kw):
    if not hasattr(obj, 'sender') or not obj.sender:
        return None
    return obj.sender.to_object.get_full_title()

grok.global_adapter(sender_as_text, name='sender_as_text')


@indexer(IDmsDocument)
def recipients_as_text(obj, **kw):
    if not hasattr(obj, 'recipients') or not obj.recipients:
        return ''
    return ' / '.join([x.to_object.get_full_title() for x in obj.recipients])

grok.global_adapter(recipients_as_text, name='recipients_as_text')


@indexer(IDmsDocument)
def can_last_version_validate(obj, **kw):
    with api.env.adopt_user('admin'):
        for child in reversed(obj.values()):
            if child.portal_type != 'dmsmainfile':
                continue
            if api.content.get_state(child) == 'trashed':
                continue
            wf_tool = getToolByName(obj, 'portal_workflow')
            workflowActions = wf_tool.listActionInfos(object=child)
            return bool('submit' in [x.get('id') for x in workflowActions])
        return False
grok.global_adapter(can_last_version_validate, name='can_last_version_validate')


@indexer(IDmsDocument)
def has_last_version_accept(obj, **kw):
    with api.env.adopt_user('admin'):
        last_version = None
        wf_tool = getToolByName(obj, 'portal_workflow')
        for child in reversed(obj.values()):
            if child.portal_type != 'dmsmainfile':
                continue
            if api.content.get_state(child) == 'trashed':
                continue
            last_version = child
            for task in reversed(obj.values()):
                if task.portal_type != 'validation':
                    continue
                if task.target.to_object.Title() != last_version.Title():
                    continue
                workflowActions = wf_tool.listActionInfos(object=task)
                return bool('validate' in [x.get('id') for x in workflowActions])
            break
        return False
grok.global_adapter(has_last_version_accept, name='has_last_version_accept')


@indexer(IDmsDocument)
def has_last_version_refuse(obj, **kw):
    with api.env.adopt_user('admin'):
        last_version = None
        wf_tool = getToolByName(obj, 'portal_workflow')
        for child in reversed(obj.values()):
            if child.portal_type != 'dmsmainfile':
                continue
            if api.content.get_state(child) == 'trashed':
                continue
            last_version = child
            for task in reversed(obj.values()):
                if task.portal_type != 'validation':
                    continue
                if task.target.to_object.Title() != last_version.Title():
                    continue
                workflowActions = wf_tool.listActionInfos(object=task)
                return bool('refuse' in [x.get('id') for x in workflowActions])
            break
        return False
grok.global_adapter(has_last_version_refuse, name='has_last_version_refuse')


def reindex_after_version_changes(document):
    if IDmsDocument.providedBy(document):
        document.reindexObject(idxs=['can_last_version_validate',
                                     'has_last_version_accept',
                                     'has_last_version_refuse'])
