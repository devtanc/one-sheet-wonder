# One Sheet Wonder: design

How the game fits together, how it is generated and balanced, and why it is the way it is. The exact rules and numbers
live in the generated references next to this file ([rules](rules.md), [hero](hero-warrior.md),
[content](content-reference.md)); this document explains them and records the decisions behind them.

## The game in brief

A scenario is one printed page: a 12 x 12 maze map with four quadrants, a danger track, enemy cards, treasure and NPC
lists, a shop and five objectives. The player explores one cell at a time; every third cell brings a movement roll that may
start a fight or an event. Interactions fill the danger track; once the scenario's fuse is lit, a 1-1 or 6-6 movement roll
brings the boss, and when the track fills the boss comes anyway. Beating the boss wins the scenario, and winning with 3 of the
5 objectives done levels the hero up.

Fights use the hero sheet's **attack grid**, a push-your-luck dice board in the spirit of Can't Stop: roll four dice, pair
them, climb columns, and keep rolling until you bust or fumble. Outer columns deal damage, middle columns give guard, and
colored squares trigger the hero's effects.

The hero sheet is one page for the hero's whole career (levels 1-6). Inventory (gold, potions, items) carries over between
scenarios; whether HP does is the player's choice.

## Scenario codes

A scenario is fully determined by its code, `VVDD-XXXX-XXXX-C`:

| Part | Meaning |
| --- | --- |
| `VV` | Generator version (`01`). A code always reprints with the version it was made with. |
| `DD` | Band and difficulty, `01`-`09`: (band - 1) x 3 + difficulty, with bands Low / Mid / High and difficulties Easy / Normal / Hard (`05` is Mid Normal). |
| `XXXX-XXXX` | The 8-hex-digit seed. |
| `C` | Check character over the first 12 characters. |

All randomness comes from a mulberry32 generator seeded from the code. Content added after the first release (boss
henchmen, quest requests, quest pay tables, number variation, hero Mythic effects, the effect cap) draws from its own stream
off the same seed, so adding it never reshuffles anything an existing code already generated.

## How a scenario is generated

`scen/generate.py`, in order (later steps read earlier ones):

1. **Parse the code** and pick the difficulty table.
2. **Quadrant danger:** the tier's total (Easy 2, Normal 3-4, Hard 5-6) is spread over the four quadrants, at most 2 each.
3. **Blocks:** each quadrant gets 0 (37.5%), 1 (37.5%) or 2 (25%) blocks, 2 x 2 (75%) or 3 x 3, open rooms (60%) or solid (40%), never overlapping.
4. **Reachability:** solid blocks are removed, last first, until every passable cell connects.
5. **Maze:** open rooms become single nodes; a recursive-backtracker spanning tree is carved, then a share of the remaining walls (the tier's loop percentage) is knocked out to add loops.
6. **Starts:** one start cell per quadrant, outside blocks.
7. **Places:** the shopkeeper, 1-2 chests and 1-4 NPCs, weighted by quadrant danger (chests toward danger 2, the shop toward 1-2, NPCs toward 0-1).
8. **Fuse and track length** from the tier's fuse pool (fuses that need 2 chests or 2 NPCs only on maps that have them).
9. **Enemies:** 6 minions and 3 minibosses from the pools, a boss, its henchmen, weak point and phase modules.
10. **Pools:** treasure and NPC entries, quest requests, the quest pay table, shop and trader stock; then number variation.
11. **Run estimate:** expected movement rolls and gold, fuse-aware (once the fuse is lit, each roll can bring the boss; players steer dice with adjustments, fit by simulation as a doubled boss chance).
12. **Objectives,** sized from that estimate.

## Danger, the fuse and pacing

Danger only rises through interactions: +1 per encounter (+2 in a 2-pip quadrant), chest, NPC or finished quest; walking
and visiting the shopkeeper are free. The fuse is the pacing device. It is printed, so the player knows what lights it but
not when the boss will roll. The hard cap (track length 16 / 15 / 14 by tier) bounds every scenario.

Rounds of simulation shaped this: with the first draft (track 8-10), almost every run ended at the cap and chests, NPCs and
the shop went unused. The track was lengthened (to 16 / 15 / 14), the quiet range of the movement table widened (3-5 is
Nothing), and the shopkeeper made free to visit. Roughly a third of bosses now arrive through the fuse rather than the cap.

## Objectives

Each objective is sized so that about half of winning runs meet it, measured only where it was offered (the bot pursues its
objectives, so a median over all runs understates them). With five objectives and "win and complete 3", about 54% of wins
level the hero up. Every scenario gets one restraint objective (take little damage, or reach the boss early) and one push
objective (chests, minibosses, encounters, NPCs), so the player has to choose a plan. "Travel 7 cells without an encounter"
was dropped because movement rolls come every third cell, so it could only ever be met 0% or 100% of the time.
Re-check after any rules change with `scen/objfit.py` and `scen/objreport.py`.

## Difficulty

Targets (average player win rates): **Easy 80%, Normal 55%, Hard 30%.** A code's band and tier are fixed, but the map itself
is identical at every difficulty; only its numbers change.

1. **Rating.** The first time a seed is generated, 300 simulated games with a level-1 reference hero rate the map (its raw win rate).
2. **Steps.** `scen/steps.py` converts the gap between rating and target into log-odds and buys whole, visible steps of enemy damage (each ±1 damage step is worth about 0.53 log-odds; up to ±3 steps).
3. **Fine-tune.** The remainder becomes an enemy-HP scale (within x0.75-1.33), then `scen/difficulty.py` fine-tunes it by simulation so the printed map lands on its tier's target.

Potions are deliberately not a lever: the hero's inventory carries over, so a scenario can't set it. Balance is calibrated
against a new hero's kit (6 gold, 3 potions, full HP). Mid and High maps currently use the Low rating, until reference
heroes for levels 3 and 5 are calibrated.

**Number variation** (`pools.JITTER`) makes every scenario's numbers differ slightly from the tuned values. Over 400 maps with
and without it, win rate moved +0.8% (within noise) and level-ups 55% to 54%, so it adds texture without changing balance.

## The simulator

- **Rust attack simulator** (`cs5rs/`): plays one attack on the grid exhaustively for a board configuration (grid height, danger line, keywords, class options) and writes outcome distributions. `regen_all.py` builds the 468 base files (about 1.9 GB) into `d4/`; hero and keyword variants are built on demand and fingerprinted with the simulator's source, so stale data is never reused.
- **Fight engine** (`engine2.py`): plays fights round by round from those distributions: targeting, guard, enemy attack patterns, keywords, class abilities, effects and potions.
- **Scenario bot** (`scen/playsim2.py`): explores a generated map with a reasonable player policy (routing for objectives, using adjustments to dodge or invite the boss, avoiding dangerous quadrants at low HP, shopping), and fights with the engine.
- **Runner** (`scen/parallel.py`): spreads games over every core; each game carries its own seed, so results are identical at any core count.

Win-rate measurements need many maps: 200+ maps per data point, because map-to-map variation alone is about ±15-20%.

## Leveling and the Warrior line

Level-ups add mechanics rather than just numbers. The path is Warrior (levels 1-2), then Knight or Barbarian (3-4), then
one of two final classes (5-6): Paladin or Cavalier after the Knight, Berserker or Beastkin after the Barbarian. Each path
step adds one class-flavored ability and ranks it up at the next level, keeping tracking light. Level 2 adds Heavy Blows II,
level 4 the once-per-fight reserve runner, and level 6 moves the danger line from row 4 to row 5.

The grid starts at 9 rows and unlocks two rows at each class upgrade (11 rows at level 3, 13 at level 5). The new rows hold
a higher concentration of effect tiles (42% of squares, against 21% in rows 1-9), including the **Mythic** rarity, so taller
grids are both a reward and a reason to push. At levels 5-6 any column reaches row 10 in about 30% of attacks and row 13 in
about 14%.

**Power ratings.** A hero's rating is the enemy-HP multiplier at which it wins 55% of scenarios (200 maps per point).

| Level | Knight path | Barbarian path |
| --- | --- | --- |
| 1 | Warrior x0.96 | |
| 2 | Warrior with Heavy Blows II x1.03 | |
| 3 | Knight x1.46 | Barbarian x1.53 |
| 4 | Knight x1.73 | Barbarian x1.95 |
| 5 | Paladin x3.57 / Cavalier x4.04 | Berserker x3.80 / Beastkin x3.89 |
| 6 | Paladin x6.35 / Cavalier x6.65 | Berserker x6.07 / Beastkin x6.47 |

**Mythic effects** (rated on a level-5 Cavalier without its final ability, which wins 55% at x2.27 enemy HP): Godslayer +7%,
Meteor +9%, Time Stop +10%, Overdrive +10%, Echo +24%, Phoenix +26%. Time Stop and Echo were flagged as slightly weak even
after buffs (within noise).

## The hero sheet

Constraints: **single-sided**, US Letter landscape, **5 mm margins** (the printer minimum is 4.2 mm), and attack-grid squares
of **12.2 mm** so a die fits on each. The design is made on the canvas first (`design/hero-sheet-warrior.dc.html`) and
`scen/render_hero.py` is then matched to it measurement for measurement.

Effects are capped so every sheet fits: a d6 per rarity (1 one effect, 2-5 two, 6 three) with only one rarity allowed three,
so heroes have 5-11 effects. 73% of heroes print their effects at the full 12 px; the rest step down to 11.5 px.

## Decision log

| Date | Decision |
| --- | --- |
| Oct 27 | Scenario sheet format, map generation and the first simulator rounds (track lengths, movement table, free shop, starting gold). |
| Oct 28 | Map rolls d6 + stat, 4 or more. Quest pay by distance, rolled per scenario (1-3 / 3-5 / 5-7 gold). Escort 3 gold, dig 2. Potions any time. Shop items bought once; effect tiles trigger whenever reached. Losing is the player's call. |
| Oct 28 | Number variation around tuned values. Objectives refit to about 50% of winning runs; "reach the boss before the track fills" replaced by "reach the boss at danger X or less". |
| Oct 29 | 13-row grid with level unlocks, the Mythic rarity, and the full Warrior class tree (abilities and ratings above). |
| Oct 29 | Inventory carries over between scenarios; HP carry-over is the player's choice. Potions removed as a difficulty lever. |
| Oct 29 | One rarity at most may have three effects. New rule: the **Pocket** (store a triggered effect's rarity, use it on a later turn). |
| Oct 29 | Hero sheet redesigned for the 13-row grid on one side: 12 mm squares, level bars, danger tabs, pockets, tracker. |

## Open items

- **Pocket balance:** the simulator doesn't model the Pocket yet; banking a strong effect for the boss will raise win rates, so it needs measuring and the difficulty recalibrating.
- **Mid and High scenarios:** calibrate against level-3 and level-5 reference heroes, and scale enemies by band (currently every band plays the Normal numbers).
- **Other classes:** Rogue, Mage and Cleric are unplanned beyond their map stats (DEX, INT, WIS).
- **Keywords not yet generated:** Grapple and Taunt are defined but no enemy uses them yet. Warlord and miniboss per-boss HP offsets are still to do.
- **Effects:** Time Stop and Echo may want a small buff. Pack (x6.47 at level 6) is the strongest level-6 class, accepted as intentional for now.
- **Pocket upgrades and permanent shop items** are on the sheet and in the pools but not simulated.
