"""Generates every profile SVG in a light and a dark variant.

Run from the repo root:  python scripts/build_assets.py
The SVGs are self-contained (system fonts, CSS + SMIL animation) because
GitHub renders them through <img>, which blocks external fonts and scripts.
Backgrounds stay transparent so each section sits on GitHub's own page.
"""

import math
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"

SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

# GitHub's own light/dark text and border colours, plus one accent.
THEMES = {
    "light": dict(text="#1F2328", muted="#59636E", line="#D1D9E0", card="#F6F8FA", accent="#4F46E5"),
    "dark": dict(text="#F0F6FC", muted="#9198A1", line="#3D444D", card="#151B23", accent="#8B93FF"),
}
GREEN = "#2DA44E"
W = 900

STYLE = f"""<style>
text{{font-family:{SANS}}}
.mono{{font-family:{MONO}}}
.float{{animation:float 8s ease-in-out infinite}}
.shadow{{animation:shadow 8s ease-in-out infinite;transform-box:fill-box;transform-origin:center}}
.pulse{{animation:pulse 2.6s ease-in-out infinite}}
@keyframes float{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-8px)}}}}
@keyframes shadow{{0%,100%{{transform:scaleX(1);opacity:1}}50%{{transform:scaleX(.82);opacity:.6}}}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.35}}}}
@media (prefers-reduced-motion: reduce){{*{{animation:none!important}}}}
</style>"""

# ---------------------------------------------------------------- 3D shapes
PHI = (1 + 5 ** 0.5) / 2


def _solid(pts):
    norm = [tuple(c / math.sqrt(sum(v * v for v in p)) for c in p) for p in pts]
    edge = min(math.dist(norm[0], q) for q in norm[1:])
    edges = [
        (i, j)
        for i in range(len(norm))
        for j in range(i + 1, len(norm))
        if abs(math.dist(norm[i], norm[j]) - edge) < 1e-6
    ]
    return norm, edges


def icosahedron():
    pts = []
    for a in (-1, 1):
        for b in (-PHI, PHI):
            pts += [(0, a, b), (a, b, 0), (b, 0, a)]
    return _solid(pts)


def octahedron():
    return _solid([(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)])


def cube():
    return _solid([(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)])


def tetrahedron():
    return _solid([(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)])


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


def rotating_solid(shape, cx, cy, scale, color, *, dur=32, frames=60, tilt=0.38,
                   wobble=0.12, node=1.8):
    """Wireframe solid turning slowly; far edges fade so it reads as 3D."""
    pts, edges = shape
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
            f'<circle cx="{xs[0]:.1f}" cy="{ys[0]:.1f}" r="{node}">'
            f'<animate attributeName="cx" values="{_vals(xs)}" {anim}/>'
            f'<animate attributeName="cy" values="{_vals(ys)}" {anim}/>'
            f'<animate attributeName="r" values="{_vals([node * (0.65 + d) for d in depth])}" {anim}/>'
            f'<animate attributeName="opacity" values="{_vals([0.25 + 0.75 * d for d in depth], "{:.2f}")}" {anim}/>'
            "</circle>"
        )
    out.append("</g>")
    return "\n".join(out)


# ---------------------------------------------------------------- helpers
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def wrap(text, max_chars):
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > max_chars:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return lines + [line] if line else lines


def svg(h, body, label, pad=0):
    """Wraps a section; `pad` adds breathing room above it."""
    h += pad
    if pad:
        body = f'<g transform="translate(0 {pad})">{body}</g>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}" '
        f'role="img" aria-label="{esc(label)}">\n{STYLE}\n{body}\n</svg>\n'
    )


def section_label(c, num, title, x=0, width=W, y=24):
    """'01  ABOUT ────────' in the header's mono label style."""
    end = x + 2 + (len(num) + 1 + len(title)) * (13 * 0.6 + 2.5)
    return (
        f'<text class="mono" x="{x + 2}" y="{y}" font-size="13" letter-spacing="2.5">'
        f'<tspan fill="{c["accent"]}">{num}</tspan><tspan dx="10" fill="{c["muted"]}">{esc(title)}</tspan></text>'
        f'<rect x="{end + 14:.0f}" y="{y - 5}" width="{x + width - end - 14:.0f}" height="1" fill="{c["line"]}"/>'
    )


# ---------------------------------------------------------------- sections
def header(c):
    cx, cy = 790, 112
    body = f"""<defs><radialGradient id="shadow"><stop offset="0" stop-color="{c['accent']}" stop-opacity=".22"/><stop offset="1" stop-color="{c['accent']}" stop-opacity="0"/></radialGradient></defs>
<text class="mono" x="2" y="46" font-size="14" letter-spacing="2.5" fill="{c['accent']}">AI ENGINEER</text>
<text x="0" y="112" font-size="54" font-weight="700" letter-spacing="-1.6" fill="{c['text']}">Zhair Ahmad</text>
<text x="1" y="150" font-size="20" fill="{c['muted']}">Generative AI, LLM applications and automation.</text>
<rect x="2" y="182" width="36" height="2" rx="1" fill="{c['accent']}"/>
<circle class="pulse" cx="7" cy="218" r="4.5" fill="{GREEN}"/>
<text x="21" y="224" font-size="16" fill="{c['muted']}">Open to AI Engineer roles  ·  Sahiwal, Pakistan</text>
<ellipse class="shadow" cx="{cx}" cy="{cy + 104}" rx="62" ry="7" fill="url(#shadow)"/>
<g class="float">{rotating_solid(icosahedron(), cx, cy, 78, c['accent'])}</g>"""
    return svg(250, body, "Zhair Ahmad, AI Engineer. Generative AI, LLM applications and automation.")


STATS = [
    ("4", "AI & automation systems built"),
    ("24% → 3%", "malformed model outputs"),
    ("2×", "recall at 19% lower cost"),
]


def about(c):
    a = c["accent"]
    lines = [
        f'I build Generative AI systems that <tspan fill="{a}" font-weight="600">hold up in production</tspan>:',
        "RAG over real data, LLM agents with tool use and document intelligence",
        "pipelines, on a solid base of Python, FastAPI and Next.js, shipped on AWS.",
    ]
    para = "".join(
        f'<text x="0" y="{72 + i * 30}" font-size="19" fill="{c["text"]}">{l}</text>'
        for i, l in enumerate(lines)
    )
    col = W / len(STATS)
    stats = []
    for i, (num, cap) in enumerate(STATS):
        x = i * col
        stats.append(
            f'<rect x="{x:.0f}" y="178" width="22" height="2" rx="1" fill="{a}"/>'
            f'<text x="{x:.0f}" y="224" font-size="36" font-weight="700" letter-spacing="-1" fill="{c["text"]}">{esc(num)}</text>'
            f'<text x="{x:.0f}" y="252" font-size="14.5" fill="{c["muted"]}">{esc(cap)}</text>'
        )
        if i:
            stats.append(f'<rect x="{x - 26:.0f}" y="178" width="1" height="78" fill="{c["line"]}"/>')
    body = section_label(c, "01", "ABOUT") + para + "".join(stats)
    return svg(268, body, "About: I build Generative AI systems that hold up in production.", pad=40)


PROJECTS = [
    ("TEXT-TO-SQL · RAG", "Intelyze", "Bilingual (EN/NL) answers over Caribbean economic data, with citations and chart-ready results.",
     "3-layer", "guardrails on generated SQL", "FastAPI · React · PostgreSQL · Claude API", octahedron),
    ("DOCUMENT AI", "Handelsregister", "Scrapers archive German register filings to S3; an OCR + vision-LLM pipeline extracts the data.",
     "24% → 3%", "malformed model outputs", "Python · Selenium · Vision LLMs · AWS S3", cube),
    ("AUTOMATION", "CigarBid", "Playwright auction monitors and a scoring engine that ranks deals against price history.",
     "512 MB", "VPS runs the full stack", "Python · Playwright · Flask · Docker", tetrahedron),
    ("FULL-STACK", "Talents Pipeline", "Hiring platform for 3 user roles with interview scheduling, real-time chat and Claude features.",
     "6-stage", "applicant pipeline", "Next.js · TypeScript · Prisma · Socket.IO", icosahedron),
]


def work(c):
    a = c["accent"]
    cw, ch, gap, top = (W - 20) / 2, 232, 20, 52
    cards = []
    for n, (label, title, desc, metric, cap, tech, shape) in enumerate(PROJECTS):
        ox = (n % 2) * (cw + gap)
        oy = top + (n // 2) * (ch + gap)
        desc_lines = wrap(desc, 52)
        assert len(desc_lines) <= 2, title
        cards.append(
            f'<rect x="{ox + .5:.1f}" y="{oy + .5:.1f}" width="{cw - 1:.1f}" height="{ch - 1}" rx="14" fill="{c["card"]}" stroke="{c["line"]}"/>'
            + rotating_solid(shape(), ox + cw - 52, oy + 52, 24, a, dur=24 + 4 * n, frames=48, node=1.4, tilt=0.5)
            + f'<text class="mono" x="{ox + 24:.0f}" y="{oy + 38}" font-size="11.5" letter-spacing="1.6" fill="{a}">{esc(label)}</text>'
            f'<text x="{ox + 24:.0f}" y="{oy + 72}" font-size="22" font-weight="700" letter-spacing="-.4" fill="{c["text"]}">{esc(title)}</text>'
            + "".join(
                f'<text x="{ox + 24:.0f}" y="{oy + 102 + i * 21}" font-size="14.5" fill="{c["muted"]}">{esc(l)}</text>'
                for i, l in enumerate(desc_lines)
            )
            + f'<text x="{ox + 24:.0f}" y="{oy + 172}"><tspan font-size="21" font-weight="700" fill="{a}">{esc(metric)}</tspan>'
            f'<tspan dx="10" font-size="13.5" fill="{c["muted"]}">{esc(cap)}</tspan></text>'
            f'<rect x="{ox + 24:.0f}" y="{oy + 190}" width="{cw - 48:.0f}" height="1" fill="{c["line"]}"/>'
            f'<text class="mono" x="{ox + 24:.0f}" y="{oy + 214}" font-size="12" fill="{c["muted"]}">{esc(tech)}</text>'
        )
    body = section_label(c, "02", "SELECTED WORK") + "".join(cards)
    return svg(int(top + 2 * ch + gap + 2), body, "Selected work: Intelyze, Handelsregister, CigarBid, Talents Pipeline.", pad=40)


STACK = [
    ("AI", ["LLMs & RAG", "LangChain · LangGraph", "MCP & tool use", "Hybrid search · pgvector",
            "RAGAS · Langfuse", "Vision LLMs & OCR"]),
    ("Engineering", ["Python", "FastAPI · Pydantic", "TypeScript", "Next.js · React",
                     "PostgreSQL", "MongoDB"]),
    ("Infra & automation", ["Docker", "AWS · EC2, S3", "GitHub Actions", "Linux",
                            "Playwright", "Selenium"]),
]


def stack(c):
    a = c["accent"]
    col, colw = (W + 30) / 3, (W + 30) / 3 - 30
    parts = [section_label(c, "03", "STACK")]
    for i, (name, items) in enumerate(STACK):
        x = i * col
        parts.append(
            f'<rect x="{x + 1:.0f}" y="62" width="8" height="8" rx="1.5" fill="{a}" transform="rotate(45 {x + 5:.0f} 66)"/>'
            f'<text x="{x + 20:.0f}" y="72" font-size="16" font-weight="600" fill="{c["text"]}">{esc(name)}</text>'
        )
        for j, it in enumerate(items):
            y = 112 + j * 34
            parts.append(
                f'<text x="{x:.0f}" y="{y}" font-size="15" fill="{c["muted"]}">{esc(it)}</text>'
                f'<rect x="{x:.0f}" y="{y + 12}" width="{colw:.0f}" height="1" fill="{c["line"]}" opacity=".7"/>'
            )
    return svg(300, "".join(parts), "Stack: AI, engineering, infrastructure and automation tools.", pad=40)


def education_now(c):
    a, half = c["accent"], (W - 40) / 2
    rx = half + 40
    body = (
        section_label(c, "04", "EDUCATION", 0, half)
        + section_label(c, "05", "NOW", rx, half)
        + f'<text x="0" y="72" font-size="19" font-weight="600" fill="{c["text"]}">COMSATS University Islamabad</text>'
        f'<text x="0" y="100" font-size="15.5" fill="{c["muted"]}">BS Computer Science</text>'
        f'<text class="mono" x="0" y="128" font-size="13" fill="{a}">2026  ·  CGPA 3.7 / 4.0</text>'
        f'<text x="0" y="160" font-size="14.5" fill="{c["muted"]}">NLP Specialization, DeepLearning.AI</text>'
        f'<circle class="pulse" cx="{rx + 6:.0f}" cy="66" r="4.5" fill="{GREEN}"/>'
        f'<text x="{rx + 20:.0f}" y="72" font-size="19" font-weight="600" fill="{c["text"]}">Looking for my next role</text>'
        f'<text x="{rx:.0f}" y="100" font-size="15.5" fill="{c["muted"]}">AI Engineer or Automation Engineer</text>'
        f'<text class="mono" x="{rx:.0f}" y="128" font-size="13" fill="{a}">SIDE PROJECT</text>'
        f'<text x="{rx:.0f}" y="160" font-size="14.5" fill="{c["muted"]}">Pakistan Compass, a travel app for northern Pakistan</text>'
    )
    return svg(180, body, "Education: BS Computer Science, COMSATS 2026. Now: looking for an AI Engineer role.", pad=40)


def contact(c):
    a = c["accent"]
    body = (
        section_label(c, "06", "CONTACT")
        + f'<text x="0" y="86" font-size="34" font-weight="700" letter-spacing="-1" fill="{c["text"]}">Let\'s build something reliable.</text>'
        f'<text x="1" y="126" font-size="18" fill="{a}">zhairdeveloper@gmail.com  →</text>'
        + rotating_solid(tetrahedron(), 840, 82, 30, a, dur=26, frames=48, node=1.4, tilt=0.5)
    )
    return svg(150, body, "Contact: zhairdeveloper@gmail.com", pad=40)


SECTIONS = {
    "header": header,
    "about": about,
    "work": work,
    "stack": stack,
    "education-now": education_now,
    "contact": contact,
}


def main():
    ASSETS.mkdir(exist_ok=True)
    for name, build in SECTIONS.items():
        for theme, colors in THEMES.items():
            out = build(colors)
            path = ASSETS / f"{name}-{theme}.svg"
            path.write_text(out, encoding="utf-8")
            print(f"{path.name:28} {len(out.encode()) / 1024:5.1f} KB")


if __name__ == "__main__":
    main()
