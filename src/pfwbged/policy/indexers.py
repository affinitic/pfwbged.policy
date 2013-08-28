from five import grok
from plone.indexer import indexer
from plone import api

from collective.dms.basecontent.dmsdocument import IDmsDocument

@indexer(IDmsDocument)
def has_final_unsigned_version(obj, **kw):
    result = False
    for child in reversed(obj.values()):
        if child.portal_type != 'dmsmainfile':
            continue
        if child.signed is True:
            return False
        if api.content.get_state(child) == 'finished':
            result = True
    return result

grok.global_adapter(has_final_unsigned_version, name='has_final_unsigned_version')
