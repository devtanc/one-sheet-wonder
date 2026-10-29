"""Draft content pools for One Sheet Wonder scenario generation (engine version 01).

Enemy numbers are the calibrated Normal-tier values from the attack-board balance work; other bands and
difficulties scale them at generation. Money and prices are first drafts for the simulator to tune.
"""

# --- Enemies --------------------------------------------------------------------------------------------
# attacks: list of (damage, heavy); weak: (column pair, row); special: short sheet text.
MINIONS = [
    dict(name="Grunt",        hp=17, attacks=[(4, False)],                 weak=("5·9", 6),  reward=1, keywords=[]),
    dict(name="Archer",       hp=14, attacks=[(6, False)],                 weak=("4·10", 5), reward=1, keywords=[]),
    dict(name="Shieldbearer", hp=24, attacks=[(3, False)],                 weak=("4·10", 5), reward=2, keywords=['Bodyguard']),
    dict(name="Trapper",      hp=17, attacks=[(4, False)],                 weak=("5·9", 6),  reward=2, keywords=["Trapper 2"]),
    dict(name="Hexer",        hp=14, attacks=[(3, False)],                 weak=("3·11", 6), reward=2, keywords=['Daze']),
    dict(name="Brute",        hp=31, attacks=[(8, False), (12, True)],     weak=("3·11", 6), reward=3, keywords=["Bulk 1 A,I"]),
    dict(name="Cultist",      hp=15, attacks=[(3, False), (7, True)],      weak=("5·9", 6),  reward=1, keywords=[]),
    dict(name="Cutpurse",     hp=12, attacks=[(5, False)],                 weak=("4·10", 5), reward=2, keywords=["Thief 1"]),
    dict(name="Bone Hound",   hp=13, attacks=[(4, False), (4, False), (8, True)], weak=("5·9", 6), reward=1, keywords=[]),
    dict(name="Slime",        hp=22, attacks=[(3, False)],                 weak=("3·11", 6), reward=2, keywords=['Venom']),
]

MINIBOSSES = [
    dict(name="Brute Chief",     hp=46, attacks=[(9, False), (15, True)],             weak=("3·11", 6), reward=5, keywords=["Bulk 1 A,I"]),
    dict(name="Hex Witch",       hp=38, attacks=[(5, False), (9, False)],             weak=("3·11", 6), reward=4, keywords=['Daze']),
    dict(name="Trapmaster",      hp=40, attacks=[(6, False), (11, True)],             weak=("5·9", 6),  reward=4, keywords=["Trapper 2"]),
    dict(name="Juggernaut",      hp=60, attacks=[(9, False), (9, False), (18, True)], weak=("3·11", 6), reward=6, keywords=["Plate A,I"]),
    dict(name="Warband Captain", hp=44, attacks=[(7, False), (7, False), (12, True)], weak=("4·10", 5), reward=5, keywords=["Rally 1"]),
    dict(name="Bone Knight",     hp=48, attacks=[(8, False), (14, True)],             weak=("4·10", 5), reward=5, keywords=['Sunder']),
]

# Boss patterns use the Normal-tier boss numbers. tags: p = poisons on a hit, d = dazes on a hit,
# g = grabs on a hit (next attack 2 runners), x = piercing (half guard). Damage 0 = wind-up.
BOSSES = [
    dict(name="The Iron Tyrant",  pattern="Brute",    attacks=[(6, False, ""), (6, False, ""), (11, True, "")]),
    dict(name="Mother of Fangs",  pattern="Venom",    attacks=[(4, False, "p"), (6, False, ""), (4, False, "p"), (10, True, "")]),
    dict(name="The Pale Hex",     pattern="Hexer",    attacks=[(4, False, "d"), (6, False, ""), (10, True, "")]),
    dict(name="Chainjaw",         pattern="Grappler", attacks=[(4, False, "g"), (6, False, ""), (10, True, "")]),
    dict(name="Warlord Kragg",    pattern="Warlord",  attacks=[(0, False, ""), (15, True, ""), (6, False, ""), (6, False, "")]),
    dict(name="The Needle",       pattern="Piercer",  attacks=[(5, False, "x"), (6, False, ""), (10, True, "")]),
]
BOSS_HP = 420
# Henchmen: (minions, minibosses, weight out of 100, boss HP). Boss HP keeps the fight as winnable as a lone boss
# (boss-fight harness, 1,000 fights each). A miniboss plus a minion stayed too hard at any boss HP, so it is left out.
BOSS_HENCHMEN = [
    (0, 0, 80, 420),
    (1, 0, 10, 360),
    (2, 0, 6, 230),
    (0, 1, 4, 240),
]
BOSS_REWARD = 12

# Boss phase modules with the re-sorted rarities (C/U/R/L) and short sheet text.
TWISTS = {
    "Iron Wall": ("C", "Columns 6 and 8 blocked"), "Shieldwall": ("C", "Columns 3 and 11 blocked"),
    "Thick Hide": ("C", "Columns 3 and 11 deal 1"), "Trapper": ("U", "Two traps on your grid"),
    "Jinx": ("U", "2 and 12 are not wild"), "Plate": ("U", "Only columns 3 and 11 deal damage"),
    "Gatehouse": ("R", "Columns 6, 7 and 8 blocked"), "Daze": ("R", "Two pairs also fumble"),
    "Pin": ("L", "Only 2 runners"),
}
PRESSURES = {
    "Doom": ("C", "Heavy attacks +50%"), "Fortify": ("C", "Your attacks deal 3 less"),
    "Regenerate": ("C", "Heals 4 each round"), "Frenzy": ("U", "All attacks +50%"),
    "Haste": ("R", "Extra strike of 4 each round"), "Berserk": ("R", "Fumble counters deal 5"),
}
OPENINGS = {"Exposed": ("C", "Weak point 2 rows lower"), "Cracked Shell": ("L", "Columns 6-8 deal 1")}

PRICE = {1: 3, 2: 6, 3: 10}                 # gold per price tier $, $$, $$$ (draft)
START_MONEY = 6                             # a new hero's purse (inventory carries over; the simulator plays every scenario from this kit)
ANY_DOUBLE_BOSS = False                     # once the fuse is lit, only 1-1 or 6-6 brings the boss
SHOP_DANGER = 0                             # visiting the shopkeeper costs no danger
FUSE_STEER = 2.0                            # boss-roll chance multiplier for WIS steering (fit to simulation)

# --- Keywords -------------------------------------------------------------------------------------------
# Printed on cards as tags; the rules live in this glossary. Scope: on an enemy, while it lives; on an attack, when that
# attack hits (Daze and Pin then apply to your next attack); in a boss phase, for that phase.
ATTACK_TAG_KEYWORD = {"p": "Venom", "d": "Daze", "g": "Pin", "x": "Sunder"}
KEYWORDS = {   # mirrors the Scenario Sheet Spec glossary; X = the number after the keyword (on an attack, its damage)
    "Bodyguard": "The player must target this enemy before other enemies.",
    "Daze": "Past the danger line, two pairs also fumble. Attack: on hit, the player is Dazed during the player's next attack.",
    "Pin": "The player has 1 fewer runner. Attack: on hit, the player's next attack is Pinned.",
    "Venom": "On hit, the player loses 2 HP at the start of each of the next 3 rounds, ignoring guard. Attack: X damage, Venom on hit.",
    "Sunder": "Enemy attacks ignore half of the player's guard. Attack: this attack ignores half of the player's guard.",
    "Thief": "Thief X: on hit, the player loses X gold.",
    "Bulk": "Bulk X [columns]: specified columns deal X less damage per square to this enemy (minimum 0).",
    "Fractured": "Fractured X [columns]: specified columns deal X more damage per square to this enemy.",
    "Taunt": "Guard columns (D, E and F) deal 1 damage per square and give no guard.",
    "Plate": "Plate [columns]: only specified columns deal damage to this enemy.",
    "Trapper": "Trapper X: at the start of each player attack, place X traps: roll two dice for the column (re-roll 2 or 12) and one die for the row. A runner reaching a trap rolls a die: 4-6 evades and removes the trap, 1-3 ends the attack as a fumble.",
    "Rally": "Rally X(Y): this enemy arrives with X extra minions and, when shown, Y minibosses, each rolled on a d6.",
    "Lock": "Lock [columns]: specified columns cannot have runners.",
    "Grapple": "Grapple [columns]: wilds (pairs totaling 2 or 12, and surges) cannot move runners in specified columns. With no columns, no wilds are available at all.",
    "Frenzy": "All enemy attacks deal 1.5 times damage, rounded. Frenzy H: only heavy attacks.",
    "Fortify": "Fortify X: player attacks deal X less damage to this enemy.",
    "Regen": "Regen X: this enemy heals X HP each round.",
    "Haste": "Haste X: each round, this enemy also strikes for X.",
    "Berserk": "Berserk X: player fumbles deal X more damage to the player.",
    "Exposed": "Exposed X: this enemy's weak point is X rows lower.",
}
ON_HIT = "An enemy attack hits when the player takes damage from it, meaning guard did not block all of the damage."
# How each boss module prints on the sheet (keyword plus its parameter).
MODULE_LABEL = {"Iron Wall": "Lock D,F", "Shieldwall": "Lock A,I", "Gatehouse": "Lock D,E,F", "Thick Hide": "Bulk 1 A,I",
                "Trapper": "Trapper 2", "Plate": "Plate A,I", "Jinx": "Grapple", "Doom": "Frenzy H", "Fortify": "Fortify 3",
                "Regenerate": "Regen 4", "Haste": "Haste 4", "Berserk": "Berserk 2", "Exposed": "Exposed 2", "Cracked Shell": "Fractured 1 D,E,F"}

# --- Map interactions -----------------------------------------------------------------------------------
# (text, weight). The generator draws 6 + (count - 1) entries per pool; duplicates are allowed except where
# 'unique' is set.
TREASURE = [
    ("Mimic! INT or take {s}, then fight miniboss 1-2", 2, True),
    ("Potion", 3, False),
    ("Purse: gain 4 gold", 3, False),
    ("Coins: gain 2 gold", 2, False),
    ("Needle trap: DEX or take 4", 2, False),
    ("Pocket upgrade: hold 1 more effect", 1, True),
    ("Effect tile (Uncommon) for your grid", 2, False),
    ("Effect tile (Rare) for your grid", 1, True),
    ("Whetstone: Weapon +1", 1, True),
    ("Buckler: Armor +1", 1, True),
    ("Spare runner: 4th runner for one attack", 1, False),
    ("Map scrap: learn one other chest's contents", 1, False),
]
# Quest requests for NPC quest entries. [_,_] = roll a cell (1-12 each); Qn[_,_] = d6 each, counted inside quadrant n.
QUESTS = [
    "Please save my cat from the tree at [_,_]",
    "I need elderberries from [_,_]",
    "My brother went to [_,_] and never came back",
    "Take this letter to the hermit at [_,_]",
    "I dropped my mother's ring near [_,_]",
    "Light the old beacon at [_,_] for me",
    "Fetch clean water from the spring at [_,_]",
    "Scare off the crows nesting at [_,_]",
    "Leave this offering at the shrine at [_,_]",
    "Find my goat; it wandered off to [_,_]",
]
NPCS = [
    ("Imposter! INT or take {s}, then fight 2 minions", 2, True),
    ("Q|", 3, False),                      # filled with a request from QUESTS
    ("Pilgrim: gain 3 gold", 2, False),
    ("Herbalist: gain a potion", 2, False),
    ("Rumor: treasure buried at [_,_] (dig with STR)", 2, False),
    ("Blessing: +1 WIS adjustment", 2, False),
    ("Field medic: heal 5", 2, False),
    ("Lost child: escort to a start; reward by distance", 1, True),
    ("Old soldier: next fight, +1 guard every round", 1, False),
    ("Fortune teller: roll your next encounter now", 1, True),
]
STRANDED = "Villager, d6: 1-2 fight 1 minion, 3-4 fight 2, 5-6 escort them to [_,_]"

# Shop catalog: (name, tier, text). The shopkeeper stocks 6, the wandering trader 3 (no permanents).
SHOP = [
    ("Potion", 1, "Heal 5"),
    ("Extra die", 1, "5 dice for one attack"),
    ("Brace charm", 1, "One-time Brace"),
    ("Effect tile: Uncommon", 1, "Place on your grid"),
    ("Effect tile: Rare", 2, "Place on your grid"),
    ("Extra runner", 2, "4th runner for one attack"),
    ("Weapon +1", 2, "+1 damage every attack"),
    ("Armor +1", 2, "+1 guard every round"),
    ("Pocket upgrade", 2, "Hold 1 more effect"),
    ("Execute scroll", 3, "One-time Execute"),
    ("Effect tile: Legendary", 3, "Place on your grid"),
    ("Permanent effect", 3, "Keep one effect for life"),
]
PERMANENT = {"Permanent effect", "Weapon +1", "Armor +1", "Pocket upgrade"}

# --- Fuses (condition, length) ---------------------------------------------------------------------------
FUSES = [
    ("Danger 4 or more", "short"),
    ("Danger 6 or more", "long"),
    ("Opened 2 chests", "medium"),
    ("Visited all 4 quadrants", "long"),
    ("Talked to 2 NPCs", "medium"),
    ("Bought anything from a shop", "short"),
]

# --- Encounter table (printed as-is; danger is added to non-double rolls) -----------------------------
NOTHING_MAX = 5          # widened from 4: rolls of 3-5 (after danger) are quiet
ENCOUNTERS = [
    ("3-5", "Nothing"),
    ("6", "Hidden treasure: STR to dig"),
    ("7", "Wandering trader"),
    ("8", "Stranded villager"),
    ("9", "1 minion"),
    ("10", "Trap: DEX or take 4"),
    ("11", "2 minions"),
    ("12", "3 minions"),
    ("13", "3 minions, +1 to their attacks"),
    ("14+", "Miniboss and 1 minion"),
]

# --- Difficulty table (from the spec; draft values) ------------------------------------------------------
DIFFICULTY = {
    "Easy":   dict(danger_total=(2, 2), fuses=("long", "medium"), cap=16, loops=0.25, surprise=3),
    "Normal": dict(danger_total=(3, 4), fuses=("short", "medium", "long"), cap=15, loops=0.20, surprise=5),
    "Hard":   dict(danger_total=(5, 6), fuses=("short", "medium"), cap=14, loops=0.15, surprise=7),
}
BANDS = {1: "Low", 2: "Mid", 3: "High"}

# Objective sizing, fit by simulation so each objective is met by about half of winning runs (scen/objfit.py).
OBJECTIVE_FIT = dict(gold=0.95, cells=3.0, minions=0.45, encounters=0.88, dmg_before_boss=1.75, danger_at_boss=0.75,
                     long_chests=8.2, long_minis=9.3, buy=2)

# Map rules (tunable). The simulator, the generator's estimates and the printed rules all read these.
MAP_ROLL_TARGET = 4                         # a map roll succeeds on d6 + stat >= this
QUEST_PAY = ((5, 2), (10, 4), (None, 6))    # (up to this many cells away, gold): 1-5 -> 2, 6-10 -> 4, 11+ -> 6
QUEST_PAY_RANGE = ((5, 1, 3), (10, 3, 5), (None, 5, 7))   # each scenario rolls its own pay per band (up to cells, min, max);
                                                           # each band pays at least as much as the one before
ESCORT_PAY = 3                              # stranded villager escorted to its cell
DIG_GOLD = 2                                # hidden treasure, on a successful STR roll

# Per-scenario variation around the tuned numbers (each scenario rolls its own, from its own seed stream).
JITTER = dict(enemy_hp=0.10, boss_hp=0.08, attack=1, reward=1, boss_reward=2, entry=1, price=1)
TRAP_DAMAGE = 4                             # "Trap: DEX or take N" on the movement table, before variation
