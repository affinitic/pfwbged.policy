from zope.component import getUtility
from zc.relation.interfaces import ICatalog
from zope.intid.interfaces import IIntIds
from Acquisition import aq_chain, aq_parent
from five import grok

from plone.app.layout.viewlets.interfaces import IBelowContentBody

from pfwbged.policy.interfaces import IIncomingMailAttributed

from collective.dms.mailcontent.dmsmail import IDmsIncomingMail
from Products.CMFCore.utils import getToolByName


class CreateOutgoingMailViewlet(grok.Viewlet):
    grok.context(IIncomingMailAttributed)
    template = grok.PageTemplateFile("templates/createoutgoingmail.pt")
    grok.viewletmanager(IBelowContentBody)
    show_button = False

    def is_outgoingmail_created(self, incomingmail):
        intids = getUtility(IIntIds)
        catalog = getUtility(ICatalog)
        refs = []
        try:
            doc_intid = intids.getId(incomingmail)
        except KeyError:
            pass
        else:
            for ref in catalog.findRelations({'to_id': doc_intid}):
                tp = (ref.from_path, ref.from_object.Title())
                if tp not in refs:
                    refs.append(tp)
        return len(refs)

    def update(self):
        for obj in aq_chain(self.context):
            obj = aq_parent(obj)
            if IDmsIncomingMail.providedBy(obj):
                break

        incomingmail = obj
        wtool = getToolByName(self.context, "portal_workflow")
        review_state = wtool.getInfoFor(self.context, 'review_state')
        if review_state == 'in-progress' and not self.is_outgoingmail_created(incomingmail):
            self.show_button = True
            self.portal_url = getToolByName(self.context, "portal_url")()
            self.title = "Re: " + incomingmail.title
            self.recipients = '/'.join(incomingmail.sender.to_object.getPhysicalPath())
            self.in_reply_to = '/'.join(incomingmail.getPhysicalPath())
            self.treating_groups = self.context.responsible[0]
