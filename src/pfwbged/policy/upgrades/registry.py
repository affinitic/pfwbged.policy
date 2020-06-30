from pfwbged.policy import _
from plone.registry.interfaces import IRegistry
from plone.registry import field
from plone.registry import Record
from plone import api
from zope.component import getUtility


def setup_mail_reader_group(context):
    record_id = u'pfwbged.mail_reader_group'
    group_id = "lecture-courriers"
    group_name = u"Lecture courriers"

    registry = getUtility(IRegistry)
    if record_id not in registry.records:
        group = field.ASCIILine(
            title=_(u"Mail reader user group"),
            description=_(u"Members of this group can read all incoming and outgoing mails on the platform."),
            required=True,
            default=group_id,
        )
        registry.records[record_id] = Record(group)

    if not api.group.get(group_id):
        api.group.create(group_id, group_name)
