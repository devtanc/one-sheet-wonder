# How to Play

*One Sheet Wonder: scenario rules. Generated from `scen/render_rules.py`; do not edit by hand.*

Explore a generated map, gather gold and treasure, then defeat the boss. You need your **hero sheet**, a **scenario sheet**, **four six-sided dice** and a pencil.

## Setup

1. Pick a start square (**S1** to **S4**) on the map.
2. A **new hero** starts with **6 gold** and **3 potions**. After that, your hero **keeps everything** from scenario to scenario: gold, potions and items. Whether you begin a scenario at **full HP** or with the HP you ended on is up to you. Drink a potion **any time**, in or out of a fight: it heals 5.
3. You have **3 + WIS adjustments** for this scenario (see Map rolls). Tick them off as you use them.

## Exploring

Move one cell at a time, up, down, left or right. Walls and solid blocks stop you. The first 3 cells are free; after that, every 3rd cell you enter, make a **movement roll**: roll 2 dice and add the danger pips of the quadrant you’re in, then read the **Movement roll** table on the scenario sheet.

**Doubles** on the dice themselves (before adding pips) bring a **miniboss** instead: roll a die to pick which. Once the fuse is lit, a **1-1 or 6-6** brings the **boss**.

## Danger, the fuse and the boss

Add **1 danger** for each interaction: an encounter from a movement roll, opening a chest, meeting an NPC or finishing a quest. Encounters in a **2-pip quadrant** add **2**. Visiting the shopkeeper is free.

The **fuse** is lit once your danger reaches the first **red box** on the track, or, on maps with no red boxes, once you meet the fuse condition printed beside the track. After that, a 1-1 or 6-6 movement roll brings the boss. If the **last box** fills, the boss comes on your next movement roll anyway.

The boss card shows its phases and keywords. **Rally** brings henchmen into the boss fight with it.

## Places

**Chests.** Open one (+1 danger) and roll a die on the **Treasure** list. If that entry is already crossed off, take the lowest unused entry numbered 7 or higher; if there is none, roll again. Cross off what you take.

**NPCs.** Meet one (+1 danger) and roll on the **NPCs** list the same way. Entries marked **Q** are quests: roll the cell **`[_,_]`**, write it in, and go there. When you arrive, collect the gold the sheet’s quest line gives for how far away the cell was (+1 danger).

**Shopkeeper.** Visiting is free. Each item can be bought once, at the prices this scenario shows for **$**, **$$** and **$$$**. **Effect tiles** go on a square of your attack grid and give that effect whenever you reach it.

**Movement roll results.** A **wandering trader** sells the items listed on the sheet. A **stranded villager** needs help: roll a die (1-2 fight 1 minion, 3-4 fight 2, 5-6 escort them to a rolled cell for **3 gold**). **Hidden treasure**: make a STR roll to dig up **2 gold**. A **trap**: make a DEX roll or take the damage shown.

## Map rolls and cells

A **map roll** is one die plus the stat named (STR, DEX, INT or WIS from your hero sheet): **4 or more** succeeds. An **adjustment** changes one die of any map roll, including a movement roll, by 1 up or down.

**`[_,_]`** means roll a cell: one die per number, adding 6 if a second die shows 4-6, for a column and row from 1 to 12. **Q3`[_,_]`**: one die per number, counted inside quadrant 3.

## Ending the scenario

Defeat the boss to **win**. Then check your five **objectives**: win and complete **3 of 5** to **level up** (fill the next level box on your hero sheet). If your HP drops to 0, you lose the scenario; whether your hero tries again or retires is up to you.

**Leveling up.** At levels **3** and **5** choose your path on the hero sheet (one class at each step); each level adds the abilities its tag shows. Grid rows **10-11** unlock at level 3 and **12-13** at level 5.

## Fights

Minions: roll a die per minion on the minion cards. Minibosses: roll a die and use the card whose range it falls in. Each enemy drops the **gold** on its card when defeated. Your HP carries over between fights.

A fight is a series of rounds: you attack on your grid, then every enemy still standing attacks you. It ends when every enemy is at 0 HP (you win) or you are (you lose). Each enemy card lists its HP, its **weak point** (two squares on your grid), and its attacks, made **in order**: after the last, it starts again. **H** marks a heavy attack; a **wind-up** deals no damage. Before you attack, note each enemy’s next attack.

## Each round

1. **Potions.** Drink any you like (heal 5 each). You can also drink them between fights.
2. **Choose a target.** While an enemy with **Bodyguard** lives, you must target it.
3. **Attack** on your attack grid (below). Your total damage goes to your target; extra damage is lost. Bonus effects resolve as they say.
4. **Fumble counter.** If your attack fumbled, take 3 damage. Guard doesn’t block it.
5. **Poison and Venom** deal their damage: on enemies first, then on you.
6. **Enemy turn.** Each living enemy makes its next attack, one at a time. This round’s guard absorbs damage first, attack by attack; the rest comes off your HP.
7. **After the enemy turn,** class abilities like Riposte resolve. Then clear your grid: guard doesn’t carry over unless an ability says so.

## Your attack

Roll four dice and split them into two pairs; each pair’s total names a column. Move a runner up one square in each named column, placing a new runner if you have fewer than **3** on the grid. You must move as much as the roll allows, but you choose the pairs. A pair totaling **2 or 12 is wild**: move one square in any column. A column is full at the top of your grid: row **9** at levels 1-2, **11** at levels 3-4 and **13** at levels 5-6.

**You can’t stop early.** Keep rolling until you **bust** (no pairing moves anything) or **fumble**. Then every filled square counts.

**Danger line.** Once any runner is on row 4 or higher (row 5 from level 6), check each roll before moving: **three or four of a kind** is a fumble. The attack ends, your squares still count, and you take the 3-damage fumble counter.

**Damage and guard.** Each filled square deals its column’s damage (shown above the grid). Middle columns deal no damage but give **2 guard** per square; a **+1** square deals 1 extra damage and gives no guard.

**Surge.** The first time a column reaches its lightning square in an attack, take one free step in any column.

**Weak points.** The first time one of the enemy’s weak squares is reached, take **2 free steps** and that column’s damage is **doubled**. Reach **both** and your whole attack is doubled instead.

**Bonus squares.** The first time a column reaches a colored square, use one of your effects of that rarity. **Once** effects can be used once per attack. Your **top column** is your highest-damage column this attack.

**Pocket.** Instead of using an effect right away, you may write its rarity in your **pocket** (one at a time). On any later turn, erase it and use one of your effects of that rarity. A pocketed effect keeps until you use it.

## Keywords

Purple tags change the rules. On an enemy, they apply while it lives; on an attack, if it hits (deals damage after guard); in a boss phase, for that phase. **X** is the number after the keyword; on an attack, its damage. Columns in brackets are letters on your grid.

- **Bodyguard** You must target this enemy before other enemies.
- **Daze** Past the danger line, two pairs also fumble. Attack: on hit, you are Dazed during your next attack.
- **Pin** You have 1 fewer runner. Attack: on hit, your next attack is Pinned.
- **Venom** On hit, you lose 2 HP at the start of each of the next 3 rounds, ignoring guard. Attack: X damage, Venom on hit.
- **Sunder** Enemy attacks ignore half of your guard. Attack: this attack ignores half of your guard.
- **Thief X** On hit, you lose X gold.
- **Bulk X [columns]** Specified columns deal X less damage per square to this enemy (minimum 0).
- **Fractured X [columns]** Specified columns deal X more damage per square to this enemy.
- **Taunt** Guard columns (D, E and F) deal 1 damage per square and give no guard.
- **Plate [columns]** Only specified columns deal damage to this enemy.
- **Trapper X** At the start of each of your attacks, place X traps: roll two dice for the column (re-roll 2 or 12) and one die for the row. A runner reaching a trap rolls a die: 4-6 evades and removes the trap, 1-3 ends the attack as a fumble.
- **Rally X(Y)** This enemy arrives with X extra minions and, when shown, Y minibosses, each rolled on a d6.
- **Lock [columns]** Specified columns cannot have runners.
- **Grapple [columns]** Wilds (pairs totaling 2 or 12, and surges) cannot move runners in specified columns. With no columns, no wilds are available at all.
- **Frenzy** All enemy attacks deal 1.5 times damage, rounded. Frenzy H: only heavy attacks.
- **Fortify X** Your attacks deal X less damage to this enemy.
- **Regen X** This enemy heals X HP each round.
- **Haste X** Each round, this enemy also strikes for X.
- **Berserk X** Your fumbles deal X more damage to you.
- **Exposed X** This enemy’s weak point is X rows lower.
