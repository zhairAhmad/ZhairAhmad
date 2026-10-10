"""Generates the profile header SVGs (light and dark variants).

Run from the repo root:  python scripts/build_assets.py
The SVGs are self-contained (system fonts, CSS + SMIL animation) because
GitHub renders them through <img>, which blocks external fonts and scripts.
"""

import math
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"

SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

# Matches GitHub's own light and dark text colours, plus one accent.
THEMES = {
    "light": dict(text="#1F2328", muted="#59636E", accent="#4F46E5"),
    "dark": dict(text="#F0F6FC", muted="#9198A1", accent="#8B93FF"),
}

PHI = (1 + 5 ** 0.5) / 2


def icosahedron():
    pts = []
    for a in (-1, 1):
        for b in (-PHI, PHI):
            pts += [(0, a, b), (a, b, 0), (b, 0, a)]
    norm = math.sqrt(1 + PHI * PHI)
    pts = [tuple(c / norm for c in p) for p in pts]
    edge = min(math.dist(pts[0], q) for q in pts[1:])
    edges = [
        (i, j)
        for i in range(len(pts))
        for j in range(i + 1, len(pts))
        if abs(math.dist(pts[i], pts[j]) - edge) < 1e-6
    ]
    return pts, edges


def _project(p, yaw, tilt, cx, cy, scale, focal=4.0):
    x, y, z = p
    c, s = math.cos(yaw), math.sin(yaw)
    x, z = c * x + s * z, -s * x + c * z
    c, s = math.cos(tilt), math.sin(tilt)
    y, z = c * y - s * z, s * y + c * z
    k = focal / (focal - z)
    return cx + x * scale * k, cy - y * scale * k, z


def _vals(seq, fmt="{:.1f}"):
    return ";".join(fmt.format(v) for v in seq)


def rotating_solid(cx, cy, scale, color, *, dur=32, frames=60, tilt=0.38, wobble=0.12):
    """Wireframe icosahedron turning slowly; far edges fade so it reads as 3D."""
    pts, edges = icosahedron()
    proj = []
    for f in range(frames + 1):
        t = f / frames
        tl = tilt + wobble * math.sin(2 * math.pi * t)
        proj.append([_project(p, 2 * math.pi * t, tl, cx, cy, scale) for p in pts])

    anim = f'dur="{dur}s" repeatCount="indefinite"'
    out = [f'<g stroke="{color}" stroke-width="1.2" stroke-linecap="round">']
    for i, j in edges:
        cols = [[fr[i][0] for fr in proj], [fr[i][1] for fr in proj],
                [fr[j][0] for fr in proj], [fr[j][1] for fr in proj]]
        op = [0.1 + 0.75 * ((fr[i][2] + fr[j][2]) / 2 + 1) / 2 for fr in proj]
        out.append(
            f'<line x1="{cols[0][0]:.1f}" y1="{cols[1][0]:.1f}" x2="{cols[2][0]:.1f}" y2="{cols[3][0]:.1f}">'
            + "".join(
                f'<animate attributeName="{a}" values="{_vals(v)}" {anim}/>'
                for a, v in zip(("x1", "y1", "x2", "y2"), cols)
            )
            + f'<animate attributeName="stroke-opacity" values="{_vals(op, "{:.2f}")}" {anim}/>'
            "</line>"
        )
    out.append(f'</g><g fill="{color}">')
    for i in range(len(pts)):
        xs = [fr[i][0] for fr in proj]
        ys = [fr[i][1] for fr in proj]
        depth = [(fr[i][2] + 1) / 2 for fr in proj]
        out.append(
            f'<circle cx="{xs[0]:.1f}" cy="{ys[0]:.1f}" r="2">'
            f'<animate attributeName="cx" values="{_vals(xs)}" {anim}/>'
            f'<animate attributeName="cy" values="{_vals(ys)}" {anim}/>'
            f'<animate attributeName="r" values="{_vals([1.2 + 1.8 * d for d in depth])}" {anim}/>'
            f'<animate attributeName="opacity" values="{_vals([0.25 + 0.75 * d for d in depth], "{:.2f}")}" {anim}/>'
            "</circle>"
        )
    out.append("</g>")
    return "\n".join(out)


def header(theme):
    c = THEMES[theme]
    W, H = 900, 250
    cx, cy = 790, 112
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t">
<title id="t">Zhair Ahmad, AI Engineer</title>
<defs>
<radialGradient id="shadow"><stop offset="0" stop-color="{c['accent']}" stop-opacity=".22"/><stop offset="1" stop-color="{c['accent']}" stop-opacity="0"/></radialGradient>
</defs>
<style>
text{{font-family:{SANS}}}
.mono{{font-family:{MONO}}}
.float{{animation:float 8s ease-in-out infinite}}
.shadow{{animation:shadow 8s ease-in-out infinite;transform-box:fill-box;transform-origin:center}}
.pulse{{animation:pulse 2.6s ease-in-out infinite}}
@keyframes float{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-8px)}}}}
@keyframes shadow{{0%,100%{{transform:scaleX(1);opacity:1}}50%{{transform:scaleX(.82);opacity:.6}}}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.35}}}}
@media (prefers-reduced-motion: reduce){{*{{animation:none!important}}}}
</style>

<text class="mono" x="2" y="46" font-size="14" letter-spacing="2.5" fill="{c['accent']}">AI ENGINEER</text>
<text x="0" y="112" font-size="54" font-weight="700" letter-spacing="-1.6" fill="{c['text']}">Zhair Ahmad</text>
<text x="1" y="150" font-size="20" fill="{c['muted']}">Generative AI, LLM applications and automation.</text>
<rect x="2" y="182" width="36" height="2" rx="1" fill="{c['accent']}"/>
<circle class="pulse" cx="7" cy="218" r="4.5" fill="#2DA44E"/>
<text x="21" y="224" font-size="16" fill="{c['muted']}">Open to AI Engineer roles  ·  Sahiwal, Pakistan</text>

<ellipse class="shadow" cx="{cx}" cy="{cy + 104}" rx="62" ry="7" fill="url(#shadow)"/>
<g class="float">
{rotating_solid(cx, cy, 78, c['accent'])}
</g>
</svg>
"""


def main():
    ASSETS.mkdir(exist_ok=True)
    for theme in THEMES:
        svg = header(theme)
        path = ASSETS / f"header-{theme}.svg"
        path.write_text(svg, encoding="utf-8")
        print(f"{path.name:22} {len(svg.encode()) / 1024:5.1f} KB")


if __name__ == "__main__":
    main()
