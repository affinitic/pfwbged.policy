import os.path

from plone import api

from ecreall.helpers.testing.workflow import BaseWorkflowTest

from ..testing import IntegrationTestCase


TEST_DOCUMENT = os.path.join(os.path.dirname(__file__), 'document-test.odt')


class TestGuards(IntegrationTestCase, BaseWorkflowTest):
    """Tests pfwbged.policy guards"""

    def setUp(self):
        super(TestGuards, self).setUp()
        self.login('manager')
        portal = api.portal.get()
        folder = portal['folder']
        self.outgoingmail = api.content.create(container=folder,
                                               type='dmsoutgoingmail',
                                               title="Outgoing mail",
                                               treating_groups="editor",
                                               recipient_groups="reader",
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

    def test_document_guards(self):
        """Test guards for pfwbgeddocument_workflow transitions"""
        self.login('manager')
        portal = api.portal.get()
        folder = portal['folder']
        doc = api.content.create(container=folder,
                                 type='pfwbdocument',
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
