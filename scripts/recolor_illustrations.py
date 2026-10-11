"""Problem 9: recolor the two illustrations that sit on dark bands (red Problem 7, blue recommendation).

Run from the repo root:  python scripts/recolor_illustrations.py
The Streamline originals (scripts/assets/originals/) are black line art with white fills and blue accents,
which has poor contrast on dark red / Yale blue. This makes black lines white, white fills transparent
(so the band shows through), and blue accents a light tint of the band color.
"""

from pathlib import Path

from PIL import Image

ASSETS = Path(__file__).resolve().parent / "assets"
JOBS = {  # output name: (original, accent color)
    "redteam.png": ("hack-3.png", (255, 196, 196)),       # light pink on #8f1b1b
    "reco.png": ("investing-3.png", (158, 197, 244)),     # light Yale blue on #00356b
}


def recolor(src: Path, dst: Path, accent: tuple[int, int, int]) -> None:
    im = Image.open(src).convert("RGBA")
    out = []
    for r, g, b, a in im.getdata():
        chroma = max(r, g, b) - min(r, g, b)
        if chroma > 60:                                   # blue accent -> tint
            out.append((*accent, int(a * min(1.0, chroma / 150))))
        else:                                             # black line -> white, white fill -> transparent
            dark = 1 - (r + g + b) / (3 * 255)
            out.append((255, 255, 255, int(a * dark)))
    res = Image.new("RGBA", im.size)
    res.putdata(out)
    res.save(dst)


for name, (orig, accent) in JOBS.items():
    recolor(ASSETS / "originals" / orig, ASSETS / name, accent)
    print("wrote", ASSETS / name)
