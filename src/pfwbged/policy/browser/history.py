from Acquisition import aq_inner
from plone import api
from plone.app.layout.viewlets.content import ContentHistoryView as BaseHistoryView
from zope.annotation.interfaces import IAnnotations

from AccessControl import Unauthorized
from Products.CMFCore.utils import getToolByName

from .. import _
from ..menu import dmsfile_wfactions_mapping, IGNORE_

class ContentHistoryView(BaseHistoryView):

    def _modify_title(self, actions):
        for action in actions:
            version = self.context.Title()
            title = dmsfile_wfactions_mapping.get(action['action'],
                    _(u"Create version ${version}"))
            title = IGNORE_(title, mapping={'version': version})
            if action.get('action') == 'obsolete':
                # do not include version marked as obsolete
                title = ''
            action['transition_title'] = title

    def pfwbged_history(self):
        context = aq_inner(self.context)
        annotations = IAnnotations(context)
        if not 'pfwbged_history' in annotations:
            return []
        history = annotations['pfwbged_history'][:]
        for history_line in history:
            if history_line['action_id'] == 'pfwbged_field':
                history_line['actor'] = None
                history_line['actor_home'] = None
                history_line['actorid'] = history_line['actor_name']
                history_line['action'] = 'pfwbged_field'
                history_line['type'] = 'pfwbged_field'
                history_line['comments'] = ', '.join(history_line['value'])
                history_line['transition_title'] = _('New value for ${attribute}',
                        mapping={'attribute': history_line['attribute']})
            if history_line['action_id'] == 'pfwbged_mail':
                history_line['actor'] = None
                history_line['actor_home'] = None
                history_line['actorid'] = history_line['actor_name']
                history_line['action'] = 'pfwbged_mail'
                history_line['type'] = 'pfwbged_mail'
                history_line['comments'] = _('To: ${to}', mapping={'to': history_line.get('to', '')})
                history_line['transition_title'] = _('Sent version ${version} by email',
                        mapping={'version': history_line.get('version', '?')})
        return history

    def workflowHistory(self, complete=True):
        review_history = []
        results = super(ContentHistoryView, self).workflowHistory(complete)
        review_history.extend(results)

        catalog = api.portal.get_tool('portal_catalog')
        folder_path = '/'.join(self.context.getPhysicalPath())

        # insert workflow history for all versions
        query = {'path': {'query' : folder_path},
                 'portal_type': 'dmsmainfile'}
        brains = catalog.unrestrictedSearchResults(query)
        old_context = self.context
        for brain in brains:
            try:
                version = brain.getObject()
            except Unauthorized:
                continue
            self.context = version
            results = super(ContentHistoryView, self).workflowHistory(complete)
            self._modify_title(results)
            results = [x for x in results if x.get('transition_title')]
            review_history.extend(results)
        self.context = old_context

        # append history entries for the various tasks
        query = {'path': {'query' : folder_path},
                 'portal_type': ['information', 'opinion', 'task', 'validation']}
        brains = catalog.unrestrictedSearchResults(query)
        for brain in brains:
            try:
                task = brain.getObject()
            except Unauthorized:
                continue
            review_history.append({
                'actor': None,
                'actorid': task.creators[0],
                'actor_home': '',
                'action': task.portal_type,
                'time': task.creation_date,
                'transition_title': task.title,
                'type': None})

        review_history.extend(self.pfwbged_history())

        # makes sure the history is kept sorted
        review_history.sort(lambda x, y: cmp(x.get('time'), y.get('time')))

        return review_history
