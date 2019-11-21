from five import grok
from plone import api
from pfwbged.basecontent.types import INoteForBoard


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
