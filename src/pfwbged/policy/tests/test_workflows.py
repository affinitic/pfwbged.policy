# -*- coding: utf8 -*-

from plone import api

from ecreall.helpers.testing.workflow import BaseWorkflowTest

from ..testing import IntegrationTestCase
from ..testing import USERDEFS


INCOMINGMAIL_PERMISSIONS = {'registering': {},
                            'assigning': {},
                            'noaction': {},
                            'processing': {},
                            'answered': {},
                            }

INCOMINGMAIL_TRACK = [('', 'registering'),
                      ('to_assign', 'assigning'),
                      ('back_to_registering', 'registering'),
                      ('to_assign', 'assigning'),
                      ('directly_noaction', 'noaction'),
                      ('back_to_assigning', 'assigning'),
                      ('to_process', 'processing'),
                      ('to_noaction', 'noaction'),
                      ('back_to_assigning', 'assigning'),
                      ('to_process', 'processing'),
                      ('answer', 'answered'),
                      ]

OUTGOINGMAIL_PERMISSIONS = {
    'writing': {'Access contents information': ('manager', 'editor', 'reader', 'greffier'),
                'View': ('manager', 'editor', 'reader', 'greffier'),
                'Modify portal content': ('manager', 'editor'),
                },
    'ready_to_send': {'Access contents information': ('manager', 'editor', 'reader', 'greffier'),
                      'View': ('manager', 'editor', 'reader', 'greffier'),
                      'Modify portal content': ('manager', 'editor'),
                    },
    'sent': {'Access contents information': ('manager', 'editor', 'reader', 'greffier'),
             'View': ('manager', 'editor', 'reader', 'greffier'),
             'Modify portal content': ('manager', 'editor'),
             },
    }

OUTGOINGMAIL_TRACK = [('', 'writing'),
                      ('finish', 'ready_to_send'),
                      ('send', 'sent'),
                      ]

DOCUMENT_PERMISSIONS = {
    'published': {'View': ('manager',
                           'editor',
                           'reader',
                           'greffier'),
                  'Modify portal content': ('manager',
                                            'editor',
                                            'greffier'),
                  'Access contents information': ('manager',
                                                  'editor',
                                                  'reader',
                                                  'greffier'),
                  },
    'acceptable': {'View': ('manager',
                           'editor',
                           'reader',
                           'greffier'),
                   'Modify portal content': ('manager',
                                             'editor',
                                             'greffier'),
                   'Access contents information': ('manager',
                                                   'editor',
                                                   'reader',
                                                   'greffier'),
                  },
    }

DOCUMENT_TRACK = [('', 'published'),
                  ('declare-acceptable', 'acceptable')]


VERSIONNOTE_PERMISSIONS = {}
VERSIONNOTE_TRACK = []


class TestSecurity(IntegrationTestCase, BaseWorkflowTest):
    """Tests pfwbged.policy workflows"""

    def setUp(self):
        super(TestSecurity, self).setUp()

    def test_everyone_is_contributor(self):
        self.login('reader')
        self.assertIn('Contributor', api.user.get_roles(username='reader'))
        portal = api.portal.get()
        params = {'title': "My Document"}
        portal.invokeFactory('pfwbdocument', 'mydoc', **params)

    def test_incomingmail_workflow(self):
        self.login('manager')
        portal = api.portal.get()
        folder = portal['folder']
        sgt_pepper = portal['mydirectory']['pepper']['sergent_pepper']

        incomingmail = api.content.create(container=folder,
                                          type='dmsincomingmail',
                                          title="Incoming mail",
                                          sender=sgt_pepper,
                                          treating_groups=['editor'],
                                          recipient_groups=['reader'],
                                          )

        api.user.grant_roles(username='editor', obj=incomingmail, roles=['Editor'])
        api.user.grant_roles(username='reader', obj=incomingmail, roles=['Reader'])

        for (transition, state) in INCOMINGMAIL_TRACK:
            if transition:
                api.content.transition(obj=incomingmail, transition=transition)
            if state:
                self.assertHasState(incomingmail, state)
                self.assertCheckPermissions(incomingmail, INCOMINGMAIL_PERMISSIONS[state],
                                            USERDEFS, stateid=state)

    def test_outgoingmail_workflow(self):
        self.login('manager')
        portal = api.portal.get()
        folder = portal['folder']

        outgoingmail = api.content.create(container=folder,
                                          type='dmsoutgoingmail',
                                          title="Outgoing mail",
                                          treating_groups="editor",
                                          recipient_groups="reader",
                                          )
        api.user.grant_roles(username='editor', obj=outgoingmail, roles=['Editor'])
        api.user.grant_roles(username='reader', obj=outgoingmail, roles=['Reader'])

        for (transition, state) in OUTGOINGMAIL_TRACK:
            if transition:
                if transition == 'finish':
                    version = api.content.create(container=outgoingmail,
                                                 type='dmsmainfile',
                                                 title="Version")
                    api.content.transition(obj=version, transition='finish_without_validation')
                else:
                    api.content.transition(obj=outgoingmail, transition=transition)
            if state:
                self.assertHasState(outgoingmail, state)
                self.assertCheckPermissions(outgoingmail, OUTGOINGMAIL_PERMISSIONS[state],
                                            USERDEFS, stateid=state)

    def test_document_workflow(self):
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

        for (transition, state) in DOCUMENT_TRACK:
            if transition:
                api.content.transition(obj=doc, transition=transition)
            if state:
                self.assertHasState(doc, state)
                self.assertCheckPermissions(doc, DOCUMENT_PERMISSIONS[state],
                                            USERDEFS, stateid=state)


    def __TODO_test_versionnote_workflow(self):
        pass
