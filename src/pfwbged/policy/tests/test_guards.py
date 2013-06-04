import os.path

from zope.component import getUtility
from zope.intid.interfaces import IIntIds
from z3c.relationfield.relation import RelationValue

from plone import api

from ecreall.helpers.testing.workflow import BaseWorkflowTest

from ..testing import IntegrationTestCase


TEST_DOCUMENT = os.path.join(os.path.dirname(__file__), 'document-test.odt')


class TestGuards(IntegrationTestCase, BaseWorkflowTest):
    """Tests pfwbged.policy guards"""

    def setUp(self):
        super(TestGuards, self).setUp()
        intids = getUtility(IIntIds)
        self.login('manager')
        portal = api.portal.get()
        folder = portal['folder']
        self.incomingmail = api.content.create(container=folder,
                                               type="dmsincomingmail",
                                               title="Incoming mail",
                                               treating_groups="editor",
                                               recipient_groups="reader",
                                               )
        incomingmail_id = intids.getId(self.incomingmail)
        self.outgoingmail = api.content.create(container=folder,
                                               type='dmsoutgoingmail',
                                               title="Outgoing mail",
                                               treating_groups="editor",
                                               recipient_groups="reader",
                                               in_reply_to=[RelationValue(incomingmail_id)],
                                               )

    def test_ready_to_send(self):
        mail = self.outgoingmail
        result = mail.restrictedTraverse('@@ready_to_send')()
        self.assertEqual(result, False)
        version1 = api.content.create(container=mail,
                                      type='dmsmainfile',
                                      title="Version 1")
        api.content.transition(obj=version1, transition='submit')
        api.content.transition(obj=version1, transition='validate')
        version2 = api.content.create(container=mail,
                                      type='dmsmainfile',
                                      title="Version 2")
        result = mail.restrictedTraverse('@@ready_to_send')()
        self.assertEqual(result, False)
        version3 = api.content.create(container=mail,
                                      type='dmsmainfile',
                                      title="Version 3")
        api.content.transition(obj=version3, transition='finish_without_validation')
        result = mail.restrictedTraverse('@@ready_to_send')()
        self.assertEqual(result, True)

    def test_can_answer(self):
        mail = self.incomingmail
        outgoingmail = self.outgoingmail
        can_answer = mail.restrictedTraverse('@@can_answer')
        self.assertEqual(can_answer(), False)
        # create a version for outgoing mail
        version1 = api.content.create(container=outgoingmail,
                                      type='dmsmainfile',
                                      title="Version 1")
        self.assertEqual(can_answer(), False)
        api.content.transition(obj=version1, transition='finish_without_validation')
        self.assertEqual(can_answer(), False)
        # send the outgoing mail
        api.content.transition(obj=outgoingmail, transition='send')
        self.assertEqual(can_answer(), True)

    def test_document_guards(self):
        """Test guards for pfwbgeddocument_workflow transitions"""
        self.login('manager')
        portal = api.portal.get()
        folder = portal['folder']
        doc = api.content.create(container=folder,
                                 type='dmsdocument',
                                 title="Document",
                                 treating_groups="editor",
                                 recipient_groups="reader")
        api.user.grant_roles(username='editor', obj=doc, roles=['Editor'])
        api.user.grant_roles(username='reader', obj=doc, roles=['Reader'])
        self.login('reader')
        with self.assertRaises(api.exc.InvalidParameterError):
            api.content.transition(obj=doc, transition='declare-acceptable')
        self.assertHasState(doc, 'published')

        self.login('editor')
        with self.assertRaises(api.exc.InvalidParameterError):
            api.content.transition(obj=doc, transition='declare-acceptable')
        self.assertHasState(doc, 'published')

        self.login('greffier')
        api.content.transition(obj=doc, transition='declare-acceptable')
        self.assertHasState(doc, 'acceptable')
