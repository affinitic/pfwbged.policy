# -*- coding: utf8 -*-
import datetime
from zope.component import getUtility
from zope.interface import alsoProvides
from zope.intid.interfaces import IIntIds
from z3c.relationfield.relation import RelationValue

from Products.CMFCore.WorkflowCore import WorkflowException
from plone import api

from ecreall.helpers.testing.workflow import BaseWorkflowTest

from pfwbged.policy.interfaces import IIncomingMailAttributed
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
                      ]

OUTGOINGMAIL_PERMISSIONS = {
    'writing': {'Access contents information': ('manager', 'editor', 'reader', 'greffier'),
                'View': ('manager', 'editor', 'reader', 'greffier'),
                'Modify portal content': ('manager', 'editor', 'greffier'),
                },
    'ready_to_send': {'Access contents information': ('manager', 'editor', 'reader', 'greffier'),
                      'View': ('manager', 'editor', 'reader', 'greffier'),
                      'Modify portal content': ('manager', 'editor', 'greffier'),
                    },
    'sent': {'Access contents information': ('manager', 'editor', 'reader', 'greffier'),
             'View': ('manager', 'editor', 'reader', 'greffier'),
             'Modify portal content': ('manager', 'editor', 'greffier'),
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
        portal.invokeFactory('dmsdocument', 'mydoc', **params)

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
                                          treated_by=[],
                                          in_copy=[],
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
        self.assertHasState(incomingmail, 'processing')
        wf_tool = api.portal.get_tool('portal_workflow')
        with self.assertRaises(WorkflowException):
            wf_tool.doActionFor(incomingmail, 'answer')

    def test_outgoingmail_workflow(self):
        self.login('manager')
        portal = api.portal.get()
        folder = portal['folder']

        outgoingmail = api.content.create(container=folder,
                                          type='dmsoutgoingmail',
                                          title="Outgoing mail",
                                          treating_groups=["editor"],
                                          recipient_groups=["reader"],
                                          treated_by=[],
                                          in_copy=[],
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
                                 type='dmsdocument',
                                 title="Document",
                                 treating_groups="editor",
                                 recipient_groups="reader",
                                 treated_by=[],
                                 in_copy=[],
                                 )
        api.user.grant_roles(username='editor', obj=doc, roles=['Editor'])
        api.user.grant_roles(username='reader', obj=doc, roles=['Reader'])

        for (transition, state) in DOCUMENT_TRACK:
            if transition:
                api.content.transition(obj=doc, transition=transition)
            if state:
                self.assertHasState(doc, state)
                self.assertCheckPermissions(doc, DOCUMENT_PERMISSIONS[state],
                                            USERDEFS, stateid=state)

    def test_delete_mail_with_subtasks(self):
        """Test delete mail with task and subtasks"""
        self.login('manager')
        portal = api.portal.get()
        folder = portal['folder']
        api.content.create(container=folder, type='dmsincomingmail',
                           id='mymail', title="My mail",
                           treated_by=["editor"],
                           treating_groups=[],
                           in_copy=[],
                           recipient_groups=[])
        mymail = folder['mymail']
        api.user.grant_roles(username='editor', obj=mymail, roles=['Editor'])
        api.content.transition(obj=mymail, transition='to_assign')
        api.content.transition(obj=mymail, transition='to_process')
        task = mymail['process-mail']
        api.content.transition(obj=task, transition='attribute')
        self.assertEqual(mymail.treating_groups, mymail.treated_by)
        api.content.create(container=task, type='task', id='subtask1', title="Subtask 1")
        subtask1 = task['subtask1']
        api.content.transition(obj=subtask1, transition='ask-for-refusal')
        api.content.transition(obj=subtask1, transition='accept-refusal')
        self.assertEqual(api.content.get_state(obj=task), 'todo')
        self.assertEqual(api.content.get_state(obj=subtask1), 'abandoned')
        api.content.create(container=task, type='task', id='subtask2', title="Subtask 2")
        api.content.delete(obj=mymail)
        self.assertNotIn('mymail', folder)

    def __TODO_test_versionnote_workflow(self):
        pass

    def test_outgoingmail_sent_mark_task_as_done(self):
        self.login('manager')
        intids = getUtility(IIntIds)
        portal = api.portal.get()
        folder = portal['folder']
        self.incomingmail = api.content.create(container=folder,
                                               type="dmsincomingmail",
                                               title="Incoming mail",
                                               treated_by=[],
                                               treating_groups=[],
                                               in_copy=[],
                                               recipient_groups=[])
        incomingmail_intid = intids.getId(self.incomingmail)
        task = api.content.create(container=self.incomingmail,
                                  type='task', id='task', title="My task")
        self.assertEqual(api.content.get_state(task), 'todo')
        api.content.transition(obj=task, transition='take-responsibility')
        self.assertEqual(api.content.get_state(task), 'in-progress')
        task_intid = intids.getId(task)
        outgoing = api.content.create(container=folder, type='dmsoutgoingmail',
                                      id='outgoingmail', title="Outgoing mail",
                                      in_reply_to=[RelationValue(incomingmail_intid)],
                                      related_task=[RelationValue(task_intid)])
        self.assertEqual(api.content.get_state(task), 'in-progress')
        v1 = api.content.create(container=outgoing, type='dmsmainfile', id='v1',
                                title='Version one')
        self.assertEqual(api.content.get_state(task), 'in-progress')
        api.content.transition(obj=v1, transition='finish_without_validation')
        self.assertEqual(api.content.get_state(task), 'in-progress')
        api.content.transition(obj=outgoing, transition='send')
        self.assertEqual(api.content.get_state(task), 'done')

    def test_tasks_created_after_attribution(self):
        self.login('manager')
        portal = api.portal.get()
        folder = portal['folder']
        self.incomingmail = api.content.create(container=folder,
                                               type="dmsincomingmail",
                                               title="Incoming mail",
                                               treated_by=[],
                                               treating_groups=['editor', 'editor2', 'editor3'],
                                               recipient_groups=[])
        incomingmail = self.incomingmail
        api.content.transition(obj=incomingmail, transition='to_assign')
        api.content.transition(obj=incomingmail, transition='to_process')
        self.assertEqual(api.content.get_state(incomingmail), 'processing')
        tasks = incomingmail.listFolderContents()
        self.assertEqual(len(tasks), 3)
        responsibles = ['editor', 'editor2', 'editor3']
        for task in tasks:
            self.assertTrue(IIncomingMailAttributed.providedBy(task))
            self.assertIn(task.responsible[0], responsibles)

    def test_all_tasks_done(self):
        """If all tasks related to an incoming mail are done, the mail is answered"""
        self.login('manager')
        intids = getUtility(IIntIds)
        portal = api.portal.get()
        folder = portal['folder']
        self.incomingmail = api.content.create(container=folder,
                                               type="dmsincomingmail",
                                               title="Incoming mail",
                                               treated_by=[],
                                               treating_groups=[],
                                               recipient_groups=[])
        incomingmail_intid = intids.getId(self.incomingmail)
        task1 = api.content.create(container=self.incomingmail, responsible=[],
                                  type='task', id='task1', title="My task 1")
        alsoProvides(task1, IIncomingMailAttributed)
        task2 = api.content.create(container=self.incomingmail, responsible=[],
                                  type='task', id='task2', title="My task 2")

        api.content.transition(obj=self.incomingmail, transition='to_assign')
        api.content.transition(obj=self.incomingmail, transition='to_process')

        api.content.transition(obj=task1, transition='take-responsibility')
        task1_intid = intids.getId(task1)
        outgoing1 = api.content.create(container=folder, type='dmsoutgoingmail',
                                       id='outgoingmail1', title="Outgoing mail",
                                       in_reply_to=[RelationValue(incomingmail_intid)],
                                       related_task=[RelationValue(task1_intid)])
        v11 = api.content.create(container=outgoing1, type='dmsmainfile', id='v11',
                                title='Version one')
        api.content.transition(obj=v11, transition='finish_without_validation')

        api.content.transition(obj=task2, transition='take-responsibility')

        ################### KeyError : from_object
#        task2_intid = intids.getId(task2)
#        outgoing2 = api.content.create(container=folder, type='dmsoutgoingmail',
#                                       id='outgoingmail2', title="Outgoing mail",
#                                       in_reply_to=[RelationValue(incomingmail_intid)],
#                                       related_task=[RelationValue(task2_intid)])
#        v21 = api.content.create(container=outgoing2, type='dmsmainfile', id='v21',
#                                title='Version one')
#        api.content.transition(obj=v21, transition='finish_without_validation')

        self.assertEqual(api.content.get_state(self.incomingmail),
                         'processing')
        api.content.transition(obj=outgoing1, transition='send')
        self.assertEqual(api.content.get_state(task1), 'done')

        self.assertEqual(api.content.get_state(self.incomingmail),
                         'processing')
        alsoProvides(task2, IIncomingMailAttributed)
        api.content.transition(obj=task2, transition='mark-as-done')
        #api.content.transition(obj=outgoing2, transition='send')  # KeyError from_object
        self.assertEqual(api.content.get_state(task2), 'done')

        self.assertEqual(api.content.get_state(self.incomingmail),
                         'answered')

    def test_all_tasks_abandoned(self):
        """If all tasks are abandoned, the mail is not answered"""
        self.login('manager')
        intids = getUtility(IIntIds)
        portal = api.portal.get()
        folder = portal['folder']
        self.incomingmail = api.content.create(container=folder,
                                               type="dmsincomingmail",
                                               title="Incoming mail",
                                               treated_by=[],
                                               treating_groups=['editor', 'editor2'],
                                               recipient_groups=[])
        incomingmail = self.incomingmail
        api.content.transition(obj=incomingmail, transition='to_assign')
        api.content.transition(obj=incomingmail, transition='to_process')
        tasks = incomingmail.listFolderContents()
        for task in tasks:
            self.assertEqual(api.content.get_state(incomingmail), 'processing')
            api.content.transition(obj=task, transition='abandon')
        self.assertEqual(api.content.get_state(incomingmail), 'processing')

    def test_tasks_done_and_abandoned(self):
        """If a task is done and a task is abandoned, the mail is answered"""
        self.login('manager')
        intids = getUtility(IIntIds)
        portal = api.portal.get()
        folder = portal['folder']
        self.incomingmail = api.content.create(container=folder,
                                               type="dmsincomingmail",
                                               title="Incoming mail",
                                               treated_by=[],
                                               treating_groups=['editor', 'editor2'],
                                               recipient_groups=[])
        incomingmail = self.incomingmail
        incomingmail_intid = intids.getId(incomingmail)
        api.content.transition(obj=incomingmail, transition='to_assign')
        api.content.transition(obj=incomingmail, transition='to_process')
        self.assertEqual(api.content.get_state(incomingmail), 'processing')

        tasks = incomingmail.listFolderContents()

        task = tasks[0]
        api.content.transition(obj=task, transition='take-responsibility')
        task_intid = intids.getId(task)
        outgoing = api.content.create(container=folder, type='dmsoutgoingmail',
                                      id='outgoingmail', title="Outgoing mail",
                                      in_reply_to=[RelationValue(incomingmail_intid)],
                                      related_task=[RelationValue(task_intid)])
        v1 = api.content.create(container=outgoing, type='dmsmainfile', id='v1',
                                title='Version one')
        api.content.transition(obj=v1, transition='finish_without_validation')
        api.content.transition(obj=outgoing, transition='send')
        self.assertEqual(api.content.get_state(task), 'done')
        self.assertEqual(api.content.get_state(incomingmail), 'processing')

        task = tasks[1]
        api.content.transition(obj=task, transition='abandon')
        self.assertEqual(api.content.get_state(incomingmail), 'answered')
