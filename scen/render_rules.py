#!/usr/bin/env python3
"""Print the player rules: playing a scenario, fights and the attack, and the keyword glossary (US Letter, portrait).

    python3 scen/render_rules.py                 # -> sheets/one-sheet-wonder-rules.pdf

The glossary is generated from pools.KEYWORDS, the same definitions the generator and engine use.
Combat wording follows the player rules document (Attack Board RPG: Rules).
"""
import os, sys, re, argparse
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import osw_paths  # noqa: F401
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.pagesizes import letter
import render_pdf as R
from render_pdf import tw, asc, wrap_rich, INK, INK2, MUTED, RED, VIO, VIO_B
import pools

W_PX, H_PX = 816, 1056                     # portrait Letter in design px

class PortraitPage(R.Page):
    def _y(self, y): return (H_PX - y) * R.PX

def typo(s): return s.replace("'", "\u2019")

def segs(text, size=12.5, color=INK):
    """**bold** markup -> rich segments."""
    out = []
    for i, part in enumerate(re.split(r"\*\*", typo(text))):
        if part: out.append((part, "Barlow-B" if i % 2 else "Barlow", size, color))
    return out

def you(text):
    """Glossary entries are written about 'the player'; the rules speak to the reader."""
    for a, b in (("the player is", "you are"), ("The player has", "You have"), ("The player must", "You must"),
                 ("the player loses", "you lose"), ("the player's", "your"), ("each player attack", "each of your attacks"),
                 ("player attacks", "your attacks"), ("Player attacks", "Your attacks"), ("player fumbles", "your fumbles"),
                 ("to the player", "to you"), ("the player", "you")):
        text = text.replace(a, b)
    assert "player" not in text.lower(), text
    return text

class Flow:
    """Two-column text flow that starts new columns and pages as it fills."""
    def __init__(self, c, top=88, bottom=1010, margin=54, gap=30):
        self.c = c; self.pg = PortraitPage(c); self.top, self.bottom = top, bottom
        cw = (W_PX - 2 * margin - gap) / 2; self.cols = [(margin, cw), (margin + cw + gap, cw)]; self.ci = 0; self.y = top
    @property
    def x(self): return self.cols[self.ci][0]
    @property
    def w(self): return self.cols[self.ci][1]
    def need(self, h):
        if self.y + h > self.bottom: self.next_col()
    def next_col(self):
        if self.ci == 0: self.ci = 1
        else: self.new_page()
        self.y = self.top
    def new_page(self):
        self.c.showPage(); self.pg = PortraitPage(self.c); self.ci = 0; self.y = self.top
        page_title(self.pg, "HOW TO PLAY", "continued")
    def heading(self, text):
        self.need(26 + 34); self.y += 6
        self.pg.text(self.x, self.y + 15, text.upper(), "Bungee", 15, INK); self.pg.line(self.x, self.y + 21, self.x + self.w, self.y + 21, INK, 1.5)
        self.y += 28
    def para(self, text, size=13.5, color=INK, indent=0, after=6, lead=1.25):
        lines = wrap_rich(segs(text, size, color), self.w - indent)
        for ln in lines:
            self.need(size * lead)
            cx = self.x + indent
            for p, f, s, col in ln: cx += self.pg.text(cx, self.y + asc(s), p, f, s, col)
            self.y += size * lead
        self.y += after
    def item(self, mark, text, size=13.5):
        h = len(wrap_rich(segs(text, size), self.w - 18)) * size * 1.25
        self.need(min(h, 3 * size * 1.25))
        self.pg.text(self.x, self.y + asc(size), mark, "Barlow-B", size, INK)
        self.para(text, size, indent=18, after=3)
    def keyword(self, name, text):
        """Tag at the start of the line (with its X and [columns] form), definition running on beside it."""
        size, lead = 13.5, 20
        label, body = name, text
        if text.startswith(name + " ") and ":" in text:
            label, body = text.split(":", 1); body = body.strip()
        body = you(body); body = body[0].upper() + body[1:]; cw = tw(label, "Barlow-B", 12, 0.3) + 10 + 6
        first = wrap_rich(segs(body, size), self.w - cw); lines = [first[0]]
        rest = " ".join("".join(p for p, *_ in ln).strip() for ln in first[1:]).strip()
        if rest: lines += wrap_rich(segs(rest, size), self.w)
        self.need(len(lines) * lead + 4)
        R.chip(self.pg, self.x, self.y, label)
        for k, ln in enumerate(lines):
            cx = self.x + (cw if k == 0 else 0)
            for p, f, s_, col in ln: cx += self.pg.text(cx, self.y + 13.8, p, f, s_, col)
            self.y += lead
        self.y += 4

def page_title(pg, text, sub=None):
    pg.text(54, 54, text, "Bungee", 26, RED)
    if sub: pg.text(W_PX - 54, 52, sub, "Barlow-SB", 13, INK2, anchor="r")

def content(f):
    """The rules, written once for both the printed sheet and the Markdown copy (docs/rules.md)."""
    T = pools.MAP_ROLL_TARGET


    f.para("Explore a generated map, gather gold and treasure, then defeat the boss. You need your **hero sheet**, a **scenario sheet**, "
           "**four six-sided dice** and a pencil.", 13)

    f.heading("Setup")
    f.item("1", "Pick a start square (**S1** to **S4**) on the map.")
    f.item("2", "A **new hero** starts with **6 gold** and **3 potions**. After that, your hero **keeps everything** from scenario to "
                "scenario: gold, potions and items. Whether you begin a scenario at **full HP** or with the HP you ended on is up to you. "
                "Drink a potion **any time**, in or out of a fight: it heals 5.")
    f.item("3", "You have **3 + WIS adjustments** for this scenario (see Map rolls). Tick them off as you use them.")

    f.heading("Exploring")
    f.para("Move one cell at a time, up, down, left or right. Walls and solid blocks stop you. The first 3 cells are free; "
           "after that, every 3rd cell you enter, make a **movement roll**: roll 2 dice and add the danger pips of the quadrant "
           "you're in, then read the **Movement roll** table on the scenario sheet.")
    f.para("**Doubles** on the dice themselves (before adding pips) bring a **miniboss** instead: roll a die to pick which. "
           "Once the fuse is lit, a **1-1 or 6-6** brings the **boss**.")

    f.heading("Danger, the fuse and the boss")
    f.para("Add **1 danger** for each interaction: an encounter from a movement roll, opening a chest, meeting an NPC or "
           "finishing a quest. Encounters in a **2-pip quadrant** add **2**. Visiting the shopkeeper is free.")
    f.para("The **fuse** is lit once your danger reaches the first **red box** on the track, or, on maps with no red boxes, "
           "once you meet the fuse condition printed beside the track. After that, a 1-1 or 6-6 movement roll brings the boss. "
           "If the **last box** fills, the boss comes on your next movement roll anyway.")
    f.para("The boss card shows its phases and keywords. **Rally** brings henchmen into the boss fight with it.")

    f.heading("Places")
    f.para("**Chests.** Open one (+1 danger) and roll a die on the **Treasure** list. If that entry is already crossed off, "
           "take the lowest unused entry numbered 7 or higher; if there is none, roll again. Cross off what you take.")
    f.para("**NPCs.** Meet one (+1 danger) and roll on the **NPCs** list the same way. Entries marked **Q** are quests: roll the "
           "cell **[_,_]**, write it in, and go there. When you arrive, collect the gold the sheet's quest line gives for "
           "how far away the cell was (+1 danger).")
    f.para("**Shopkeeper.** Visiting is free. Each item can be bought once, at the prices this scenario shows for **$**, **$$** and **$$$**. "
           "**Effect tiles** go on a square of your attack grid and give that effect whenever you reach it.")
    f.para("**Movement roll results.** A **wandering trader** sells the items listed on the sheet. A **stranded villager** "
           f"needs help: roll a die (1-2 fight 1 minion, 3-4 fight 2, 5-6 escort them to a rolled cell for **{pools.ESCORT_PAY} gold**). "
           f"**Hidden treasure**: make a STR roll to dig up **{pools.DIG_GOLD} gold**. A **trap**: make a DEX roll or take the damage shown.")

    f.heading("Map rolls and cells")
    f.para(f"A **map roll** is one die plus the stat named (STR, DEX, INT or WIS from your hero sheet): **{T} or more** succeeds. "
           "An **adjustment** changes one die of any map roll, including a movement roll, by 1 up or down.")
    f.para("**[_,_]** means roll a cell: one die per number, adding 6 if a second die shows 4-6, for a column and row from 1 to 12. "
           "**Q3[_,_]**: one die per number, counted inside quadrant 3.")

    f.heading("Ending the scenario")
    f.para("Defeat the boss to **win**. Then check your five **objectives**: win and complete **3 of 5** to **level up** "
           "(fill the next level box on your hero sheet). If your HP drops to 0, you lose the scenario; whether your hero "
           "tries again or retires is up to you.")
    f.para("**Leveling up.** At levels **3** and **5** choose your path on the hero sheet (one class at each step); each level "
           "adds the abilities its tag shows. Grid rows **10-11** unlock at level 3 and **12-13** at level 5.")

    f.heading("Fights")
    f.para("Minions: roll a die per minion on the minion cards. Minibosses: roll a die and use the card whose range it falls in. "
           "Each enemy drops the **gold** on its card when defeated. Your HP carries over between fights.")
    f.para("A fight is a series of rounds: you attack on your grid, then every enemy still standing attacks you. It ends when "
           "every enemy is at 0 HP (you win) or you are (you lose). Each enemy card lists its HP, its **weak point** "
           "(two squares on your grid), and its attacks, made **in order**: after the last, it starts again. **H** marks a heavy "
           "attack; a **wind-up** deals no damage. Before you attack, note each enemy's next attack.")
    f.heading("Each round")
    for i, t in enumerate(("**Potions.** Drink any you like (heal 5 each). You can also drink them between fights.",
                           "**Choose a target.** While an enemy with **Bodyguard** lives, you must target it.",
                           "**Attack** on your attack grid (below). Your total damage goes to your target; extra damage is lost. "
                           "Bonus effects resolve as they say.",
                           "**Fumble counter.** If your attack fumbled, take 3 damage. Guard doesn't block it.",
                           "**Poison and Venom** deal their damage: on enemies first, then on you.",
                           "**Enemy turn.** Each living enemy makes its next attack, one at a time. This round's guard absorbs "
                           "damage first, attack by attack; the rest comes off your HP.",
                           "**After the enemy turn,** class abilities like Riposte resolve. Then clear your grid: guard doesn't carry over "
                           "unless an ability says so."), 1):
        f.item(str(i), t)
    f.heading("Your attack")
    f.para("Roll four dice and split them into two pairs; each pair's total names a column. Move a runner up one square in each "
           "named column, placing a new runner if you have fewer than **3** on the grid. You must move as much as the roll allows, "
           "but you choose the pairs. A pair totaling **2 or 12 is wild**: move one square in any column. A column is full at the top "
           "of your grid: row **9** at levels 1-2, **11** at levels 3-4 and **13** at levels 5-6.")
    f.para("**You can't stop early.** Keep rolling until you **bust** (no pairing moves anything) or **fumble**. Then every "
           "filled square counts.")
    f.para("**Danger line.** Once any runner is on row 4 or higher (row 5 from level 6), check each roll before moving: **three or four of a kind** "
           "is a fumble. The attack ends, your squares still count, and you take the 3-damage fumble counter.")
    f.para("**Damage and guard.** Each filled square deals its column's damage (shown above the grid). Middle columns deal no "
           "damage but give **2 guard** per square; a **+1** square deals 1 extra damage and gives no guard.")
    f.para("**Surge.** The first time a column reaches its lightning square in an attack, take one free step in any column.")
    f.para("**Weak points.** The first time one of the enemy's weak squares is reached, take **2 free steps** and that column's "
           "damage is **doubled**. Reach **both** and your whole attack is doubled instead.")
    f.para("**Bonus squares.** The first time a column reaches a colored square, use one of your effects of that rarity. "
           "**Once** effects can be used once per attack. Your **top column** is your highest-damage column this attack.")
    f.para("**Pocket.** Instead of using an effect right away, you may write its rarity in your **pocket** (one at a time). "
           "On any later turn, erase it and use one of your effects of that rarity. A pocketed effect keeps until you use it.")
    f.heading("Keywords")
    f.para("Purple tags change the rules. On an enemy, they apply while it lives; on an attack, if it hits (deals damage after "
           "guard); in a boss phase, for that phase. **X** is the number after the keyword; on an attack, its damage. "
           "Columns in brackets are letters on your grid.", 12, INK2)
    for name, text in pools.KEYWORDS.items(): f.keyword(name, text)


class MarkdownFlow:
    """Writes the same content as Markdown (docs/rules.md)."""
    def __init__(self): self.out = ["# How to Play", "", "*One Sheet Wonder: scenario rules. Generated from `scen/render_rules.py`; do not edit by hand.*", ""]
    @staticmethod
    def md(t): return typo(t).replace("[_,_]", "`[_,_]`")
    def heading(self, text): self.out += [f"## {text}", ""]
    def para(self, text, *a, **k): self.out += [self.md(text), ""]
    def item(self, mark, text, *a, **k): self.out += [f"{mark}. {self.md(text)}"] + ([""] if False else [])
    def keyword(self, name, text):
        label, body = name, text
        if text.startswith(name + " ") and ":" in text: label, body = text.split(":", 1); body = body.strip()
        body = you(body); body = body[0].upper() + body[1:]
        self.out += [f"- **{label}** {self.md(body)}"]
    def text(self):
        lines, prev = [], ""
        for ln in self.out:                                   # blank line between a list and the next block
            if prev[:2] in ("- ",) or (prev[:1].isdigit() and ". " in prev[:4]):
                if ln and not (ln[:2] == "- " or (ln[:1].isdigit() and ". " in ln[:4])): lines.append("")
            lines.append(ln); prev = ln
        return "\n".join(lines).rstrip() + "\n"

def render_markdown(out):
    f = MarkdownFlow(); content(f)
    open(out, "w").write(f.text()); return out

def render(out):
    R._fonts(); os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    c = rl_canvas.Canvas(out, pagesize=letter); c.setTitle("One Sheet Wonder: How to Play"); c.setAuthor("One Sheet Wonder generator")
    f = Flow(c); page_title(f.pg, "HOW TO PLAY", "One Sheet Wonder \u00b7 scenario rules")
    content(f)
    c.showPage(); c.save(); return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out", default=os.path.join(os.getcwd(), "sheets", "one-sheet-wonder-rules.pdf"))
    ap.add_argument("--markdown", metavar="PATH", help="write the rules as Markdown instead (docs/rules.md)")
    a = ap.parse_args()
    print(render_markdown(a.markdown) if a.markdown else render(a.out))
