import unittest2 as unittest

from plone.registry.interfaces import IRegistry
from plone.app.testing import TEST_USER_ID, setRoles
from Products.CMFPlone.utils import getToolByName

from uu.qiext.user.interfaces import WORKSPACE_GROUPS
from uu.qiext.tests.layers import DEFAULT_PROFILE_TESTING
from uu.qiext.tests.fixtures import CreateContentFixtures


class HandlerTest(unittest.TestCase):
    """Test event subscribers/handlers"""
    
    THEME = 'Sunburst Theme'
    
    layer = DEFAULT_PROFILE_TESTING
    
    def setUp(self):
        self.portal = self.layer['portal']
        self.wftool = getToolByName(self.portal, 'portal_workflow')
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.groups_plugin = self.portal.acl_users.source_groups

    def test_create(self):
        adapter = CreateContentFixtures(self, self.layer)
        suffixes = WORKSPACE_GROUPS.keys()
        proj_id1 = 'proj_handler_test_create1'
        allgroups_before = self.groups_plugin.listGroupIds()
        for g in ['%s-%s' % (proj_id1, suffix) for suffix in suffixes]:
            assert g not in allgroups_before
        proj = adapter.add_project(proj_id1)
        allgroups_after = self.groups_plugin.listGroupIds()
        ## necessary/sufficient: all expected groups (and only these):
        self.assertEquals(len(allgroups_after) - len(allgroups_before), 4)
        for g in ['%s-%s' % (proj_id1, suffix) for suffix in suffixes]:
            assert g in allgroups_after
        ## now create a team workspace inside the project, similarly:
        team_id1 = 'team1'
        allgroups_before = self.groups_plugin.listGroupIds()
        for g in ['-'.join((proj_id1, team_id1, s)) for s in suffixes]:
            assert g not in allgroups_before
        team = adapter.add_team_to(proj, team_id1)
        allgroups_after = self.groups_plugin.listGroupIds()
        ## necessary/sufficient: all expected groups (and only these):
        self.assertEquals(len(allgroups_after) - len(allgroups_before), 4)
        for g in ['-'.join((proj_id1, team_id1, s)) for s in suffixes]:
            assert g in allgroups_after
    
    def test_move_rename(self):
        """Test move or rename"""
        adapter = CreateContentFixtures(self, self.layer)
        suffixes = WORKSPACE_GROUPS.keys()
        proj_id1 = 'proj_handler_test_move_rename'
        self.assertNotIn(proj_id1, self.portal.contentIds())
        allgroups_before = self.groups_plugin.listGroupIds()
        proj = adapter.add_project(proj_id1)
        self.assertIn(proj_id1, self.portal.contentIds())
        allgroups_after = self.groups_plugin.listGroupIds()
        self.assertEquals(len(allgroups_after) - len(allgroups_before), 4)
        for g in ['%s-%s' % (proj_id1, suffix) for suffix in suffixes]:
            assert g in allgroups_after
        self.portal.manage_renameObject(proj_id1, proj_id1 + 'a')
        self.assertNotIn(proj_id1, self.portal.contentIds())     # old name
        self.assertIn(proj_id1 + 'a', self.portal.contentIds())  # new name
        allgroups_postrename = self.groups_plugin.listGroupIds()
        self.assertEquals(len(allgroups_postrename), len(allgroups_after))
        
        
        
