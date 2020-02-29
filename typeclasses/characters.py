"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""
from random import randint

from evennia import DefaultCharacter, search_object
from evennia.commands import cmdhandler

from gamerules.combat import die
from gamerules.health import health_msg
from gamerules.xp import level_from_xp



class Character(DefaultCharacter):
  """
  The Character defaults to reimplementing some of base Object's hook methods with the
  following functionality:

  at_basetype_setup - always assigns the DefaultCmdSet to this object type
                (important!)sets locks so character cannot be picked up
                and its commands only be called by itself, not anyone else.
                (to change things, use at_object_creation() instead).
  at_after_move(source_location) - Launches the "look" command after every move.
  at_post_unpuppet(account) -  when Account disconnects from the Character, we
                store the current location in the pre_logout_location Attribute and
                move it to a None-location so the "unpuppeted" character
                object does not need to stay on grid. Echoes "Account has disconnected"
                to the room.
  at_pre_puppet - Just before Account re-connects, retrieves the character's
                pre_logout_location Attribute and move it back on the grid.
  at_post_puppet - Echoes "AccountName has entered the game" to the room.

  """
  def at_object_creation(self):
    """Called at initial creation."""
    super().at_object_creation()
    self.set_field_defaults()

  def set_field_defaults(self):
    """Set various field defaults in an idempotent way."""
    # TODO: figure health etc from level and class
    if self.db.max_health is None:
      self.db.max_health = 1000
    if self.db.health is None:
      self.db.health = 1000
    if self.db.brief_descriptions is None:
      self.db.brief_descriptions = False      
    # TODO: support various equipment slots
    # checking None to set None is pointless
    if self.db.gold_in_bank is None:
      self.db.gold_in_bank = 0
    if self.db.xp is None:
      self.db.xp = 0

  def execute_cmd(self, raw_string, session=None, **kwargs):
    """Support execute_cmd(), like account and object."""
    return cmdhandler.cmdhandler(
        self, raw_string, callertype="account", session=session, **kwargs
    )

  # helper getters

  def carried_gold_amount(self):
    gold = self.search("gold",
      candidates=self.contents, typeclass="typeclasses.objects.Gold", quiet=True)
    if len(gold) > 0:
      return gold[0].db.amount
    return 0

  def level(self):
    return level_from_xp(self.db.xp)

  def classname(self):
    # TODO: pull from character class
    return "Peasant"

  # at_* event notifications

  def at_after_move(self, source_location, **kwargs):
    # override to apply our brief descriptions setting
    if self.location.access(self, "view"):
      self.msg(self.at_look(self.location, brief=self.db.brief_descriptions))

  def at_object_leave(self, obj, target_location):
    # called when an object leaves this object in any fashion
    super().at_object_leave(obj, target_location)
    # unequip if equipped
    if obj == self.db.equipped_armor:
      self.db.equipped_armor = None
    elif obj == self.db.equipped_weapon:
      self.db.equipped_weapon = None

  def at_weapon_hit(self, attacker, weapon, damage):
    # TODO: apply armor
    armor = self.db.equipped_armor
    if armor:
      if armor.db.deflect_armor > 0 and randint(0, 100) < armor.db.deflect_armor:
        self.msg("The attack is deflected by your armor.")
        attacker.msg(f"Your weapon is deflected by {self.key}'s armor.")
        damage = int(damage / 2)
      if armor.db.base_armor > 0:
        self.msg("The attack is partially blocked by your armor.")
        attacker.msg(f"Your weapon is partially blocked by {self.key}'s armor.")
        damage = int(damage * ((100 - armor.db.base_armor) / 100))
    self.at_damage(damage, damager=attacker)

  def at_damage(self, damage, damager=None):
    self.db.health = max(self.db.health - damage, 0)
    self.msg(f"You take {damage} damage.")
    self.msg(health_msg("You", self.db.health))
    self.location.msg_contents(health_msg(self.key, self.db.health), exclude=[self])
    if self.db.health <= 0:
      die(self, damager)

  def at_heal(self, amount):
    self.db.health = min(self.db.health + amount, self.db.max_health)
    self.msg(health_msg("You", self.db.health))
    self.location.msg_contents(health_msg(self.key, self.db.health), exclude=[self])

  def at_gain_xp(self, xp):
    new_xp = max(1000, self.db.xp + xp)
    self.at_set_xp(new_xp)

  def at_set_xp(self, new_xp):
    old_level = self.level()
    self.db.xp = new_xp
    new_level = self.level()
    if old_level != new_level:
      self.msg(f"You are now level {new_level}.")

