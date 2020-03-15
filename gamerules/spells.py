import random
from gamerules.hiding import find_unhidden, reveal
from gamerules.spell_effect_kind import SpellEffectKind


def can_cast_spell(caster, spell):
  # TODO: convert to character_class.key?
  if spell.class_id and spell.class_id != caster.character_class.record_id:
    caster.msg("You are the wrong class to cast that spell.")
    return False

  if spell.group and spell.group != caster.character_class.group:
    caster.msg("You are the wrong group to cast that spell.")
    return False

  if spell.min_level > caster.level:
    caster.msg(f"Your level is too low to cast {spell.key}.")
    return False

  mana_cost = spell.mana + spell.level_mana * caster.level
  if mana_cost > caster.db.mana:
    caster.msg("You do not have enough mana.")
    return False


def cast_spell(caster, spell, target=None):
  # TODO: convert to character_class.key?
  if spell.class_id and spell.class_id != caster.character_class.record_id:
    caster.msg("You are the wrong class to cast that spell.")
    return

  if spell.group and spell.group != caster.character_class.group:
    caster.msg("You are the wrong group to cast that spell.")
    return

  if spell.min_level > caster.level:
    caster.msg(f"Your level is too low to cast {spell.key}.")
    return

  mana_cost = spell.mana + spell.level_mana * caster.level
  if mana_cost > caster.db.mana:
    caster.msg("You do not have enough mana.")
    return

  # possibly reveal caster
  if spell.reveals and caster.is_hiding:
      reveal(caster)

  # possibly fail
  if spell.failure_chance and random.randint(0, 100) < spell.failure_chance:
    if spell.failure_desc:
      caster.msg(spell.failure_desc)
    else:
      caster.msg("Your spell failed!")
    return

  # deduct mana
  caster.gain_mana(-mana_cost)

  # send messages
  # TODO: handle spell.silent checks for messaging
  caster.msg(f"You cast {spell.key}.")
  caster.location.msg_contents(
    f"{caster.key} casts {spell.key}.", exclude=[caster])
  if spell.caster_desc:
    caster.msg(spell.caster_desc)

  if spell.victim_desc:
    victim_desc = spell.victim_desc.replace("#", caster.key)
    if spell.affects_room:
      caster.location.msg_contents(victim_desc, exclude=[caster])
    elif target:
      target.msg(victim_desc)
  # TODO: our room descriptions / alignment field??? seem off. DEBUG and look at old pascal code.
  #if spell.room_desc:
  #  caster.location.msg_contents(spell.room_desc, exclude=[caster, target])
  # TODO: do we need to consider effect vs. room for msgs?

  # apply spell effects
  for effect in spell.effects:
    apply_spell_effect(effect, caster, target)


def apply_spell_effect(effect, caster, target=None):
  if effect.effect_kind == SpellEffectKind.CURE_POISON:
    apply_cure_poison_effect(effect, caster, target)
  elif effect.effect_kind == SpellEffectKind.STRENGTH:
    apply_strength_effect(effect, caster, target)
  elif effect.effect_kind == SpellEffectKind.SPEED:
    apply_speed_effect(effect, caster, target)
  elif effect.effect_kind == SpellEffectKind.INVISIBLE:
    apply_invisible_effect(effect, caster, target)
  elif effect.effect_kind == SpellEffectKind.SEE_INVISIBLE:
    apply_see_invisible_effect(effect, caster, target)
  elif effect.effect_kind == SpellEffectKind.HEAL:
    apply_heal_effect(effect, caster, target)
  elif effect.effect_kind == SpellEffectKind.HURT:
    apply_hurt_effect(effect, caster, target)
  elif effect.effect_kind == SpellEffectKind.SLEEP:
    apply_sleep_effect(effect, caster, target)
  elif effect.effect_kind == SpellEffectKind.PUSH:
    apply_push_effect(effect, caster, target)
  elif effect.effect_kind == SpellEffectKind.ANNOUNCE:
    apply_announce_effect(effect, caster, target)
  elif effect.effect_kind == SpellEffectKind.COMMAND:
    apply_command_effect(effect, caster, target)
  elif effect.effect_kind == SpellEffectKind.DISTANCE_HURT:
    apply_distance_hurt_effect(effect, caster, target)
  elif effect.effect_kind == SpellEffectKind.DETECT_MAGIC:
    apply_detect_magic_effect(effect, caster, target)
  elif effect.effect_kind == SpellEffectKind.FIND_PERSON:
    apply_find_person_effect(effect, caster, target)
  elif effect.effect_kind == SpellEffectKind.LOCATE:
    apply_locate_effect(effect, caster, target)
  elif effect.effect_kind == SpellEffectKind.WEAK:
    apply_weak_effect(effect, caster, target)
  elif effect.effect_kind == SpellEffectKind.SLOW:
    apply_slow_effect(effect, caster, target)


def apply_cure_poison_effect(effect, caster, target):
  pass


def apply_strength_effect(effect, caster, target):
  pass


def apply_speed_effect(effect, caster, target):
  pass


def apply_invisible_effect(effect, caster, target):
  pass


def apply_see_invisible_effect(effect, caster, target):
  pass


def apply_heal_effect(effect, caster, target):
  pass


def apply_hurt_effect(effect, caster, target):
  # calculate damage
  base = effect.param_1
  level_base = effect.param_2
  rand = effect.param_3
  level_rand = effect.param_4
  base_dmg = base + level_base * caster.level
  random_dmg = rand + level_rand * caster.level
  damage = base_dmg + random.randint(0, random_dmg)
  # dish it out
  if effect.affects_room:
    # everyone in room
    for occupant in caster.location.contents:
      if occupant != caster and hasattr(occupant, "gain_health"):
        occupant.gain_health(-damage, damager=caster)
  else:
    # just single target
    if target and hasattr(target, "gain_health"):
      target.gain_health(-damage, damager=caster)
  if effect.affects_caster and hasattr(caster, "gain_health"):
    target.gain_health(-damage, damager=None)


def apply_sleep_effect(effect, caster, target):
  pass


def apply_push_effect(effect, caster, target):
  pass


def apply_announce_effect(effect, caster, target):
  pass


def apply_command_effect(effect, caster, target):
  pass


def apply_distance_hurt_effect(effect, caster, target):
  pass


def apply_detect_magic_effect(effect, caster, target):
  pass


def apply_find_person_effect(effect, caster, target):
  pass


def apply_locate_effect(effect, caster, target):
  pass


def apply_weak_effect(effect, caster, target):
  pass


def apply_slow_effect(effect, caster, target):
  pass

