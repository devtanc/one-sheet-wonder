# Hero sheet design

`hero-sheet-warrior.dc.html` is the source of the Warrior hero sheet as designed on the canvas (US Letter landscape,
1056 x 816 CSS px, 5 mm margins). It is a design-tool document: open and edit it on the canvas, not as a plain web page.

`scen/render_hero.py` reproduces it measurement for measurement. The workflow is: change the design on the canvas first,
save its source here, then update `render_hero.py` to match.

Fixed constraints: the sheet is single-sided, and attack-grid squares stay 12 mm or more so a die fits.
