# One Sheet Wonder

A solo tabletop RPG played on two printed pages: a **scenario sheet** (a seeded maze map, enemies, treasure, NPCs, a shop and
five objectives) and a **hero sheet** (a 13-row attack grid you climb with dice, plus abilities, effects and a class path).
This repository holds everything that makes and balances those sheets:

- **Generators** that turn a code like `0105-a6a3-a450-7` into a print-ready PDF, always the same sheet for the same code.
- **A simulator** that plays thousands of scenarios with a bot hero (a Rust attack simulator plus a Python fight and
  exploration engine) to rate maps, set difficulty and tune objectives and class abilities.
- **A small web app** for generating sheets from a browser or phone.

| Path | What it is |
| --- | --- |
| `scen/generate.py`, `scen/pools.py` | Scenario generator and all of its content pools and tunable rules |
| `scen/render_pdf.py` | Scenario sheet PDF |
| `scen/render_hero.py` | Hero sheet PDF (matches `design/hero-sheet-warrior.dc.html`) |
| `scen/render_rules.py` | Two-page player rules PDF |
| `scen/playsim2.py`, `scen/parallel.py` | Scenario simulator (bot hero) and the multi-core runner |
| `scen/steps.py`, `scen/difficulty.py` | Difficulty steps and the per-map enemy-HP fine-tune |
| `engine2.py`, `kwboard.py` | Fight engine and keyword-board data builder |
| `cs5rs/` | Rust attack simulator (builds the attack data in `d4/`) |
| `cs5.cpp`, `regen_all.sh` | Original C++ simulator and bash data builder, kept for reference and analysis modes |
| `server.py`, `web/` | Web generator |
| `design/` | Canvas source of the hero sheet design |
| `docs/` | Design and rules documentation: `design.md` (by hand) and generated references for the rules, the hero and all scenario content |
| `scen/render_docs.py` | Regenerates the reference docs from the code (`--check` verifies them) |
| `tests/smoke_test.py` | Quick check that the sheet renderers work |

## One-time setup (macOS)

1. **Rust** (for the attack simulator):
   `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh` (or `brew install rust`)
2. **Build the simulator:** `cd cs5rs && cargo build --release && cd ..`
3. **Python 3.10+ and its packages:** `pip3 install -r requirements.txt` (NumPy, ReportLab, pypdfium2, Pillow)
   pypdfium2 and Pillow make the sheet previews on the web page. Phones can't show PDFs inside a page, so without it the page falls back to a PDF frame on desktop and an "open the PDF" link on phones.
4. **Build the attack data** (468 files, about 1.9 GB, a minute or two on all cores):
   `python3 regen_all.py`
5. **Check it works:** `python3 tests/smoke_test.py` (renders a hero, the rules and a scenario sheet; no attack data needed), then
   `python3 scen/parallel.py 0105-a6a3-a450-7 400`, which plays 400 games serially, then in parallel, and confirms the results are identical.

Steps 1, 2 and 4 are only needed for simulation and for rating maps; printing sheets needs only Python and its packages.

Run every command from this folder.

## Web generator

    python3 server.py              # then open http://localhost:8000

Enter a seed (optional), choose a hero level and a difficulty, then **Generate map** or **Generate hero**. The page shows the printable sheet with buttons to download it or open it to print.

| Input | What it does |
| --- | --- |
| Seed left empty | A random seed is rolled. |
| 8 characters (`1a2b-3c4d`) | That seed, printed with this generator's version. |
| A full code (`0105-1a2b-3c4d-a`) | Reprints it. Its version is kept, and the level and difficulty switch to the code's own; change them to print the same seed at another tier. |
| Hero level (default Low) | Maps: the hero band. Heroes: start at level 1, 3 or 5, with the path taken chosen by the seed. |
| Difficulty (default Normal) | Maps only. The map is the same at every difficulty; only its numbers change (enemy damage and enemy HP). |

How maps are balanced: the first time a seed's map is generated, the server plays 300 simulated games with a level-1 reference hero to rate it, then picks the visible difficulty steps for the chosen tier (see `scen/steps.py`). That takes a few seconds on all cores and is cached, so other tiers of the same seed are instant. Mid and High maps currently use the Low rating, until heroes for those levels are designed.

Every hero is a Warrior for now, the only class whose sheet is designed. Its path at levels 3 and 5 and its effects come from the seed (a d6 per rarity: 1 gives one effect, 2-5 two, 6 three, but only one rarity may keep three).

The page works on phones: the preview is an image (tap it to open the PDF), and the layout stacks into one column on small screens. To use it from your phone, start the server with `--host 0.0.0.0` and open `http://<your Mac's IP>:8000` on the same Wi-Fi.

Sheets and ratings are cached in `cache/`; delete it to start fresh. Options: `--port 8080`, `--host 0.0.0.0` (to reach it from other devices on your network), `--workers 6` (simulation processes; default all cores).

## Rules and documentation

The full documentation is in [`docs/`](docs/README.md). `python3 scen/render_rules.py` prints the two-page player rules (how to play a scenario, fights, and the keyword glossary). The glossary comes from `pools.KEYWORDS`, the same definitions the generator uses. The web page links to the rules too.

## Map rules you can tune

`scen/pools.py` holds the map-roll target (`MAP_ROLL_TARGET`, d6 + stat), quest pay by distance (`QUEST_PAY_RANGE`: each scenario rolls its own table within these ranges and prints it under the NPC list; `QUEST_PAY` is the fallback), the villager escort reward (`ESCORT_PAY`) and the dig reward (`DIG_GOLD`). The simulator, the generator's gold estimates and the printed rules all read them, so changing a value changes balance and wording together. The server notices the change and builds fresh sheets.

## Leveled heroes (Warrior line)

The simulator plays heroes of any level and path: `play(code, seed, level=1-6, path="Knight"|"Barbarian"|"Paladin"|"Cavalier"|"Berserker"|"Beastkin")`.
Each level's grid height (9 / 11 / 13 rows), Heavy Blows II, the danger line and the path abilities come from `hero_config` in `scen/playsim2.py`; the rules for each ability live in `engine2.py` (fight effects) and the Rust simulator (`cs5rs`, attack mechanics, enabled by name=value options). `scen/finalstudy.py` measures each hero's power rating: the enemy-HP multiplier at which it wins 55%.

Hero attack data is built on demand into `d4/` and tagged with a fingerprint of the simulator source, so changing the simulator never reuses stale data. It grows with use (several GB after large studies); delete hero datasets (`d4/kw*` whose spec has `"HERO"`) whenever you like, and they rebuild as needed.

## Number variation

Each scenario varies its numbers slightly around the tuned values, from its own seed stream: enemy HP, attacks and gold, the boss's HP, attacks and gold, treasure and NPC amounts, surprise and trap damage, and shop prices. The amounts are `JITTER` in `scen/pools.py` (set any of them to 0 to turn that one off). Every number averages its tuned value, and each map's difficulty kit is computed from what it actually prints.

## Objectives

Each objective is sized to be met by about half of winning runs, so "win and complete 3 of 5" levels a hero up about half the time. The sizing constants are `pools.OBJECTIVE_FIT`. To re-check after a rules change: `python3 scen/objfit.py 500 <seed> check.json` then `python3 scen/objreport.py check.json`.

## Printing scenario sheets

`scen/render_pdf.py` turns codes straight into print-ready PDFs (US Letter, landscape, fonts embedded):

| Task | Command |
| --- | --- |
| One sheet | `python3 scen/render_pdf.py 0105-a6a3-a450-7` (writes `sheets/0105-a6a3-a450-7.pdf`) |
| Several sheets in one PDF | `python3 scen/render_pdf.py CODE1 CODE2 CODE3 -o campaign.pdf` |
| Longer or shorter danger track | `--cap 20` |
| Difficulty kit | `--dmg-add 1 --hp-scale 1.1` (see `scen/steps.py`) |

Everything on the page comes from the generator, so the same code always prints the same sheet. Print at 100% ("Actual size"), not "Fit to page", so the map's cells stay 9 mm.

Fonts: Bungee and Barlow Condensed (SIL Open Font License, in `fonts/`).

## Printing hero sheets

`python3 scen/render_hero.py 0102-1a2b-3c4d-0` writes `sheets/hero-0102-1a2b-3c4d-0.pdf`. The code's band sets the starting
level (low 1, mid 3, high 5); the seed decides the path and the effects. The sheet lasts the hero's whole career: level boxes,
path choices, gold, potions, pockets and the tracker are all filled in by hand as the hero plays.

The layout reproduces the canvas design in `design/hero-sheet-warrior.dc.html` measurement for measurement (CSS pixels, 5 mm
margins, text placed with each font's own line metrics). When the design changes, update the canvas first, then
`render_hero.py` to match. Grid squares are 12.2 mm so a die fits; print at 100% ("Actual size").

Heroes draw 5-11 effects. The Effects text is 12 px when it fits and steps down to 11.5 px or less only when a hero's list
would reach the path tree, so every sheet fits.

## Everyday use

| Task | Command |
| --- | --- |
| Rate scenarios across enemy HP levels | `python3 scen/calibrate.py 0105-xxxx-xxxx-x ...` |
| Difficulty steps for each tier | `python3 scen/stepcal.py` |
| Many games from your own script | `from parallel import play_many, run_games` (see `scen/parallel.py`) |

## How parallelism works

- **Games are independent and carry their own seeds,** so results are identical whatever the core count.
- **Workers start fresh** (the macOS "spawn" method). Anything a script changes in memory (a pools setting, for example) must be passed through `overrides=`, such as `{"DIFFICULTY.Normal.cap": 20}`.
- **Scripts that use the runner need `if __name__ == "__main__":` around their main code;** otherwise every worker re-runs the whole script.
- **Keyword boards are built on demand.** The first time a new combination of keywords (Lock, Grapple, Bulk and so on) is needed, one worker builds its data while the others wait, then everyone reuses it.

Environment settings:

| Variable | Effect |
| --- | --- |
| `OSW_WORKERS` | Worker count (1 = serial). Default: all cores. |
| `OSW_CS5` | Path to a simulator binary to use instead of the Rust build. |
| `OSW_ENGINE_DIR` | Folder that holds `engine2.py`, if the scripts live elsewhere. |

## Rust vs C++ simulator

`cs5rs/` is a port of `cs5.cpp` that produces **byte-identical** data to the C++ built with GCC on Linux, the build that made the original data. It is about 1.8x faster per file.

Use the Rust build on macOS. A C++ build there uses clang's standard library, which turns random numbers into dice differently, so it would produce statistically equivalent but *not identical* data. The Rust version spells out the exact algorithms, so it matches on every platform.

Only the data-dump mode is ported. `cs5.cpp`'s analysis printouts (modes 0/1/2/8/9) remain C++-only.

`regen_all.sh` is the original bash data builder, kept for reference. It needs bash 4, which macOS doesn't ship; use `regen_all.py` instead.
