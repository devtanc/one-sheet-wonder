# Documentation

| Document | What it covers | Source |
| --- | --- | --- |
| [design.md](design.md) | How the game fits together, how scenarios are generated and balanced, the simulator, leveling and power ratings, the decision log and open items | Written by hand |
| [rules.md](rules.md) | The player rules, word for word as printed on the rules sheet | Generated |
| [hero-warrior.md](hero-warrior.md) | The Warrior line: classes, stats, every ability with its exact numbers, the 13-row grid, all effects, pockets | Generated |
| [content-reference.md](content-reference.md) | Everything the scenario generator draws on: enemies, bosses and their phases, keywords, treasure, NPCs, quests, shop, fuses, the movement table, difficulty, objective sizing, map rules, number variation | Generated |

The generated documents come from the code (`scen/pools.py`, `scen/steps.py`, `scen/render_rules.py`, `scen/render_hero.py`,
`engine2.py`), so they always match the game. After changing any of those, run:

    python3 scen/render_docs.py

`python3 tests/smoke_test.py` fails if they are out of date.

The original design record, the **One Sheet Wonder — Scenario Sheet Spec** document, holds the full history of the early
simulation rounds; `design.md` summarizes what came of them.
