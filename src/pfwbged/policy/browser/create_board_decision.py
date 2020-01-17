from five import grok
from pfwbged.basecontent.types import INoteForBoard
from plone import api
from zc.relation.interfaces import ICatalog
from zope.component import getUtility
from zope.intid.interfaces import IIntIds


class CanCreateBoardDecision(grok.View):
    """Create a board decision from a note for board"""

    grok.name('can_create_board_decision')
    grok.context(INoteForBoard)
    grok.require("zope2.View")

    def in_gestion_sg(self):
        return any([group for group in api.group.get_groups(user=api.user.get_current()) if
                    group.id == 'Gestion-secretariat-general'])

    def board_decision_created(self):
        """Return true if a board decision has been created for this note for board"""
        intids = getUtility(IIntIds)
        catalog = getUtility(ICatalog)
        try:
            note_intid = intids.getId(self.context)
        except KeyError:
            return False
        else:
            return any(catalog.findRelations({'to_id': note_intid,
                                              'from_attribute': 'related_docs'}))

    def render(self):
        if not self.in_gestion_sg():
            return False

        if self.board_decision_created():
            return False

        return True


class CreateBoardDecision(grok.View):
    """Create a board decision from a note for board"""

    grok.name('create_board_decision')
    grok.context(INoteForBoard)
    grok.require("zope2.View")

    def render(self):
        note = self.context

        values_params = [
            u'form.widgets.IBasic.title={}'.format(
                note.title,
            ),
            u'form.widgets.related_docs:list={}'.format(
                u'/'.join(note.getPhysicalPath()),
            ),
        ]

        list_fields = {
            'treated_by': 'IPfwbDocument.treated_by',
            'treating_groups': 'treating_groups',
            'recipient_groups': 'recipient_groups',
            'keywords': 'IPfwbDocument.keywords',
        }
        for field_id, field_param_id in list_fields.items():
            field = getattr(note, field_id, []) or []
            for item in field:
                values_params.append(
                    u'form.widgets.{}:list={}'.format(field_param_id, item)
                )

        documents_folder_url = api.portal.get()['documents'].absolute_url()
        encoded_params = "&".join(values_params).encode('utf-8')
        url = '{0}/++add++pfwb.boarddecision?{1}'.format(
            documents_folder_url,
            encoded_params,
        )
        self.request.response.redirect(url)
