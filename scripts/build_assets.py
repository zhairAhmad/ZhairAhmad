"""Generates the animated SVGs used in the profile README.

Run from the repo root:  python scripts/build_assets.py
Everything is self-contained SVG (CSS + SMIL animation, system fonts) so it
renders inside GitHub's <img> sandbox, which blocks external fonts and scripts.
"""

import math
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"

# ---------------------------------------------------------------- tokens
BG = "#0A0E1A"
PANEL = "#0E1324"
BORDER = "#1E2740"
TEXT = "#E8ECF4"
MUTED = "#8F9AB3"
DIM = "#5B6782"
INDIGO = "#7C8CFF"
CYAN = "#22D3EE"
VIOLET = "#A78BFA"
EMERALD = "#34D399"

SANS = "'Segoe UI', Inter, -apple-system, BlinkMacSystemFont, Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"

REDUCED_MOTION = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"

# ---------------------------------------------------------------- 3D helpers
PHI = (1 + 5 ** 0.5) / 2


def _normalize(points):
    return [tuple(c / math.sqrt(sum(v * v for v in p)) for c in p) for p in points]


def _edges_by_distance(points, tol=1e-6):
    dists = [
        math.dist(points[i], points[j])
        for i in range(len(points))
        for j in range(i + 1, len(points))
    ]
    shortest = min(dists)
    return [
        (i, j)
        for i in range(len(points))
        for j in range(i + 1, len(points))
        if abs(math.dist(points[i], points[j]) - shortest) < tol
    ]


def icosahedron():
    pts = []
    for a in (-1, 1):
        for b in (-PHI, PHI):
            pts += [(0, a, b), (a, b, 0), (b, 0, a)]
    pts = _normalize(pts)
    return pts, _edges_by_distance(pts)


def octahedron():
    pts = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    return pts, _edges_by_distance(pts)


def cube():
    pts = _normalize([(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)])
    return pts, _edges_by_distance(pts)


def tetrahedron():
    pts = _normalize([(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)])
    return pts, _edges_by_distance(pts)


def _transform(p, yaw, tilt):
    x, y, z = p
    c, s = math.cos(yaw), math.sin(yaw)
    x, z = c * x + s * z, -s * x + c * z
    c, s = math.cos(tilt), math.sin(tilt)
    y, z = c * y - s * z, s * y + c * z
    return x, y, z


def _project(p, cx, cy, scale, focal=4.0):
    x, y, z = p
    k = focal / (focal - z)
    return cx + x * scale * k, cy - y * scale * k, z


def _vals(seq):
    return ";".join(f"{v:.1f}" for v in seq)


def rotating_solid(shape, cx, cy, scale, *, dur, stroke, frames=48,
                   tilt=0.42, wobble=0.18, nodes=True, width=1.4,
                   node_fill="#FFFFFF", reverse=False):
    """Wireframe solid spinning around a tilted axis.

    Each edge and node gets SMIL keyframes for its projected position; opacity
    follows depth so the far side fades back and the shape reads as 3D.
    """
    pts, edges = shape
    direction = -1 if reverse else 1
    proj = []
    for f in range(frames + 1):
        t = f / frames
        yaw = direction * 2 * math.pi * t
        tl = tilt + wobble * math.sin(2 * math.pi * t)
        proj.append([_project(_transform(p, yaw, tl), cx, cy, scale) for p in pts])

    anim = f'dur="{dur}s" repeatCount="indefinite"'
    out = [f'<g stroke="{stroke}" stroke-width="{width}" stroke-linecap="round" fill="none">']
    for i, j in edges:
        x1 = [fr[i][0] for fr in proj]
        y1 = [fr[i][1] for fr in proj]
        x2 = [fr[j][0] for fr in proj]
        y2 = [fr[j][1] for fr in proj]
        op = [0.12 + 0.78 * ((fr[i][2] + fr[j][2]) / 2 + 1) / 2 for fr in proj]
        out.append(
            f'<line x1="{x1[0]:.1f}" y1="{y1[0]:.1f}" x2="{x2[0]:.1f}" y2="{y2[0]:.1f}">'
            f'<animate attributeName="x1" values="{_vals(x1)}" {anim}/>'
            f'<animate attributeName="y1" values="{_vals(y1)}" {anim}/>'
            f'<animate attributeName="x2" values="{_vals(x2)}" {anim}/>'
            f'<animate attributeName="y2" values="{_vals(y2)}" {anim}/>'
            f'<animate attributeName="stroke-opacity" values="{";".join(f"{o:.2f}" for o in op)}" {anim}/>'
            "</line>"
        )
    out.append("</g>")
    if nodes:
        out.append(f'<g fill="{node_fill}">')
        for i in range(len(pts)):
            xs = [fr[i][0] for fr in proj]
            ys = [fr[i][1] for fr in proj]
            depth = [(fr[i][2] + 1) / 2 for fr in proj]
            rs = [1.6 + 2.6 * d for d in depth]
            ops = [0.2 + 0.8 * d for d in depth]
            out.append(
                f'<circle cx="{xs[0]:.1f}" cy="{ys[0]:.1f}" r="{rs[0]:.1f}">'
                f'<animate attributeName="cx" values="{_vals(xs)}" {anim}/>'
                f'<animate attributeName="cy" values="{_vals(ys)}" {anim}/>'
                f'<animate attributeName="r" values="{_vals(rs)}" {anim}/>'
                f'<animate attributeName="opacity" values="{";".join(f"{o:.2f}" for o in ops)}" {anim}/>'
                "</circle>"
            )
        out.append("</g>")
    return "\n".join(out)


def iso_cube(x, y, s, gid, cls="", delay=0.0):
    """Shaded isometric cube centred on (x, y); floats via the .bob class."""
    h = s * 0.866
    top = f"{x},{y - s} {x + h},{y - s / 2} {x},{y} {x - h},{y - s / 2}"
    left = f"{x - h},{y - s / 2} {x},{y} {x},{y + s} {x - h},{y + s / 2}"
    right = f"{x},{y} {x + h},{y - s / 2} {x + h},{y + s / 2} {x},{y + s}"
    style = f' style="animation-delay:{delay}s"' if delay else ""
    return (
        f'<g class="{cls}"{style}>'
        f'<polygon points="{top}" fill="url(#{gid}-t)"/>'
        f'<polygon points="{left}" fill="url(#{gid}-l)"/>'
        f'<polygon points="{right}" fill="url(#{gid}-r)"/>'
        f'<polygon points="{top}" fill="none" stroke="#FFFFFF" stroke-opacity=".18" stroke-width=".8"/>'
        "</g>"
    )


def cube_gradients(gid, light, mid, dark):
    return (
        f'<linearGradient id="{gid}-t" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{light}"/><stop offset="1" stop-color="{mid}"/></linearGradient>'
        f'<linearGradient id="{gid}-l" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{mid}"/><stop offset="1" stop-color="{dark}"/></linearGradient>'
        f'<linearGradient id="{gid}-r" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{dark}"/><stop offset="1" stop-color="{BG}"/></linearGradient>'
    )


def text_width(s, size, mono=False):
    """Rough advance width; generous so layouts survive font fallbacks."""
    return len(s) * size * (0.62 if mono else 0.54)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------- hero
def hero():
    W, H = 1200, 420
    phrases = [
        "production RAG systems",
        "LLM agents with tool use",
        "document intelligence pipelines",
        "automation that runs itself",
    ]
    cycle = 3.2 * len(phrases)
    share = 100 / len(phrases)
    phrase_css = (
        f"@keyframes cyc{{0%{{opacity:0;transform:translateY(8px)}}"
        f"{share * 0.12:.1f}%{{opacity:1;transform:translateY(0)}}"
        f"{share * 0.88:.1f}%{{opacity:1;transform:translateY(0)}}"
        f"{share:.1f}%{{opacity:0;transform:translateY(-8px)}}100%{{opacity:0}}}}"
    )
    phrase_nodes = "".join(
        f'<text class="ph" x="64" y="296" style="animation-delay:{i * cycle / len(phrases):.1f}s">'
        f'<tspan font-weight="400" fill-opacity="0">I build </tspan>{esc(p)}</text>'
        for i, p in enumerate(phrases)
    )

    solid = rotating_solid(icosahedron(), 915, 205, 118, dur=22, stroke="url(#wire)",
                           width=1.5, node_fill="#DDE3FF")
    inner = rotating_solid(octahedron(), 915, 205, 46, dur=14, stroke=CYAN,
                           width=1.1, nodes=False, reverse=True, tilt=0.7)

    orbit = "M 745 205 a 170 44 0 1 0 340 0 a 170 44 0 1 0 -340 0"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">
<title id="t">Zhair Ahmad — AI Engineer</title>
<desc id="d">Generative AI, LLM applications, Python and automation.</desc>
<defs>
<linearGradient id="brand" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{INDIGO}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>
<linearGradient id="wire" gradientUnits="userSpaceOnUse" x1="760" y1="60" x2="1070" y2="350"><stop offset="0" stop-color="{VIOLET}"/><stop offset=".5" stop-color="{INDIGO}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>
<radialGradient id="fade" cx=".5" cy=".5" r=".6"><stop offset="0" stop-color="#fff" stop-opacity=".9"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
<pattern id="dots" width="28" height="28" patternUnits="userSpaceOnUse"><circle cx="1.5" cy="1.5" r="1.1" fill="#8FA0D8"/></pattern>
<mask id="gridmask"><rect width="{W}" height="{H}" fill="url(#fade)"/></mask>
<filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="60"/></filter>
<filter id="glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<clipPath id="card"><rect width="{W}" height="{H}" rx="22"/></clipPath>
{cube_gradients("c1", "#B9C2FF", INDIGO, "#3B3F8F")}
{cube_gradients("c2", "#A5F3FC", CYAN, "#0E5A6B")}
{cube_gradients("c3", "#DDD0FF", VIOLET, "#4C3A8C")}
</defs>
<style>
text{{font-family:{SANS}}}
.mono{{font-family:{MONO}}}
.bob{{animation:bob 7s ease-in-out infinite}}
.drift{{animation:drift 16s ease-in-out infinite}}
.ph{{font-size:21px;font-weight:600;fill:url(#brand);opacity:0;animation:cyc {cycle:.1f}s infinite}}
@keyframes bob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-12px)}}}}
@keyframes drift{{0%,100%{{transform:translate(0,0)}}50%{{transform:translate(-40px,25px)}}}}
@keyframes pulse{{0%{{r:5;opacity:.7}}100%{{r:14;opacity:0}}}}
.ring{{animation:pulse 2.2s ease-out infinite}}
{phrase_css}
{REDUCED_MOTION}
</style>
<g clip-path="url(#card)">
<rect width="{W}" height="{H}" fill="{BG}"/>
<circle class="drift" cx="980" cy="110" r="170" fill="{INDIGO}" opacity=".22" filter="url(#blur)"/>
<circle class="drift" style="animation-delay:-8s" cx="780" cy="360" r="140" fill="{CYAN}" opacity=".13" filter="url(#blur)"/>
<circle cx="120" cy="40" r="160" fill="{VIOLET}" opacity=".08" filter="url(#blur)"/>
<rect width="{W}" height="{H}" fill="url(#dots)" opacity=".12" mask="url(#gridmask)"/>

<!-- 3D scene -->
<path d="{orbit}" fill="none" stroke="{INDIGO}" stroke-opacity=".28" stroke-dasharray="2 7" transform="rotate(-14 915 205)"/>
<g filter="url(#glow)">{solid}</g>
<g opacity=".75">{inner}</g>
<g transform="rotate(-14 915 205)"><circle r="4.5" fill="{CYAN}" filter="url(#glow)"><animateMotion dur="9s" repeatCount="indefinite" path="{orbit}"/></circle></g>
{iso_cube(768, 96, 16, "c3", "bob", -2)}
{iso_cube(1098, 92, 26, "c1", "bob")}
{iso_cube(1112, 322, 17, "c2", "bob", -4)}
{iso_cube(760, 330, 22, "c1", "bob", -5.5)}

<!-- copy -->
<g>
<rect x="64" y="62" width="236" height="34" rx="17" fill="#FFFFFF" fill-opacity=".04" stroke="{BORDER}"/>
<circle class="ring" cx="86" cy="79" r="5" fill="{EMERALD}"/>
<circle cx="86" cy="79" r="4.5" fill="{EMERALD}"/>
<text x="102" y="84.5" font-size="14" fill="{TEXT}" font-weight="500">Open to AI Engineer roles</text>
</g>
<text x="62" y="172" font-size="68" font-weight="800" letter-spacing="-2" fill="{TEXT}">Zhair Ahmad</text>
<text x="64" y="218" font-size="24" fill="{MUTED}"><tspan font-weight="700" fill="url(#brand)">AI Engineer</tspan><tspan dx="10">·  Generative AI  ·  LLM Applications</tspan></text>
<rect x="64" y="244" width="56" height="3" rx="1.5" fill="url(#brand)"/>
<text x="64" y="296" font-size="21" fill="{MUTED}">I build</text>
{phrase_nodes}
<text class="mono" x="64" y="364" font-size="14.5" fill="{MUTED}" fill-opacity=".8" letter-spacing=".4">PYTHON  /  FASTAPI  /  LANGGRAPH  /  POSTGRES + PGVECTOR  /  DOCKER  /  AWS</text>
</g>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="22" fill="none" stroke="{BORDER}"/>
</svg>
"""


# ---------------------------------------------------------------- project cards
PROJECTS = [
    dict(
        slug="intelyze",
        label="TEXT-TO-SQL  ·  RAG",
        title="Intelyze",
        subtitle="Caribbean Economic Intelligence",
        desc="Bilingual (EN/NL) platform that answers plain-language questions over economic data with cited, chart-ready results.",
        metric="3-layer",
        caption="guardrails on every LLM-generated SQL query",
        tags=["FastAPI", "React", "PostgreSQL", "Claude API", "Docker"],
        accent=INDIGO,
        accent2=VIOLET,
        shape=octahedron,
    ),
    dict(
        slug="handelsregister",
        label="OCR  ·  VISION LLMs  ·  SCRAPING",
        title="Handelsregister",
        subtitle="Document Intelligence & CRM",
        desc="Six Dockerized services: parallel scrapers archive German register filings to S3, an OCR + VLM pipeline extracts the data.",
        metric="24% → 3%",
        caption="malformed outputs, ~2× recall",
        tags=["Python", "Selenium", "Vision LLMs", "PostgreSQL", "AWS S3"],
        accent=CYAN,
        accent2=INDIGO,
        shape=cube,
    ),
    dict(
        slug="cigarbid",
        label="AUTOMATION  ·  SCORING ENGINE",
        title="CigarBid",
        subtitle="Deal Intelligence System",
        desc="Playwright auction monitors with live price tracking and a scoring engine that ranks deals S–C against price history.",
        metric="512 MB",
        caption="VPS running the whole 4-service stack",
        tags=["Python", "Playwright", "Flask", "SQLite", "Docker"],
        accent=VIOLET,
        accent2="#F0ABFC",
        shape=tetrahedron,
    ),
    dict(
        slug="talents-pipeline",
        label="FULL-STACK  ·  REAL-TIME",
        title="Talents Pipeline",
        subtitle="Recruitment Platform",
        desc="Hiring platform for 3 user roles with applicant tracking, interview scheduling, live messaging and Claude-powered features.",
        metric="6-stage",
        caption="applicant tracking pipeline",
        tags=["Next.js", "TypeScript", "Prisma", "PostgreSQL", "Socket.IO"],
        accent=EMERALD,
        accent2=CYAN,
        shape=icosahedron,
    ),
]


def wrap(text, max_chars):
    lines, line = [], ""
    for word in text.split():
        if len(line) + len(word) + (1 if line else 0) > max_chars:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}" if line else word
    if line:
        lines.append(line)
    return lines


def card(p):
    W, H = 460, 270
    a, a2 = p["accent"], p["accent2"]
    desc = "".join(
        f'<text x="26" y="{122 + i * 20}" font-size="13.5" fill="{MUTED}">{esc(l)}</text>'
        for i, l in enumerate(wrap(p["desc"], 58))
    )
    x, tags = 26, []
    for t in p["tags"]:
        w = text_width(t, 11.5) + 18
        tags.append(
            f'<rect x="{x:.1f}" y="226" width="{w:.1f}" height="24" rx="12" fill="{a}" fill-opacity=".08" stroke="{a}" stroke-opacity=".28"/>'
            f'<text x="{x + w / 2:.1f}" y="242" font-size="11.5" text-anchor="middle" fill="{TEXT}" fill-opacity=".85">{esc(t)}</text>'
        )
        x += w + 6
    solid = rotating_solid(p["shape"](), 404, 62, 28, dur=16, stroke=a, width=1.2,
                           frames=40, node_fill=a, tilt=0.5)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{esc(p['title'])} — {esc(p['subtitle'])}">
<defs>
<linearGradient id="g" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{a2}"/></linearGradient>
<radialGradient id="glow" cx="1" cy="0" r="1"><stop offset="0" stop-color="{a}" stop-opacity=".18"/><stop offset=".6" stop-color="{a}" stop-opacity="0"/></radialGradient>
<clipPath id="c"><rect width="{W}" height="{H}" rx="18"/></clipPath>
</defs>
<style>text{{font-family:{SANS}}}.mono{{font-family:{MONO}}}{REDUCED_MOTION}</style>
<g clip-path="url(#c)">
<rect width="{W}" height="{H}" fill="{PANEL}"/>
<rect width="{W}" height="{H}" fill="url(#glow)"/>
<rect width="{W}" height="2" fill="url(#g)" opacity=".7"/>
</g>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="18" fill="none" stroke="{BORDER}"/>
{solid}
<text class="mono" x="26" y="40" font-size="11" letter-spacing="1.4" fill="{a}">{esc(p['label'])}</text>
<text x="26" y="72" font-size="23" font-weight="700" fill="{TEXT}" letter-spacing="-.4">{esc(p['title'])}</text>
<text x="26" y="94" font-size="14" fill="{TEXT}" fill-opacity=".7">{esc(p['subtitle'])}</text>
{desc}
<text x="26" y="200"><tspan font-size="22" font-weight="800" fill="url(#g)">{esc(p['metric'])}</tspan><tspan dx="12" dy="-1" font-size="12.5" fill="{MUTED}">{esc(p['caption'])}</tspan></text>
{''.join(tags)}
</svg>
"""


# ---------------------------------------------------------------- toolkit
TOOLKIT = [
    ("LLMs & Agents", INDIGO, ["Claude API", "OpenAI API", "LangChain", "LangGraph", "MCP",
                               "Tool Use", "Prompt Engineering"]),
    ("Retrieval", CYAN, ["RAG", "Text-to-SQL", "Hybrid Search · BM25", "pgvector",
                         "Embeddings", "Re-ranking"]),
    ("Vision & NLP", VIOLET, ["Vision-Language Models", "OCR · Tesseract · PyMuPDF",
                              "Hugging Face Transformers", "NLP"]),
    ("Eval & Ops", EMERALD, ["RAGAS", "Langfuse", "Docker", "AWS EC2 / S3", "GitHub Actions", "Linux"]),
    ("Data & Automation", "#F0ABFC", ["Playwright", "Selenium", "ETL / ELT", "Pandas",
                                      "Async Python", "Pydantic", "FastAPI"]),
]


def toolkit():
    W = 900
    left, right = 206, W - 28
    rows, y = [], 34
    for name, color, items in TOOLKIT:
        x, row_y = left, y
        pills = []
        for it in items:
            w = len(it) * 13 * 0.5 + 24
            if x + w > right:
                x, row_y = left, row_y + 40
            pills.append(
                f'<rect x="{x:.1f}" y="{row_y - 20}" width="{w:.1f}" height="30" rx="15" fill="{color}" fill-opacity=".07" stroke="{color}" stroke-opacity=".3"/>'
                f'<text x="{x + w / 2:.1f}" y="{row_y}" font-size="13" text-anchor="middle" fill="{TEXT}">{esc(it)}</text>'
            )
            x += w + 8
        rows.append(
            f'<rect x="28" y="{y - 11}" width="8" height="8" rx="2" fill="{color}" transform="rotate(45 32 {y - 7})"/>'
            f'<text class="mono" x="48" y="{y - 2}" font-size="12" letter-spacing="1.2" fill="{color}">{esc(name.upper())}</text>'
            + "".join(pills)
        )
        y = row_y + 52
        rows.append(f'<line x1="28" x2="{W - 28}" y1="{y - 26}" y2="{y - 26}" stroke="{BORDER}" stroke-dasharray="2 5"/>')
    rows.pop()  # no divider after the last group
    H = y - 22
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="AI and ML toolkit">
<defs>
<linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{INDIGO}" stop-opacity="0"/><stop offset=".5" stop-color="{CYAN}"/><stop offset="1" stop-color="{INDIGO}" stop-opacity="0"/></linearGradient>
<clipPath id="c"><rect width="{W}" height="{H}" rx="18"/></clipPath>
</defs>
<style>text{{font-family:{SANS}}}.mono{{font-family:{MONO}}}
.sw{{animation:sw 7s ease-in-out infinite}}@keyframes sw{{0%{{transform:translateX(-300px)}}100%{{transform:translateX({W}px)}}}}
{REDUCED_MOTION}</style>
<g clip-path="url(#c)">
<rect width="{W}" height="{H}" fill="{PANEL}"/>
<rect class="sw" width="300" height="2" fill="url(#sweep)"/>
</g>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="18" fill="none" stroke="{BORDER}"/>
{''.join(rows)}
</svg>
"""


# ---------------------------------------------------------------- footer
def footer():
    W, H = 900, 130
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Thanks for visiting">
<defs>
<linearGradient id="line" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{INDIGO}" stop-opacity="0"/><stop offset=".5" stop-color="{INDIGO}"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></linearGradient>
<linearGradient id="brand" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{INDIGO}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>
{cube_gradients("f1", "#B9C2FF", INDIGO, "#3B3F8F")}
{cube_gradients("f2", "#A5F3FC", CYAN, "#0E5A6B")}
{cube_gradients("f3", "#DDD0FF", VIOLET, "#4C3A8C")}
</defs>
<style>text{{font-family:{SANS}}}
.bob{{animation:bob 6s ease-in-out infinite}}@keyframes bob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-8px)}}}}
{REDUCED_MOTION}</style>
<rect x="90" y="36" width="720" height="1" fill="url(#line)"/>
{iso_cube(425, 36, 10, "f1", "bob")}
{iso_cube(450, 30, 13, "f2", "bob", -2)}
{iso_cube(475, 36, 10, "f3", "bob", -4)}
<text x="450" y="88" text-anchor="middle" font-size="21" font-weight="600" fill="url(#brand)">Building AI systems that hold up in production.</text>
<text x="450" y="114" text-anchor="middle" font-size="14.5" fill="{MUTED}">Thanks for stopping by.</text>
</svg>
"""


def main():
    (ASSETS / "projects").mkdir(parents=True, exist_ok=True)
    files = {"hero.svg": hero(), "toolkit.svg": toolkit(), "footer.svg": footer()}
    for p in PROJECTS:
        files[f"projects/{p['slug']}.svg"] = card(p)
    for name, svg in files.items():
        (ASSETS / name).write_text(svg, encoding="utf-8")
        print(f"{name:32} {len(svg.encode()) / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
