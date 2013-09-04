from z3c.form import button
from z3c.form.field import Fields
from z3c.form.interfaces import HIDDEN_MODE
from zope.i18nmessageid import MessageFactory
from zope import schema

from plone import api
from plone.app.discussion.browser.comments import CommentForm, CommentsViewlet
from plone.supermodel import model

from collective.task.indexers import get_document

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
    opinion = form.context
    current_user = api.user.get_current()
    roles = api.user.get_roles(user=current_user, obj=opinion)
    return api.content.get_state(opinion) != 'done' and 'Editor' in roles


class OpinionCommentForm(BaseTaskCommentForm):

    @button.buttonAndHandler(_(u"Render opinion"),
                             name='render_opinion',
                             condition=can_render_opinion,
                             )
    def handleRenderOpinion(self, action):
        """After comment, execute transition if wanted"""
        super(OpinionCommentForm, self).handleComment(self, action)
        api.content.transition(self.context, 'mark-as-done')
        self.context.reindexObject(idxs=['review_state'])

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


class IWorkflowAction(model.Schema):
    """Simple schema that contains workflow action hidden field"""
    workflow_action = schema.TextLine(title=u'Workflow action',
                                      required=False
                                      )


def has_workflow_action(form):
    return ('workflow_action' in form.request or \
            form.request.get('form.widgets.workflow_action', False))


def not_has_workflow_action(form):
    return not ('workflow_action' in form.request or \
                form.request.get('form.widgets.workflow_action', False))


class TaskCommentForm(BaseTaskCommentForm):

    titles_mapping = {'accept-refusal': _(u'Accept refusal'),
                      'ask-for-refusal': _(u'Ask for refusal'),
                      'refuse-refusal': _(u'Refuse refusal'),
                      }

    def updateActions(self):
        # We don't want to use super from TaskCommentForm (it raises a KeyError)
        super(CommentForm, self).updateActions()
        actions = self.actions
        if 'cancel' in actions:
            actions['cancel'].addClass("standalone")
            actions['cancel'].addClass("hide")
        elif 'comment' in actions:
            actions['comment'].addClass("context")
        elif 'transition_comment' in actions:
            actions['comment'].addClass("context")

    def updateFields(self):
        super(TaskCommentForm, self).updateFields()
        self.fields += Fields(IWorkflowAction)
        self.fields['workflow_action'].mode = HIDDEN_MODE

    def updateWidgets(self):
        super(TaskCommentForm, self).updateWidgets()
        if 'workflow_action' in self.request:
            wf_action = self.request['workflow_action']
            self.widgets['workflow_action'].value = wf_action
            self.buttons['transition_comment'].title = self.titles_mapping[wf_action]

    @button.buttonAndHandler(PADMF(u"add_comment_button", default=u"Comment"),
                             name='comment',
                             condition=not_has_workflow_action)
    def handleComment(self, action):
        """After comment, redirect to the parent"""
        super(BaseTaskCommentForm, self).handleComment(self, action)
        data, errors = self.extractData()
        if not errors:
            document = get_document(self.context)
            self.request.response.redirect(document.absolute_url())

    @button.buttonAndHandler(u"Transition comment",
                             name='transition_comment',
                             condition=has_workflow_action)
    def handleTransitionComment(self, action):
        """After comment, redirect to the parent"""
        super(BaseTaskCommentForm, self).handleComment(self, action)
        data, errors = self.extractData()
        if not errors:
            workflow_action = data['workflow_action']
            api.content.transition(self.context, workflow_action)
            self.context.reindexObject(idxs=['review_state'])
            document = get_document(self.context)
            self.request.response.redirect(document.absolute_url())

    @button.buttonAndHandler(PADMF(u"Cancel"))
    def handleCancel(self, action):
        # This method should never be called, it's only there to show
        # a cancel button that is handled by a jQuery method.
        pass  # pragma: no cover


class TaskCommentsViewlet(CommentsViewlet):

    form = TaskCommentForm
