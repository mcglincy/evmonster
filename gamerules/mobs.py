import random
from evennia import create_object
from evennia.prototypes import prototypes as protlib, spawner
from evennia.utils.search import search_object_by_tag
from gamerules.combat import apply_armor, attack_bystander_msg, attack_target_msg
from gamerules.special_room_kind import SpecialRoomKind
from gamerules.xp import calculate_kill_xp, set_xp, gain_xp

# never spawn more than this many mobs in the world
MAX_MOBS = 20

MOB_NAMES = [
  'Agroth','Agrit','Atamut','Ali Baba','Arnold','Aluzinthra','Atariana','Agmeish',
  'Buster','Boozer','Brent','Bugzool','Butch','Barahirin','Broog','Bidrethmog',
  'Buffy','Chadwik','Chuck','Chimlick','Cheuk','Chumliz','Cromwell','Carbanor',
  'Canawok','Cordread','Cirith','Droog','Dirk','Daldinaron','Denowet','Draka',
  'Dum dum','Dimwit','Dumshitz','Elvis','Ecthellion','Eneroth','Elethil',
  'Eugumoot','Eleduin','Egor','Feanor','Fargblatz','Farging','Fletch','Friggit',
  'Gothmog','Grondin','Gangleous','Grog','Gerland','Ginreth','Glockbleshz',
  'Grouzithab','Herbruk','Hallwaith','Helmut','Hercimer','Howarmuk','Henchhelm',
  'Hanmaddin','Ingwe','Ingrish','Jerluk','Jabbalop','Jocko','Jeth','Junga','Jinga',
  'Jimba','Krotche','Kunta','Killroy','Kaputa','Kuch','Kumquat','Kurgan','Khadaffy',
  'Krazool','Lenin','Leonard','Leo','Lear','Louie','Lister','Laurendil','Lokesiltary',
  'Mudarasah','Morgoth','Mugwump','Melmen','Masnads','Mrokbut','Merlkyteral',
  'Milknenrou','Mybalon','Mordenkainen','Nadien','Opie','Orgrond','Orville','Ogden',
  'Orion','Pharelen','Pogo','Pfzarrak','Poofley','Proklmt','Rellinger','Rhunwik',
  'Rugrat','Retred','Rocky','Rhygon','Rejuon','Rogundin','Roxanne',
  'Sceleron','Scarythe','Smegma','Spunk','Sindar','Sarek','Swatme','Swishme',
  'Tellemicus','Talleyrand','Turin','Tyme','Vermothrax','Whacker'
]

def resolve_mob_attack(mob, target, attack_name="claws"):
  if target.is_dead:
    # already dead
    return

  # TODO: add hiding
  is_surprise = False
  damage = mob_attack_damage(mob, is_surprise)

  # attack message for target
  target.msg("|w" + attack_target_msg(mob.name, attack_name, damage))

  # attack message for room bystanders
  location_msg = attack_bystander_msg(mob.name, target.name, attack_name, damage)
  mob.location.msg_contents(location_msg, exclude=[mob, target])

  # apply armor to reduce damage
  damage = apply_armor(target, damage)

  # target takes the damage
  target.gain_health(-damage, damager=mob, weapon_name=attack_name)


def mob_attack_damage(mob, is_surprise=False):
  rand_multiplier = .7 if is_surprise else random.random()
  # TODO: consider mob.level_damage?
  dmg = mob.base_damage + random.randint(0, mob.random_damage)
  if is_surprise:
    dmg = dmg + int(dmg * mob.shadow_damage_percent / 100)
  return dmg  


def mob_death(mob, killer=None):
  if killer:
    killer.msg(f"You killed {mob.key}!")
    xp = calculate_kill_xp(killer.db.xp, mob.db.xp)
    gain_xp(killer, xp)

  if mob.db.drop_gold:
    gold = create_object("typeclasses.objects.Gold", key="gold")
    gold.add(mob.db.drop_gold)
    # use move_to() so we invoke StackableObject accumulation
    gold.move_to(mob.location, quiet=True)
    mob.location.msg_contents(f"{mob.key} drops {mob.db.drop_gold} gold.")

  if mob.db.drop_object_id:
    tags = ["object", f"record_id_{mob.db.drop_object_id}"]
    prototypes = protlib.search_prototype(tags=tags)
    if prototypes:
      obj = spawner.spawn(prototypes[0]["prototype_key"])[0]
      obj.location = mob.location
      mob.location.msg_contents(f"{mob.key} drops {obj.name}.")

  mob.location.msg_contents(
    f"{mob.key} disappears in a cloud of greasy black smoke.", exclude=[mob])
  mob.location = None
  mob.delete()


def generate_mob(location, level):
  tags = [f"min_level_{x}" for x in range(level+1)]
  mob_prototypes = protlib.search_prototype(tags=tags)
  if not mob_prototypes:
    # no valid prototypes found
    return
  proto = random.choice(mob_prototypes)
  mob_name = f"{random.choice(MOB_NAMES)} the {proto['key']}"
  mob = spawner.spawn({
    'prototype_parent': proto['prototype_key'], 'prototype_key': mob_name, 'key': mob_name,
  })[0]
  mob.location = location
  location.msg_contents(f"A {mob.key} appears!")


def has_players_or_mobs(location):
  for obj in location.contents:
    if (obj.is_typeclass("typeclasses.characters.Character")
      or obj.is_typeclass("typeclasses.mobs.Mob", exact=False)):
      return True
  return False


def mob_count():
  return len(all_mobs())


def all_mobs():
  return search_object_by_tag("mob")


def has_mobs(location):
  for obj in location.contents:
    if obj.is_typeclass("typeclasses.mobs.Mob", exact=False):
      return True
  return False


def find_mob_prototype(mob_id):
  record_id_tag = f"record_id_{mob_id}"
  # unfortunately search_prototype() tags are OR'd,
  # so we can't search for tags "mob" AND "record_id_123".
  # Instead we do the second-pass filtering ourself.
  mob_prototypes = protlib.search_prototype(tags=["mob"])
  for proto in mob_prototypes:
    if record_id_tag in proto["prototype_tags"]:
      return proto
  return None


def maybe_spawn_mob_in_lair(location):
  if not location.is_special_kind(SpecialRoomKind.MONSTER_LAIR):
    # not a lair
    return
  if has_players_or_mobs(location):
    # only spawn a new mob in a room devoid of players or mobs
    return
  mob_id = location.magnitude(SpecialRoomKind.MONSTER_LAIR)
  proto = find_mob_prototype(mob_id)
  if not proto:
    # no such mob found
    return
  mob_name = f"{random.choice(MOB_NAMES)} the {proto['key']}"
  mob = spawner.spawn({
    'prototype_parent': proto['prototype_key'], 'prototype_key': mob_name, 'key': mob_name,
  })[0]
  # stay in the lair
  mob.location = location
  mob.db.moves_between_rooms = False
