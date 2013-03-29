from five import grok

from plone import api

from collective.dms.mailcontent.dmsmail import IDmsOutgoingMail


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
