from zope.component import getUtility
from zope.intid.interfaces import IIntIds
from zc.relation.interfaces import ICatalog

from five import grok

from plone import api

from collective.dms.mailcontent.dmsmail import IDmsOutgoingMail,\
    IDmsIncomingMail


class OutgoingMailReadyToSend(grok.View):
    """Guard that returns True if ready to send transition is permitted
    It is permitted if the outgoing mail contains a finalized version note
    """
    grok.name("ready_to_send")
    grok.context(IDmsOutgoingMail)
    grok.require("zope2.View")

    def render(self):
        catalog = api.portal.get_tool('portal_catalog')
        container_path = '/'.join(self.context.getPhysicalPath())
        results = catalog.searchResults({'path': {'query': container_path},
                                         'portal_type': 'dmsmainfile',
                                         'review_state': 'finished'})
        return bool(results)


class CanAnswerIncomingMail(grok.View):
    """Guard that check if the incoming mail can be answered
    (i.e. has an sent related doc)
    """
    grok.name('can_answer')
    grok.context(IDmsIncomingMail)
    grok.require('zope2.View')

    def render(self):
        refs_catalog = getUtility(ICatalog)
        intids = getUtility(IIntIds)
        mail_id = intids.getId(self.context)
        for ref in refs_catalog.findRelations({'to_id': mail_id}):
            outgoing_mail = ref.from_object
            if api.content.get_state(obj=outgoing_mail) == 'sent':
                return True
        return False
