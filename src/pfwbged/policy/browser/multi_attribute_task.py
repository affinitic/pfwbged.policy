# -*- coding: utf-8 -*-

from copy import deepcopy
import z3c.form
from z3c.form import button

import zope.event
from zope.i18nmessageid.message import MessageFactory
from Products.CMFCore.utils import getToolByName

from plone import api
from plone.dexterity.browser.add import DefaultAddForm
from plone.dexterity.utils import createContentInContainer
from plone.stringinterp.adapters import _recursiveGetMembersFromIds

from collective.task import _
from collective.task.content.task import ITask
from collective.task.browser.attribute_task import find_nontask


class AttributeTasks(DefaultAddForm):
    "Attribute multiple tasks"

    portal_type = "task"

    @property
    def label(self):
        return u"Attribuer les tâches"

    @property
    def action(self):
        return self.request.getURL() + '?documents=' + self.request.documents

    def updateWidgets(self):
        """Update widgets then add workflow_action value to workflow_action field"""
        super(AttributeTasks, self).updateWidgets()
        for obj_id in self.request.documents.split(','):
            base_obj = api.content.get(str(obj_id))
            if ITask.providedBy(base_obj):
                self.widgets['title'].value = base_obj.title
                break
            else:
                tasks = base_obj.listFolderContents({"portal_type": "task"})
                if tasks:
                    self.widgets['title'].value = tasks[0].title
                    break

    @button.buttonAndHandler(_('Add'), name='add')
    def handleAdd(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        for task_id in self.request.documents.split(','):
            base_task = api.content.get(str(task_id))
            self.attribute_task(base_task, data)

        self._finishedAdd = True
        return

    def attribute_task(self, base_task, data):
        seen = {}
        nontask = find_nontask(base_task)
        portal_workflow = getToolByName(nontask, 'portal_workflow')
        transitions = portal_workflow.getTransitionsFor(nontask)
        transition_ids = [t['id'] for t in transitions]

        for responsible in data['responsible']:
            if responsible in seen:
                continue
            _data = deepcopy(data)
            _data['responsible'] = [responsible]
            new_task = createContentInContainer(base_task, 'task', **_data)
            seen[responsible] = True

            for responsible in data['responsible']:
                nontask.manage_addLocalRoles(responsible, ['Editor',])
            if 'attribute' in transition_ids:
                portal_workflow.doActionFor(nontask, 'attribute')
            nontask.reindexObjectSecurity()
            nontask.reindexObject(idxs=['allowedRolesAndUsers'])
