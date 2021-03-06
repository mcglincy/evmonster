"""
Exits

Exits are connectors between Rooms. An exit always has a destination property
set and has a single command defined on itself with the same name as its key,
for allowing Characters to traverse the exit to its destination.

"""
from evennia import DefaultExit
from commands.movement import CmdExit
from gamerules.exit_effects import apply_exit_effect
from gamerules.exit_kind import ExitKind
from gamerules.mobs import maybe_spawn_mob_in_lair


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
    self.db.password = None
    self.db.required_object = None
    self.db.hiding = 0
    # description to show if exit was hidden then found
    self.db.hidden_desc = None
    self.db.auto_look = True

  def at_traverse(self, traversing_object, target_location, **kwargs):
    """Override superclass for custom exit messaging.

    Args:
        traversing_object (Object): Object traversing us.
        target_location (Object): Where target is going.
        **kwargs (dict): Arbitrary, optional arguments for users
            overriding the call (unused by default).
    """
    source_location = traversing_object.location

    # check for mob lair at our destination
    maybe_spawn_mob_in_lair(target_location)

    if traversing_object.move_to(target_location,
        # TODO: this is too-powerful way to control character looking
        move_hooks=self.db.auto_look != False,
        # pass our various exit messages down
        success_msg=self.db.success_msg,
        go_in_msg=self.db.go_in_msg,
        come_out_msg=self.db.come_out_msg
        ):
      self.at_after_traverse(traversing_object, source_location)
    else:
      self.at_failed_traverse(traversing_object)

  def at_after_traverse(self, traversing_object, source_location, **kwargs):
    # note: this is taking place *after* we have moved to the new location.
    if self.db.exit_effect_kind:
      apply_exit_effect(traversing_object, source_location, self.db.exit_effect_kind, self.db.exit_effect_value)
    if self.db.hidden_desc:
      # re-hide the exit
      self.make_invisible()
      self.make_impassable()

  def at_failed_traverse(self, traversing_object, **kwargs):
    fail_msg = self.db.fail_msg if self.db.fail_msg else "You can't go that way."
    traversing_object.msg(fail_msg)

  def make_passable(self):
    self.locks.remove("traverse")
    self.locks.add("traverse:all()")

  def make_impassable(self):
    self.locks.remove("traverse")
    self.locks.add("traverse:none()")

  def make_visible(self):
    self.db.hiding = 0
    self.locks.remove("view")
    self.locks.add("view:all()")

  def make_invisible(self):
    self.db.hiding = 1
    self.locks.remove("view")
    self.locks.add("view:perm(see_hidden)")

  def get_display_name(self, looker, **kwargs):
    if self.db.exit_desc:
      display_name = self.db.exit_desc
    elif self.db.exit_kind == ExitKind.NO_EXIT:
      # won't show for non-admin users
      display_name = ""
    elif self.name in ["north", "south", "east", "west"]:
      display_name = f"To the {self.name} is {self.destination.key}."
    elif self.name in ["up", "down"]:
      display_name = f"The {self.destination.key} is {self.name} from here."
    else:
      display_name = self.name
    if (self.locks.check_lockstring(looker, "perm(Builder)")
      or self.locks.check_lockstring(looker, "perm(Developer)")):
      display_name += f"(#{self.id}, {self.key}, {ExitKind(self.db.exit_kind).name})"
    return display_name