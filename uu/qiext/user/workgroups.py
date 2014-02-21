"""
uu.qiext.user.workgroups: membership management adapters for
workspaces/workgroups.
"""

__author__ = 'Sean Upton'
__email__ = 'sean.upton@hsc.utah.edu'
__copyright__ = """
                Copyright, 2011-2013, The University of Utah
                """.strip()
__license__ = 'GPL'


import itertools

from plone.indexer.decorator import indexer
from Products.CMFCore.interfaces import ISiteRoot
from zope.interface import implements
from zope.component import adapts, queryUtility
from zope.component.hooks import getSite

from uu.qiext.interfaces import IWorkspaceContext, IProjectContext
from uu.qiext.user import interfaces
from uu.qiext.user.groups import GroupInfo, Groups
from uu.qiext.user.utils import group_namespace


def valid_setattr(obj, field, value):
    field.validate(value)
    setattr(obj, field.__name__, value)

_decode = lambda v: v.decode('utf-8') if isinstance(v, str) else v


class WorkspaceGroup(object):
    """
    Workspace group adapter: provides mapping for managing workspace
    membership in a specific group.
    """

    implements(interfaces.IWorkspaceGroup)
    adapts(IWorkspaceContext)

    # class attribute defaults (for instance attributes):
    __parent__ = None

    def __init__(self,
                 context,
                 parent=None,
                 groupid=u'',
                 title=u'',
                 description=u'',
                 namespace=u'',
                 roles=(),
                 members=None,
                 **kwargs):
        if not IWorkspaceContext.providedBy(context):
            raise ValueError('Could not adapt: context not a workspace')
        schema = interfaces.IWorkspaceGroup
        if schema.providedBy(parent):
            self.__parent__ = parent
        self.context = context
        self.adapts_project = IProjectContext.providedBy(context)
        valid_setattr(self, schema['baseid'], _decode(groupid))
        valid_setattr(self, schema['title'], _decode(title))
        valid_setattr(self, schema['description'], _decode(description))
        valid_setattr(self, schema['namespace'], _decode(namespace))
        self._keys = None
        self.portal = getSite()
        self.site_members = members or interfaces.ISiteMembers(self.portal)
        groups = Groups(self.portal)
        groupname = self.pas_group()[0]
        if groupname not in groups:
            groups.add(groupname)  # edge-case: may cause write-on-read
        self._group = GroupInfo(groupname, members=self.site_members)

    @property
    def __name__(self):
        return self.baseid or None

    def _groupname(self):
        ns = self.namespace  # usually UUID of workspace
        return '-'.join((ns, self.baseid))

    def _grouptitle(self):
        r = []  # stack of object context (LIFO)
        context = self.context
        while getattr(context, '__parent__', None) is not None:
            if ISiteRoot.providedBy(context):
                break
            r.append(context)
            context = context.__parent__
        titles = [o.Title() for o in reversed(r)]
        return u'%s - %s' % (' / '.join(titles).encode('utf-8'), self.title)

    def pas_group(self):
        return (self._groupname(), self._grouptitle())

    def _get_user(self, username):
        return self.site_members.get(username)

    def __contains__(self, username):
        return username in self.keys()

    def __getitem__(self, username):
        if username not in self.keys():
            raise KeyError('User %s not in group %s (%s)' % (
                username,
                self._groupname(),
                self._grouptitle(),
            ))
        return self._get_user(username)

    def get(self, username, default=None):
        if username not in self.keys():
            return default
        return self._get_user(username)

    # mapping enumeration -- keys/values/items:

    def keys(self):
        """
        List of login names as group members.  This may be cached,
        as it is expensive to list assigned group principals in the
        stock Plone group plugin (ZODBGroupManager).
        """
        if self._keys is None:
            self._keys = self._group.keys()
        return self._keys  # cached lookup for session

    def values(self):
        return [self._get_user(k) for k in self.keys()]

    def items(self):
        return [(k, self._get_user(k)) for k in self.keys()]

    def __len__(self):
        return len(self.keys())

    # iterable mapping methods:

    def iterkeys(self):
        return iter(self.keys())

    __iter__ = iterkeys

    def itervalues(self):
        return itertools.imap(self._get_user, self.keys())

    def iteritems(self):
        func = lambda username: (username, self._get_user(username))  # (k,v)
        return itertools.imap(func, self.keys())

    # add / delete (assign/unassign) methods:

    def add(self, username):
        if username not in self.site_members:
            raise RuntimeError('User %s unknown to site' % username)
        if username not in self.keys():
            self._group.assign(username)
        self.refresh()  # need to invalidate keys -- membership modified.

    def unassign(self, username):
        if username not in self.keys():
            raise ValueError('user %s is not group member' % username)
        self._group.unassign(username)
        self.refresh()  # need to invalidate keys -- membership modified.

    def refresh(self):
        self._keys = None  # invalidate previous cached keys
        self._group.refresh()
        if interfaces.IWorkspaceGroup.providedBy(self.__parent__):
            if self.__parent__.baseid == self.baseid:
                # group equivalence, invalidate parent group too!
                self.__parent__._keys = None


class WorkspaceRoster(WorkspaceGroup):
    """
    Adapts project or other workspace (e.g. team) context, loads base
    group roster (for 'viewers') and loads contained groups.

    Provides interface to add (assign), remove (unassign and purge),
    and iterate over users and (other) groups for workspace.

    Some operations may be project-specific and raise exceptions in
    non-project workspace context per interface specification.
    """

    implements(interfaces.IWorkspaceRoster)
    adapts(IWorkspaceContext)

    def __init__(self, context):
        self.adapts_project = IProjectContext.providedBy(context)
        self._load_config()
        super(WorkspaceRoster, self).__init__(
            context,
            parent=None,
            groupid=self._base['groupid'],
            title=self._base['title'],
            description=self._base['description'],
            namespace=group_namespace(context),
            )
        self._load_groups()

    def _load_config(self):
        self._config = config = queryUtility(interfaces.IWorkgroupTypes)
        basename = config.BASE_GROUPNAME
        if self.adapts_project:
            self._config = dict(config.select('project', config.items))
        self._base = self._config[basename]

    def _load_groups(self):
        self.groups = {}
        for name, group_cfg in self._config.items():
            self.groups[name] = WorkspaceGroup(
                self.context,
                parent=self,
                namespace=self.namespace,
                members=self.site_members,
                **group_cfg)  # title, description, groupid

    def can_purge(self, username):
        if not self.adapts_project:
            return False  # no purge in workspace other than top-level project
        if username not in self.keys():
            return False  # sanity check, username must be in project roster
        if not self.namespace:
            return False  # empty namespace -- seems wrong!
        user_groups = self.site_members.get(username).getGroups()
        for group in user_groups:
            if group in ('AuthenticatedUsers',):
                continue
            if not group.startswith(self.namespace):
                return False  # any match outside our scope == fail
        return True

    def unassign(self, username):
        # recursive removal: relies on transaction atomicity from ZODB
        # and ZODB group plugin to provide complete rollback on exception.
        super(WorkspaceRoster, self).unassign(username)  # WorkspaceGroup impl
        for group in self.groups.values():
            if username in group.keys():
                group.unassign(username)

    def remove(self, username, purge=False):
        if not purge:
            return self.unassign(username)  # without purge: remove===unassign
        ## purge from site -- or check if possible and attempt:
        if not self.adapts_project:
            # no purge in workspace other than top-level project
            raise RuntimeError('Cannot purge user from non-project workspace')
        if not self.can_purge(username):
            raise RuntimeError('Cannot purge: user member of other projects')
        self.unassign(username)
        del(self.site_members[username])

    def refresh(self):
        super(WorkspaceRoster, self).refresh()
        if self.baseid in self.groups:
            # there is an equivalent group to roster, invalidate it too!
            self.groups[self.baseid].refresh()


# indexer adapter for project/workspace context group names:

@indexer(IWorkspaceContext)
def workspace_pas_groups(context, **kw):
    roster = interfaces.IWorkspaceRoster(context)
    names = set([roster.pas_group()[0]])
    groups = roster.groups.values()
    names = names.union(group.pas_group()[0] for group in groups)
    return list(names)

