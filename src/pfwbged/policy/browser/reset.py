# (initially copied from ftw.dashboard.dragndrop)

from Products.Five import BrowserView
from Products.statusmessages.interfaces import IStatusMessage
from zope.component import queryUtility
from plone.app.portlets.storage import UserPortletAssignmentMapping
from plone.portlets.interfaces import IPortletManager
from plone.portlets.constants import USER_CATEGORY

from plone.app.portlets.dashboard import new_user


class ResetView(BrowserView):

    def __call__(self, *args, **kwargs):
        user = self.context.portal_membership.getAuthenticatedMember()
        for number in range(4):
            name = "plone.dashboard" + str(number + 1)
            column = queryUtility(IPortletManager, name=name)
            if column is not None:
                category = column.get(USER_CATEGORY, None)
                if category is not None:
                    manager = category.get(user.getId(), None)
                    if manager is None:
                        manager = category[user.getId()] = \
                            UserPortletAssignmentMapping(
                                manager=name,
                                category=USER_CATEGORY,
                                name=user.getId())
                        if manager is None:
                            IStatusMessage(self.request).addStatusMessage(
                                "can't reset the Dashboard",
                                type="error")
                            break
                    for portlet in manager.keys():
                        del manager[portlet]

        # and now, fill it back with the default portlets
        new_user(user.getUser(), None)

        IStatusMessage(self.request).addStatusMessage(
            "Dashboard reseted",
            type="info")
        return self.request.RESPONSE.redirect(
            self.context.portal_url() + '/dashboard')
