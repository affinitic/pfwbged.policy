from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory

from Products.Five.browser import BrowserView
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import base_hasattr

from plone import api

from collective.z3cform.rolefield.field import LocalRolesToPrincipalsDataManager
from pfwbged.folder import IFolder


class ImportGroupFolders(BrowserView):
    def __call__(self):
        portal = self.context
        factory = getUtility(IVocabularyFactory, 'plone.principalsource.Groups')
        vocabulary = factory(self.context)
        reset = self.request.form.get('reset') == 'true'
        for term in vocabulary:
            if term.value in ('Administrators', 'Reviewers',
                    'Site Administrators', 'AuthenticatedUsers'):
                # ignore system groups
                continue
            if term.title.startswith('(Groupe) '):
                term.title = term.title[len('(Groupe) '):] # remove '(Groupe) '

            if term.value in portal['dossiers']:
                if not reset:
                    continue
                folder = portal['dossiers'].get(term.value)
            else:
                folder_id = portal['dossiers'].invokeFactory('pfwbgedfolder',
                    term.value, title=term.title)
                folder = portal['dossiers'].get(folder_id)

            canwrite_dm = LocalRolesToPrincipalsDataManager(folder,
                        IFolder['treating_groups'])
            canread_dm = LocalRolesToPrincipalsDataManager(folder,
                        IFolder['recipient_groups'])
            if reset:
                canwrite_dm.set([])
            canwrite_dm.set([term.value])
            if reset:
                canread_dm.set([])
            canread_dm.set([term.value])
            folder.reindexObjectSecurity()

        return 'OK'


class ImportUserFolders(BrowserView):
    def __call__(self):
        portal = self.context
        factory = getUtility(IVocabularyFactory, 'plone.principalsource.Users')
        membership_tool = getToolByName(portal, 'portal_membership')
        vocabulary = factory(self.context)
        members_folder = getattr(portal, 'Members')
        for term in vocabulary:
            if base_hasattr(members_folder, term.value):
                continue
            with api.env.adopt_user(username=term.value):
                membership_tool.loginUser()

        return 'OK'


class Pdb(BrowserView):
    def __call__(self):
        import pdb; pdb.set_trace()
