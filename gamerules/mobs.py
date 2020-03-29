import random
from evennia import TICKER_HANDLER
from evennia.prototypes import prototypes as protlib, spawner
from gamerules.special_room_kind import SpecialRoomKind
from gamerules.xp import calculate_kill_xp, set_xp, gain_xp

# AllStats.Tick.TkRandMove := AllStats.Tick.TkRandMove + 100;
MOB_GENERATOR_TICK_SECONDS = 10


def resolve_mob_attack(mob, target):
  # TODO: add hiding
  is_surprise = False
  damage = mob_attack_damage(mob, is_surprise)

  # TODO: consider mob.weapon_id / weapon_name
  attack_name = "claws"

  # attack message for target
  target.msg(attack_target_msg(mob.name, attack_name, damage))

  # attack message for room bystanders
  location_msg = attack_bystander_msg(mob.name, target.name, attack_name, damage)
  mob.location.msg_contents(location_msg, exclude=[mob, target])

  # apply armor to reduce damage
  base_armor = target.base_armor
  deflect_armor = target.deflect_armor
  if deflect_armor > 0 and random.randint(0, 100) < deflect_armor:
    target.msg("The attack is deflected by your armor.")
    damage = int(damage / 2)
  if base_armor > 0:
    target.msg("The attack is partially blocked by your armor.")
    damage = int(damage * ((100 - base_armor) / 100))

  # target takes the damage
  target.gain_health(-damage, damager=mob, weapon_name=attack_name)


def mob_attack_damage(mob, is_surprise=False):
  rand_multiplier = .7 if is_surprise else random.random()
  # TODO: consider mob.level_damage?
  dmg = mob.base_damage + random.randint(0, mob.random_damage)
  if is_surprise:
    dmg = dmg + int(dmg * attacker.shadow_damage_percent / 100)
  return dmg  


def mob_death(mob, killer=None):
  if killer:
    killer.msg(f"You killed {mob.key}!")
    xp = calculate_kill_xp(killer.db.xp, mob.db.xp)
    gain_xp(killer, xp)
  mob.location.msg_contents(
    f"{mob.key} disappears in a cloud of greasy black smoke.", exclude=[mob])
  # TODO: object drop
  # TODO: gold drop
  mob.location = None
  mob.delete()


def add_mob_generator_ticker(subject):
  id_string = f"tick_mob_generator_{subject.key}"
  store_key = TICKER_HANDLER.add(MOB_GENERATOR_TICK_SECONDS, tick_mob_generator, id_string, False, subject)
  subject.db.mob_generator_ticker_key = store_key


def remove_mob_generator_ticker(subject):
  try:
    TICKER_HANDLER.remove(store_key=subject.db.mob_generator_ticker_key)
  except KeyError:
    pass
  subject.db.mob_generator_ticker_key = None


def tick_mob_generator(subject):
  if subject.location.is_special_kind(SpecialRoomKind.NO_COMBAT):
    # never spawn in a no-combat room
    return

  if subject.location.is_special_kind(SpecialRoomKind.MONSTER_GENERATOR):
    spawn_chance = subject.location.magnitude(SpecialRoomKind.MONSTER_GENERATOR)
  else:
    # always a 1% chance
    spawn_chance = 1

  # spawn_chance = 50

  if random.randint(0, 100) < spawn_chance:
    # yay, let's make a monster
    spawn_mob(subject.location, subject.level)


def spawn_mob(location, level):
  tags = [f"min_level_{x}" for x in range(level+1)]
  mob_prototypes = protlib.search_prototype(tags=tags)
  if not mob_prototypes:
    # no valid prototypes found
    return
  proto_choice = random.choice(mob_prototypes)
  mob = spawner.spawn(proto_choice['prototype_key'])[0]
  mob.location = location
  location.msg_contents(f"A {mob.key} appears!")
