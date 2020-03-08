"""
Exits

Exits are connectors between Rooms. An exit always has a destination property
set and has a single command defined on itself with the same name as its key,
for allowing Characters to traverse the exit to its destination.

"""
from evennia import DefaultExit
from commands.movement import CmdExit
from gamerules.exit_effects import apply_exit_effect
from typeclasses.exit_kind import ExitKind


def exit_opposite(key):
  if key == "north":
    return "south"
  if key == "south":
    return "north"
  if key == "east":
    return "west"
  if key == "west":
    return "east"
  if key == "up":
    return "down"
  if key == "down":
    return "up"
  return None


class Exit(DefaultExit):
  """
  Exits are connectors between rooms. Exits are normal Objects except
  they defines the `destination` property. It also does work in the
  following methods:

   basetype_setup() - sets default exit locks (to change, use `at_object_creation` instead).
   at_cmdset_get(**kwargs) - this is called when the cmdset is accessed and should
                            rebuild the Exit cmdset along with a command matching the name
                            of the Exit object. Conventionally, a kwarg `force_init`
                            should force a rebuild of the cmdset, this is triggered
                            by the `@alias` command when aliases are changed.
   at_failed_traverse() - gives a default error message ("You cannot
                          go there") if exit traversal fails and an
                          attribute `err_traverse` is not defined.

  Relevant hooks to overload (compared to other types of Objects):
      at_traverse(traveller, target_loc) - called to do the actual traversal and calling of the other hooks.
                                          If overloading this, consider using super() to use the default
                                          movement implementation (and hook-calling).
      at_after_traverse(traveller, source_loc) - called by at_traverse just after traversing.
      at_failed_traverse(traveller) - called by at_traverse if traversal failed for some reason. Will
                                      not be called if the attribute `err_traverse` is
                                      defined, in which case that will simply be echoed.
  """
  # use our own exit command, to track last command for '.'
  exit_command = CmdExit

  def at_object_creation(self):
    super().at_object_creation()
    self.db.exit_kind = ExitKind.OPEN
    self.db.exit_desc = None
    self.db.exit_effect_kind = None
    self.db.exit_effect_value = None
    self.db.fail_msg = None
    self.db.success_msg = None
    # departure message to show others when someone uses this exit
    self.db.go_in_msg = None
    # note: come_out_msg has goofball semantics; see at_traverse()
    # arrival message to show others when someone uses the "opposite" exit
    self.db.come_out_msg = None

  def at_traverse(self, traversing_object, target_location, **kwargs):
    """Override superclass for custom exit messaging.

    Args:
        traversing_object (Object): Object traversing us.
        target_location (Object): Where target is going.
        **kwargs (dict): Arbitrary, optional arguments for users
            overriding the call (unused by default).
    """
    source_location = traversing_object.location

    # see if target_location has a mirror exit for us
    # e.g., if we're "up", see if there's a "down", with a come_out_msg
    # TODO: this is stupid to do dynamically, and confusing to boot.
    # Could we figure this out when generating build.ev?
    come_out_msg = None
    opp_exit_key = exit_opposite(self.key)
    target_exits = target_location.search(opp_exit_key,
      candidates=target_location.contents, typeclass="typeclasses.exits.Exit", quiet=True)
    if len(target_exits) > 0:
      come_out_msg = target_exits[0].db.come_out_msg

    # pass our various exit messages down
    if traversing_object.move_to(target_location,
        success_msg=self.db.success_msg,
        go_in_msg=self.db.go_in_msg,
        come_out_msg=come_out_msg):
      self.at_after_traverse(traversing_object, source_location)
    else:
      self.at_failed_traverse(traversing_object)

  def at_after_traverse(self, traversing_object, source_location, **kwargs):
    # note: this is taking place *after* we have moved to the new location.
    if self.db.exit_effect_kind:
      apply_exit_effect(traversing_object, self.db.exit_effect_kind, self.db.exit_effect_value)

  def at_failed_traverse(self, traversing_object, **kwargs):
    if self.db.fail_msg:
      traversing_object.msg(self.db.fail_msg)

  def get_display_name(self, looker, **kwargs):
    if self.db.exit_desc:
      return self.db.exit_desc
    elif self.name in ["north", "south", "east", "west"]:
      return f"To the {self.name} is {self.destination.key}."
    elif self.name in ["up", "down"]:
      return f"The {self.destination.key} is {self.name} from here."
    if self.locks.check_lockstring(looker, "perm(Builder)"):
      return "{}(#{})".format(self.name, self.id)
    return self.name
