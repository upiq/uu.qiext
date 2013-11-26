import csv
from StringIO import cStringIO as StringIO

from zope.globalrequest import getRequest

from uu.qiext.interfaces import IWorkspaceContext
from uu.qiext.user.interfaces import IWorkspaceRoster


class WorkspaceMembershipCSV(object):
    """
    Adapter or view of workspace providing CSV output of membership.
    """

    ORDER = ('EMAIL', 'FULLNAME')

    def __init__(self, context, request=None):
        if not IWorkspaceContext.providedBy(context):
            raise ValueError
        self.context = context
        self.request = request if request else getRequest()

    def _info(self, user):
        _get = lambda name: user.getProperty(name)
        return {
            'EMAIL': _get('email'),
            'FULLNAME': _get('fullname').encode('utf-8'),
            }

    def update(self, *args, **kwargs):
        # get list of IPropertiedUser objects for all members
        self.members = IWorkspaceRoster(self.context).values()
        self.info = map(self._info, self.members)
        self.output = StringIO()
        self.output.write(u'\ufeff'.encode('utf8'))  # UTF-8 BOM for MSExcel
        self.writer = csv.dictWriter(self.output, self.ORDER)
        # write heading row:
        self.writer.writerow(dict([(n, n) for n in self.ORDER]))
        for record in self.info:
            self.writer.writerow(record)
        self.output.seek(0)

    def index(self, *args, **kwargs):
        filename = '%s.csv' % self.context.getId()
        self.output.seek(0)
        csv = self.output.read()
        if self.request:
            self.request.response.setHeader('Content-Type', 'text/csv')
            self.request.response.setHeader('Content-Length', str(len(csv)))
            self.request.response.setHeader(
                'Content-Disposition',
                self.DISP % filename,
                )
        return csv

    def __call__(self, *args, **kwargs):
        self.update(*args, **kwargs)
        return self.index(*args, **kwargs)

