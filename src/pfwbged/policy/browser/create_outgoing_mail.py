from Acquisition import aq_parent
from five import grok
from plone import api

from collective.dms.mailcontent.dmsmail import IDmsIncomingMail
from collective.task.content.task import ITask
from pfwbged.basecontent.types import IBoardDecision


class NoIDmsIncomingMailFound(Exception):
    """No IDmsIncomingMail found"""


class CreateOutgoingMailFromTask(grok.View):

    grok.name("create_outgoing_mail")
    grok.context(ITask)
    grok.require("zope2.View")

    def find_incomingmail(self):
        """Find the first IDmsIncomingMail in the acquisition chain"""
        parent = self.context
        while not IDmsIncomingMail.providedBy(parent):
            parent = aq_parent(parent)
            if parent is None:
                raise NoIDmsIncomingMailFound
        return parent

    def render(self):
        task = self.context
        incomingmail = self.find_incomingmail()
        container_path = '/'.join(incomingmail.getPhysicalPath())
        catalog = api.portal.get_tool("portal_catalog")
        brains = catalog.searchResults({"portal_type": "task",
                                        "path": container_path,
                                        "review_state": "in-progress"})

        values = {}
        values['title'] = u"Re: " + incomingmail.title
        values['recipients'] = u'/'.join(incomingmail.sender.to_object.getPhysicalPath())
        values['in_reply_to'] = u'/'.join(incomingmail.getPhysicalPath())
        values['treating_groups'] = task.responsible[0]
        values['related_task'] = u'/'.join(task.getPhysicalPath())
        values_url = u"""
form.widgets.IBasic.title=%(title)s&
form.widgets.recipients:list=%(recipients)s&
form.widgets.in_reply_to:list=%(in_reply_to)s&
form.widgets.IRelatedTask.related_task=%(related_task)s&
form.widgets.treating_groups=%(treating_groups)s""" % values
        if incomingmail.keywords:
            values_url += '&' + '&'.join([
                    'form.widgets.IPfwbDocument.keywords=%s' % x
                    for x in incomingmail.keywords])
        for principal, local_roles in incomingmail.get_local_roles():
            if 'Editor' in local_roles:
                values_url += '&' + 'form.widgets.treating_groups:list=%s' % principal
            if 'Reader' in local_roles:
                values_url += '&' + 'form.widgets.recipient_groups:list=%s' % principal

        folder_url = api.portal.get()['documents'].absolute_url()
        if incomingmail.portal_type == 'pfwb.apfincomingmail':
            outgoing_add_url = '/++add++pfwb.apfoutgoingmail?'
        else:
            outgoing_add_url = "/++add++dmsoutgoingmail?"
        url = folder_url + outgoing_add_url + values_url.encode('utf-8')
        self.request.response.redirect(url)


class CreateOutgoingMailFromBoardDecision(grok.View):

    grok.name("create_outgoing_mail")
    grok.context(IBoardDecision)
    grok.require("zope2.View")

    def render(self):
        decision = self.context

        values_params = [
            u'form.widgets.related_docs:list={}'.format(
                u'/'.join(decision.getPhysicalPath()),
            ),
        ]

        list_fields = {
            'treated_by': 'IPfwbDocument.treated_by',
            'treating_groups': 'treating_groups',
            'recipient_groups': 'recipient_groups',
            'keywords': 'IPfwbDocument.keywords',
        }
        for field_id, field_param_id in list_fields.items():
            field = getattr(decision, field_id, []) or []
            for item in field:
                values_params.append(
                    u'form.widgets.{}:list={}'.format(field_param_id, item)
                )

        documents_folder_url = api.portal.get()['documents'].absolute_url()
        encoded_params = "&".join(values_params).encode('utf-8')
        url = '{0}/++add++dmsoutgoingmail?{1}'.format(
            documents_folder_url,
            encoded_params,
        )
        self.request.response.redirect(url)
