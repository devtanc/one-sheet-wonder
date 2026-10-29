"""Difficulty steps: buy whole, visible steps from a scenario's rating, then fine-tune enemy HP within a narrow band.

Potions are not a difficulty lever: the hero's inventory (gold, potions, items) carries over between scenarios, so a
scenario cannot set it. Balance is calibrated against a new hero's kit: 6 gold, 3 potions, full HP.
"""
import math
STEP_DMG, STEP_POT, HP_SLOPE = 0.53, 0.27, 3.3          # log-odds per step (lever experiment); HP: per unit ln(scale)
TARGET = {"Easy": 0.80, "Normal": 0.55, "Hard": 0.30}
START_POTIONS, MAX_DMG_STEPS = 3, 3
def logit(p): return math.log(p / (1 - p))
def plan(rating, tier):
    need = logit(TARGET[tier]) - logit(rating)          # >0: make it easier
    n_d = max(-MAX_DMG_STEPS, min(MAX_DMG_STEPS, int(need / STEP_DMG)))   # whole damage steps (truncated: never overshoot)
    rem = need - n_d * STEP_DMG
    hp = math.exp(-rem / HP_SLOPE)                      # enemy HP takes the rest (fine-tuned by simulation)
    return dict(dmg_add=-n_d, potions=START_POTIONS, hp_scale=round(hp, 2))
