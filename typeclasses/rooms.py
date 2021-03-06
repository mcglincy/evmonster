"""
Room

Rooms are simple containers that has no location of their own.

"""

from collections import defaultdict
from enum import IntEnum
from evennia import DefaultRoom
from evennia.utils import evtable
from evennia.utils.utils import list_to_string
from gamerules.find import find_first
from gamerules.special_room_kind import SpecialRoomKind


# TODO: move this somewhere (utils?)
def check_bit(num, offset):
  mask = 1 << offset
  return(num & mask)


class WhichDesc(IntEnum):
  PRIMARY = 0
  SECONDARY = 1
  PRIMARY_AND_SECONDARY = 2
  PRIMARY_THEN_SECONDARY_IF_OBJECT = 3
  SECONDARY_IF_OBJECT_ELSE_PRIMARY = 4


class Room(DefaultRoom):
  """Rooms are like any Object, except their location is None
  (which is default). They also use basetype_setup() to
  add locks so they cannot be puppeted or picked up.
  (to change that, use at_object_creation instead)

  See examples/object.py for a list of
  properties and methods available on all Objects.
  """
  def at_object_creation(self):
    super().at_object_creation()
    self.db.record_id = None
    self.db.secondary_desc = None
    self.db.which_desc = 0
    # see SpecialRoomKind for the various special kinds and bit positions
    self.db.special_kind_bitmask = 0
    # special kind magnitudes
    self.db.magnitudes = [0] * 32  # a list of 32 zeroes
    self.db.trap_chance = 0
    self.db.trap_direction = None
    self.db.magic_object = None
    # dict of detail name => description
    self.db.details = {}

  def at_object_receive(self, new_arrival, source_location):
    """
    When an object enter a tutorial room we tell other objects in
    the room about it by trying to call a hook on them. The Mob object
    uses this to cheaply get notified of enemies without having
    to constantly scan for them.

    Args:
      new_arrival (Object): the object that just entered this room.
      source_location (Object): the previous location of new_arrival.
    """
    # and not new_arrival.is_superuser???
    if new_arrival.has_account:
      # this is a character
      for obj in self.contents_get(exclude=new_arrival):
        if hasattr(obj, "at_new_arrival"):
          obj.at_new_arrival(new_arrival)

  def special_kinds(self):
    return [x for x in SpecialRoomKind 
      if check_bit(self.db.special_kind_bitmask, x.value)]

  def is_special_kind(self, special_room_kind):
    return check_bit(self.db.special_kind_bitmask, special_room_kind.value)

  def magnitude(self, special_room_kind):
    return self.db.magnitudes[special_room_kind.value]

  def choose_desc(self, looker):
    if self.db.which_desc == WhichDesc.PRIMARY:
      return self.db.desc
    elif self.db.which_desc == WhichDesc.SECONDARY:
      if self.db.secondary_desc:
        return self.db.secondary_desc
      else:
        return self.db.desc
    elif self.db.which_desc == WhichDesc.PRIMARY_AND_SECONDARY:
      if self.db.secondary_desc:
        return f"{self.db.desc}\n{self.db.secondary_desc}"
      else:
        return self.db.desc
    elif self.db.which_desc == WhichDesc.PRIMARY_THEN_SECONDARY_IF_OBJECT:
      if self.db.secondary_desc is not None and self.db.magic_object is not None:
        has_obj = find_first(looker, self.db.magic_object)
        if has_obj:
          return f"{self.db.desc}\n{self.db.secondary_desc}"
      return self.db.desc
    elif self.db.which_desc == WhichDesc.SECONDARY_IF_OBJECT_ELSE_PRIMARY:
      if self.db.secondary_desc is not None and self.db.magic_object is not None:
        has_obj = find_first(looker, self.db.magic_object)
        if has_obj:
          return self.db.secondary_desc
      return self.db.desc

  def return_appearance(self, looker, **kwargs):
    """This formats a description. It is the hook a 'look' command
    should call.

    Args:
        looker (Object): Object doing the looking.
        **kwargs (dict): Arbitrary, optional arguments for users
            overriding the call (unused by default).
    """
    if not looker:
      return ""
    # get and identify all objects
    visible = (con for con in self.contents if con != looker and con.access(looker, "view"))
    exits, users, things = [], [], defaultdict(list)
    for con in visible:
      key = con.get_display_name(looker)
      if not key:
        # skip any no-description things
        continue
      if con.destination:
        exits.append(key)
      elif con.has_account:
        users.append("|c%s|n" % key)
      else:
        # things can be pluralized
        things[key].append(con)
    # get description, build string
    string = "|c%s|n\n" % self.get_display_name(looker)

    if not kwargs.get('brief', False):
      desc = self.choose_desc(looker)
      if desc:
        string += "%s\n" % desc
    if exits:
      string += "\n" + "\n".join(exits)
    if users or things:
      # handle pluralization of things (never pluralize users)
      thing_strings = []
      for key, itemlist in sorted(things.items()):
        nitem = len(itemlist)
        if nitem == 1:
          key, _ = itemlist[0].get_numbered_name(nitem, looker, key=key)
        else:
          key = [item.get_numbered_name(nitem, looker, key=key)[1] for item in itemlist][0]
        thing_strings.append(key)
      string += "\n|wYou see:|n " + list_to_string(users + thing_strings)
    return string
