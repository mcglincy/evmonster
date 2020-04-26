import random

from evennia.utils.search import search_object
from gamerules.combat_msgs import *
from gamerules.gold import give_starting_gold
from gamerules.find import is_hidden, keymatch
from gamerules.hiding import reveal
from gamerules.saving_throw import make_saving_throw
from gamerules.talk import msg_global
from gamerules.xp import calculate_kill_xp, set_xp, gain_xp


PUNCH_KINDS = 15  # 0-15


def is_attackable(target):
  # TODO: consider hasattr(target, "gain_health") ?
  return (target.is_typeclass("typeclasses.characters.Character")
    or target.is_typeclass("typeclasses.mobs.Mob", exact=False))


def find_first_attackable(container, key):
  for obj in container.contents:
    if keymatch(obj, key) and not is_hidden(obj) and is_attackable(obj):
      return obj
  return None


def resolve_attack(attacker, target):
  weapon = attacker.equipped_weapon
  if not weapon and not attacker.has_claws:
    attacker.msg("You have no equipped weapon!")
    return
  if attacker.key == target.key:
    attacker.msg("You can't attack yourself!")
    return
  # TODO: add more rigorous can-attack checks
  if not is_attackable(target):
    attacker.msg("You can't attack that.")
    return
  if target.is_dead:
    # already dead
    return

  is_surprise = False
  if attacker.is_hiding:
    attacker.msg(f"You unexpectedly attack {target.name}!")
    target.msg("Surprise!!!")
    reveal(attacker)
    is_surprise = True

  # calculate damage
  damage = attack_damage(attacker, weapon, is_surprise)

  # attack message for attacker
  attack_name = weapon.key if weapon else "claws"
  attacker.msg("|w" + attack_attacker_msg(target.name, attack_name, damage))

  # attack message for target
  target.msg("|w" + attack_target_msg(attacker.name, attack_name, damage))

  # attack message for room bystanders
  location_msg = attack_bystander_msg(attacker.name, target.name, attack_name, damage)
  attacker.location.msg_contents(location_msg, exclude=[attacker, target])

  # apply armor to reduce damage
  damage = apply_armor(target, damage)

  # check for poison
  if random.randint(0, 100) < attacker.poison_chance:
    attacker.msg(f"You've poisoned {target.name}!")
    if not make_saving_throw(target, "poison"):
      target.msg(f"You've been poisoned by {attacker.name}'s {attack_name}!")
      attacker.location.msg_contents(
        f"{attacker.name} has poisoned {target.name}!", exclude=[attacker, target])
      target.db.poisoned = True

  # target takes the damage, and maybe dies
  target.gain_health(-damage, damager=attacker, weapon_name=attack_name)


def apply_armor(target, damage):
  final_damage = damage
  base_armor = target.base_armor
  deflect_armor = target.deflect_armor
  if deflect_armor > 0 and random.randint(0, 100) < deflect_armor:
    target.msg("The attack is deflected by your armor.")
    final_damage = int(damage / 2)
  if base_armor > 0:
    target.msg("The attack is partially blocked by your armor.")
    final_damage = int(damage * ((100 - base_armor) / 100))
  return final_damage


def attack_damage(attacker, weapon, is_surprise=False):
  rand_multiplier = .7 if is_surprise else random.random()
  if weapon:
    # attacker weapon damages may be the sum of several equipped objects
    dmg = attacker.base_weapon_damage + int(attacker.random_weapon_damage * rand_multiplier)
    dmg = int(dmg * attacker.total_weapon_use / 100)
  else:
    # claws
    dmg = (
      attacker.base_claw_damage
      + int(attacker.random_claw_damage * rand_multiplier)
      + attacker.level_claw_damage * attacker.level
      )
  if is_surprise:
    dmg = dmg + int(dmg * attacker.shadow_damage_percent / 100)
  # make sure we don't allow negative damage,
  # as some classes have negative shadow_damage_percent
  return max(dmg, 0)


def resolve_punch(attacker, target):
  if not hasattr(target, "gain_health"):
    attacker.msg("You can't punch that.")
    return
  if target.is_dead:
    return

  attack_name = "fists of fury"

  if target == attacker:
    # surprisingly enough, you can punch yourself
    if attacker.is_hiding:
      reveal(attacker)
    attacker.msg("You catch yourself off guard with an elbow to the ribs, arrg!")
    attacker.location.msg(f"{attacker.name} is heading for the void.", exclude=[attacker])
    attacker.gain_health(-100, damager=attacker, weapon_name=attack_name)
    return

  is_surprise = False
  if attacker.is_hiding:
    attacker.msg(f"You pounce unexpectedly on {target.name}!")
    target.msg(f"{attacker.name} pounces on you from the shadows!")
    attacker.location.msg_contents(
      f"{attacker.name} jumps out of the shadows and attacks {target.name}.",
      exclude=[attacker, target])
    reveal(attacker)
    is_surprise = True

  punch_num = random.randint(0, PUNCH_KINDS)
  if attacker.db.health < 75:
    punch_num = 16

  attacker.msg(punch_attacker_msg(target.name, punch_num))
  target.msg(punch_target_msg(attacker.name, punch_num))
  attacker.location.msg_contents(
    punch_bystander_msg(attacker.name, target.name, punch_num),
    exclude=[attacker, target])

  damage = punch_damage(punch_num)
  target.gain_health(-damage, damager=attacker, weapon_name=attack_name)


def punch_damage(num):
  if num < 7:
    return 25
  elif num < 12:
    return 50
  elif num < 15:
    return 75
  else:
    return 100


def character_death(victim, killer=None, weapon_name=None):
  # send an appropriate global death message
  if killer and weapon_name:
    msg_global(f"{victim.name} has been slain by {killer.name}'s {weapon_name}.")
  elif killer:
    msg_global(f"{victim.name} has been slain by {killer.name}.")
  elif weapon_name:
    msg_global(f"{victim.name} has been slain by a {weapon_name}.")
  else:
    msg_global(f"{victim.name} has died of mysterious causes.")

  # award xp to the killer
  if killer and killer.is_typeclass("typeclasses.characters.Character"):
    killer.msg(f"You killed {victim.name}!")
    xp = calculate_kill_xp(killer.db.xp, victim.db.xp)
    gain_xp(killer, xp)

  # victim drops everything they were holding before leaving room
  for obj in victim.contents:
    if obj.worth:
      # only drop things with value
      # TODO: possible destroy chance?
      # since drop is now a queued commend, do all the steps of a drop ourselves
      if obj.at_before_drop(victim):
        obj.move_to(victim.location, quiet=True)
        victim.msg(f"You drop {obj.name}.")
        victim.location.msg_contents(f"{victim.name} drops {obj.name}.", exclude=victim)
        obj.at_drop(victim)
      else:
        obj.delete()
    else:
      # nuke worthless objects
      obj.delete()

  # victim goes to the void
  the_void = search_object("Void")[0]
  if the_void:
    victim.location.msg_contents(
      f"{victim.name} disappears in a cloud of greasy black smoke.", exclude=[victim])
    victim.move_to(the_void, quiet=True)

  # reduce victim xp/level
  set_xp(victim, int(victim.db.xp / 2))

  # clear/reset various stats
  reset_victim_state(victim)

  # starting gold!
  give_starting_gold(victim)


def reset_victim_state(victim):
  # victim.db.health = 1
  victim.db.mana = 0
  victim.db.poisoned = False
  victim.ndb.active_command = None
  victim.ndb.command_queue.clear()
  victim.ndb.frozen_until = 0
  victim.ndb.hiding = 0
  victim.ndb.resting = False
