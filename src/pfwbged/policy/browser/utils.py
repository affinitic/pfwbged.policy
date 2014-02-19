from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory

from Products.Five.browser import BrowserView

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
            if term.title.startswith('(Group) '):
                term.title = term.title[len('(Group) '):] # remove '(Group) '

            if term.value in portal['dossiers']:
                if not reset:
                    continue
                folder = portal['dossiers'].get(term.value)
            else:
                folder = portal['dossiers'].invokeFactory('pfwbgedfolder',
                    term.value, title=term.title)

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
