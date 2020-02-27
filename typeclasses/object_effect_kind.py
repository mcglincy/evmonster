from enum import IntEnum


class ObjectEffectKind(IntEnum):
  ATTACK_SPEED = 13
  WEAPON_BASE_DAMAGE = 27
  WEAPON_RANDOM_DAMAGE = 28
  BASE_ARMOR = 29
  DEFLECT_ARMOR = 30
  SPELL_ARMOR = 31
  SMALLEST_FIT = 32
  LARGEST_FIT = 33
  # spell deflect aka spell destroy
  SPELL_DEFLECT_ARMOR = 39
  THROW_BASE = 40
  THROW_RANDOM = 41
  THROW_RANGE = 42
  THROW_BEHAVIOR = 43 
