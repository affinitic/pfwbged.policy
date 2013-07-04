from five import grok

from zope.interface import Interface
from zope.cachedescriptors.property import CachedProperty
from plone.app.querystring.querybuilder import QueryBuilder

from collective.dms.basecontent.browser.listing import TasksTable as BaseTasksTable
from pfwbged.policy import _

grok.templatedir('templates')


class TasksTable(BaseTasksTable):
    @CachedProperty
    def values(self):
        b_start = int(self.request.get('b_start', 0))
#        batch = self.context.results(b_start=b_start)
        # items are plone.app.contentlisting.catalog.CatalogContentListingObject instances
        # use item.getDataOrigin() to get the brain
#        results = [b.getDataOrigin() for b in batch]
#        return results
        return self.results(b_start=b_start, brains=True)

    # copied from plone.app.collection.collection to add a brains parameter
    def results(self, batch=True, b_start=0, b_size=None, brains=False):
        querybuilder = QueryBuilder(self, self.request)
        sort_order = 'reverse' if self.context.sort_reversed else 'ascending'
        if not b_size:
            b_size = self.context.item_count
        return querybuilder(query=self.context.query,
                            batch=batch, b_start=b_start, b_size=b_size,
                            sort_on=self.context.sort_on, sort_order=sort_order,
                            limit=self.context.limit, brains=brains)


class TasksView(grok.View):
    grok.context(Interface)
    grok.name('tasks_view')
    grok.require('zope2.View')

    template = grok.PageTemplateFile('templates/tasks_view.pt')
    __table__ = TasksTable

    def update(self):
        self.table = self.__table__(self.context, self.request)
        self.table.viewlet = self
        self.table.update()
