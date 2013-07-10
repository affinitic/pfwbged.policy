import Missing
from five import grok

from zope.interface import Interface
from zope.cachedescriptors.property import CachedProperty
from zope.component import getMultiAdapter
from zope.publisher.interfaces.browser import IBrowserRequest
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.PloneBatch import Batch
from plone.app.querystring.querybuilder import QueryBuilder
from plone.app.contenttypes.interfaces import ICollection, IFolder

from collective.dms.basecontent.browser.listing import TasksTable as BaseTasksTable
from collective.dms.basecontent.browser import column
from z3c.table.interfaces import IValues
from z3c.table.value import ValuesMixin

grok.templatedir('templates')


class TasksTable(BaseTasksTable):
    @CachedProperty
    def values(self):
        adapter = getMultiAdapter(
            (self.context, self.request, self), IValues)
        return adapter.values


class ValuesFromFolder(grok.MultiAdapter, ValuesMixin):
    grok.adapts(IFolder, IBrowserRequest, TasksTable)

    @property
    def values(self):
        b_start = int(self.request.get('b_start', 0))
        b_size = int(self.request.get('b_size', 50))
        sort_on = self.request.get('sort_on', 'getObjPositionInParent')
        sort_order = self.request.get('sort_order', 'ascending')
        query = {'path': {'query': '/'.join(self.context.getPhysicalPath()),
                          'depth': 1},
                 'b_start': b_start,
                 'b_size': b_size,
                 'sort_on': sort_on,
                 'sort_order': sort_order}
        catalog = getToolByName(self.context, 'portal_catalog')
        results = catalog.searchResults(query)
        results = Batch(results, b_size, b_start)
        return results


class ValuesFromCollection(grok.MultiAdapter, ValuesMixin):
    grok.adapts(ICollection, IBrowserRequest, TasksTable)

    @property
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
        querybuilder = QueryBuilder(self.context, self.request)
        sort_order = 'reverse' if self.context.sort_reversed else 'ascending'
        if not b_size:
            b_size = self.context.item_count
        return querybuilder(query=self.context.query,
                            batch=batch, b_start=b_start, b_size=b_size,
                            sort_on=self.context.sort_on, sort_order=sort_order,
                            limit=self.context.limit, brains=brains)


class DocumentTitleColumn(column.TitleColumn):
    grok.name('dms.title')
    grok.adapts(Interface, Interface, TasksTable)

    def getLinkContent(self, item):
        if item.document_title is Missing.Value:
            return super(DocumentTitleColumn, self).getLinkContent(item)

        return item.document_title.decode('utf8') + ' / ' + item.Title.decode('utf8')

    def getLinkURL(self, item):
        if item.document_title is Missing.Value:
            return super(DocumentTitleColumn, self).getLinkURL(item)

        return self.request.physicalPathToURL(item.document_path)


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
