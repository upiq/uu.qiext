## Script (Python) "check_id"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=id=None,required=0,alternative_id=None,contained_by=None
##title=Check an id's validity
"""
This script tests an id to make sure it is valid.

Returns an error message if the id is bad or None if the id is good.
Parameters are as follows:

    id - the id to check

    required - if False, id can be the empty string

    alternative_id - an alternative value to use for the id
    if the id is empty or autogenerated

Note: The reason the id is included is to handle id error messages for such
objects as files and images that supply an alternative id when an id is auto-
generated. If you say "There is already an item with this name in this folder"
for an image that has the Name field populated with an autogenerated id,
it can cause some confusion; since the real problem is the name of
the image file name, not in the name of the autogenerated id.
"""

from AccessControl import Unauthorized
from ZODB.POSException import ConflictError
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone import PloneMessageFactory as _
from Products.CMFPlone.utils import base_hasattr

# http://dev.plone.org/plone/ticket/10518#comment:7
ts = getToolByName(context, 'translation_service')
def xlate(message):
    return ts.translate(message, context=context.REQUEST)

# if an alternative id has been supplied, see if we need to use it
if alternative_id and not id:
    id = alternative_id

# make sure we have an id if one is required
if not id:
    if required:
        return _(u'Please enter a name.')

    # Id is not required and no alternative was specified, so assume the
    # object's id will be context.getId(). We still should check to make sure
    # context.getId() is OK to handle the case of pre-created objects
    # constructed via portal_factory.  The main potential problem is an id
    # collision, e.g. if portal_factory autogenerates an id that already exists.

    id = context.getId()

#
# do basic id validation
#

# check for reserved names
if id in ('login', 'layout', 'plone', 'zip', 'properties', ):
    return xlate(
        _(u'${name} is reserved.',
          mapping={'name': id}))

# check for bad characters
plone_utils = getToolByName(container, 'plone_utils', None)
if plone_utils is not None:
    bad_chars = plone_utils.bad_chars(id)
    if len(bad_chars) > 0:
        return xlate(
            _(u'${name} is not a legal name. The following characters are invalid: ${characters}',
                mapping={u'name': id, u'characters': ''.join(bad_chars)}))

# check for a catalog index
portal_catalog = getToolByName(container, 'portal_catalog', None)
if portal_catalog is not None:
    try:
        if id in portal_catalog.indexes() + portal_catalog.schema():
            return xlate(
                _(u'${name} is reserved.',
                  mapping={u'name': id}))
    except Unauthorized:
        pass # ignore if we don't have permission; will get picked up at the end

# id is good; decide if we should check for id collisions
portal_factory = getToolByName(container, 'portal_factory', None)
if contained_by is not None:
    # always check for collisions if a container was passed
    checkForCollision = True
elif portal_factory is not None and portal_factory.isTemporary(context):
    # always check for collisions if we are creating a new object
    checkForCollision = True
    try:
        # XXX this can't really be necessary, can it!?
        contained_by = context.aq_inner.aq_parent.aq_parent.aq_parent
    except Unauthorized:
        pass
else:
    # if we have an existing object, only check for collisions
    # if we are changing the id
    checkForCollision = (context.getId() != id)

# check for id collisions
if checkForCollision:
    # handles two use cases:
    # 1. object has not yet been created and we don't know where it will be
    # 2. object has been created and checking validity of id within container
    if contained_by is None:
        try:
            contained_by = context.getParentNode()
        except Unauthorized:
            return # nothing we can do

    # Check for an existing object.
    if id in contained_by:
        try:
            existing_obj = getattr(contained_by, id, None)
            if base_hasattr(existing_obj, 'portal_type'):
                return xlate(
                    _(u'There is already an item named ${name} in this folder.',
                      mapping={u'name': id}))
        except Unauthorized:
            # we can't access the object: safe to assume we can't replace it
            #
            return xlate(
                _(u'There is already an item named ${name} in this folder.',
                  mapping={u'name': id}))

    if base_hasattr(contained_by, 'checkIdAvailable'):
        try:
            if not contained_by.checkIdAvailable(id):
                return xlate(
                    _(u'${name} is reserved.',
                      mapping={u'name': id}))
        except Unauthorized:
            pass # ignore if we don't have permission

    # containers may implement this hook to further restrict ids
    if base_hasattr(contained_by, 'checkValidId'):
        try:
            contained_by.checkValidId(id)
        except Unauthorized:
            raise
        except ConflictError:
            raise
        except:
            return xlate(
                _(u'${name} is reserved.',
                  mapping={u'name': id}))

    # make sure we don't collide with any parent method aliases
    portal_types = getToolByName(context, 'portal_types', None)
    if plone_utils is not None and portal_types is not None:
        parentFti = portal_types.getTypeInfo(contained_by)
        if parentFti is not None:
            aliases = plone_utils.getMethodAliases(parentFti)
            if aliases is not None:
                if id in aliases.keys():
                    return xlate(
                        _(u'${name} is reserved.',
                          mapping={u'name': id}))

    # Lastly, we want to disallow the id of any of the tools in the portal root,
    # as well as any object that can be acquired via portal_skins. However,
    # we do want to allow overriding of *content* in the object's parent path,
    # including the portal root.

    if id != 'index_html': # always allow index_html
        portal = context.portal_url.getPortalObject()
        if id not in portal.contentIds(): # can override root *content*
            try:
                if id.endswith('.css'):
                    pass
                elif getattr(portal, id, None) is not None: # but not other things
                    return xlate(
                        _(u'${name} is reserved.',
                          mapping={u'name': id}))
            except Unauthorized:
                pass # ignore if we don't have permission
