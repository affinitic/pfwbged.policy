from z3c.form import button
from zope.i18nmessageid import MessageFactory

from plone import api
from plone.app.discussion.browser.comments import CommentForm, CommentsViewlet

from pfwbged.policy import _


PADMF = MessageFactory('plone.app.discussion')


class BaseTaskCommentForm(CommentForm):

    @button.buttonAndHandler(PADMF(u"add_comment_button", default=u"Comment"),
                             name='comment')
    def handleComment(self, action):
        """After comment, redirect to the parent"""
        super(BaseTaskCommentForm, self).handleComment(self, action)
        self.request.response.redirect(self.context.getParentNode().absolute_url())

    @button.buttonAndHandler(PADMF(u"Cancel"))
    def handleCancel(self, action):
        # This method should never be called, it's only there to show
        # a cancel button that is handled by a jQuery method.
        pass  # pragma: no cover


class BaseTaskCommentsViewlet(CommentsViewlet):

    form = BaseTaskCommentForm


def can_render_opinion(form):
    """Return True if the current user can render an opinion"""
    responsible = form.context.responsible[0]
    current_user = api.user.get_current().id
    return api.content.get_state(form.context) != 'done' and current_user == responsible


class OpinionCommentForm(BaseTaskCommentForm):

    @button.buttonAndHandler(_(u"Render opinion"),
                             name='render_opinion',
                             condition=can_render_opinion,
                             )
    def handleRenderOpinion(self, action):
        """After comment, execute transition if wanted"""
        super(OpinionCommentForm, self).handleComment(self, action)
        api.content.transition(self.context, 'mark-as-done')

    @button.buttonAndHandler(PADMF(u"add_comment_button", default=u"Comment"),
                             name='comment')
    def handleComment(self, action):
        """After comment, redirect to the parent"""
        super(BaseTaskCommentForm, self).handleComment(self, action)
        self.request.response.redirect(self.context.getParentNode().absolute_url())

    @button.buttonAndHandler(PADMF(u"Cancel"))
    def handleCancel(self, action):
        # This method should never be called, it's only there to show
        # a cancel button that is handled by a jQuery method.
        pass  # pragma: no cover


class OpinionCommentsViewlet(CommentsViewlet):

    form = OpinionCommentForm
