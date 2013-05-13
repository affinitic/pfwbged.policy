from Acquisition import aq_chain, aq_parent
from zope.component import getUtility
from zc.relation.interfaces import ICatalog
from zope.intid.interfaces import IIntIds
from zope.i18n import translate
from five import grok

from plone.app.layout.viewlets.interfaces import (
        IBelowContentBody, IAboveContentBody)

from pfwbged.policy.interfaces import IIncomingMailAttributed
from collective.task.content.task import ITask

from collective.dms.mailcontent.dmsmail import IDmsIncomingMail
from collective.dms.basecontent.dmsdocument import IDmsDocument
from Products.CMFCore.utils import getToolByName

from pfwbged.policy import _


class CreateOutgoingMailViewlet(grok.Viewlet):
    grok.context(ITask)
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
        # first_task is the task created by the to_assign transition
        # from incoming mail workflow
        first_task = self.context
        for obj in aq_chain(self.context):
            obj = aq_parent(obj)
            if IDmsIncomingMail.providedBy(obj):
                break

            first_task = obj

        if (not IDmsIncomingMail.providedBy(obj) or
            not IIncomingMailAttributed.providedBy(first_task)):
            return

        incomingmail = obj
        task = self.context
        wtool = getToolByName(self.context, "portal_workflow")
        task_state = wtool.getInfoFor(task, 'review_state')
        if task_state == 'in-progress' and not self.is_outgoingmail_created(incomingmail):
            self.show_button = True
            self.portal_url = getToolByName(self.context, "portal_url")()
            self.title = "Re: " + incomingmail.title
            self.recipients = '/'.join(incomingmail.sender.to_object.getPhysicalPath())
            self.in_reply_to = '/'.join(incomingmail.getPhysicalPath())
            self.treating_groups = self.context.responsible[0]


class GoBackToDocumentViewlet(grok.Viewlet):
    grok.context(ITask)
    grok.viewletmanager(IAboveContentBody)

    def render(self):
        for obj in aq_chain(self.context):
            obj = aq_parent(obj)
            if IDmsDocument.providedBy(obj):
                break

        if not IDmsDocument.providedBy(obj):
            return u""

        title = translate(_(u"Go back to document"), context=self.request)
        return u"""<a href="%s">%s</a>""" % (obj.absolute_url(), title)
