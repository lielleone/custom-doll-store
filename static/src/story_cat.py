"""Generate templates/partials/story_cat.svg (the home page story drawing).

Run from the project folder:
    venv/bin/python static/src/story_cat.py > templates/partials/story_cat.svg

A child's crayon cat sketch on notebook paper plus the layers it turns into
(cutting pattern, felt pieces, stitches, shading). The element ids are used by
static/js/story.js, keep them. Deterministic (fixed random seed)."""
import math
import random
import sys

random.seed(7)

# ---------- smooth shapes (the finished doll) ----------
BODY = ("M 82 190 C 78 150 84 110 98 72 C 118 92 140 112 160 124 C 185 118 220 118 245 124 "
        "C 262 110 282 94 304 80 C 318 118 324 156 320 194 C 336 238 318 284 262 296 "
        "C 270 340 276 400 268 440 C 240 452 160 452 132 440 C 124 400 130 340 138 296 "
        "C 82 284 64 238 82 190 Z")
TAIL = ("M 266 405 C 300 410 318 380 312 356 C 309 344 322 338 330 348 "
        "C 342 366 330 420 268 428 Z")
SPOTS = [
    "M 84 168 C 80 140 92 112 104 102 C 118 118 120 150 108 172 C 100 180 88 180 84 168 Z",
    "M 292 104 C 304 96 314 120 318 150 C 318 170 300 170 294 150 C 290 135 286 112 292 104 Z",
    "M 240 330 C 262 326 270 360 262 390 C 252 396 240 380 238 360 C 236 345 234 334 240 330 Z",
    "M 134 420 C 150 412 170 418 168 438 C 160 446 140 446 132 440 C 130 432 128 424 134 420 Z",
]
EYES = [(160, 205, 30, 32), (240, 205, 30, 32)]
PUPILS = [(164, 211, 13, 18), (236, 211, 13, 18)]
MOUTH = "M 186 248 Q 193 258 200 248 Q 207 258 214 248"
WHISKERS = ["M 126 226 L 90 216", "M 126 238 L 88 240", "M 274 226 L 310 216", "M 274 238 L 312 240"]
LEGS = ["M 172 342 L 172 430 Q 182 440 192 430 L 192 346", "M 208 346 L 208 430 Q 218 440 228 430 L 228 342"]


def ellipse_d(cx, cy, rx, ry):
    """Ellipse as four cubic Beziers (kappa approximation), no arc commands."""
    k = 0.5523
    ox, oy = rx * k, ry * k
    f = lambda v: f"{v:.1f}"
    return (f"M {f(cx - rx)} {f(cy)} "
            f"C {f(cx - rx)} {f(cy - oy)} {f(cx - ox)} {f(cy - ry)} {f(cx)} {f(cy - ry)} "
            f"C {f(cx + ox)} {f(cy - ry)} {f(cx + rx)} {f(cy - oy)} {f(cx + rx)} {f(cy)} "
            f"C {f(cx + rx)} {f(cy + oy)} {f(cx + ox)} {f(cy + ry)} {f(cx)} {f(cy + ry)} "
            f"C {f(cx - ox)} {f(cy + ry)} {f(cx - rx)} {f(cy + oy)} {f(cx - rx)} {f(cy)} Z")


# ---------- tiny path sampler (M, L, C, Q, Z only) ----------
def tokens(d):
    out, num = [], ""
    for ch in d.replace(",", " "):
        if ch.isalpha():
            if num.strip():
                out.append(float(num)); num = ""
            out.append(ch)
        elif ch == " ":
            if num.strip():
                out.append(float(num)); num = ""
        else:
            num += ch
    if num.strip():
        out.append(float(num))
    return out


def sample(d, step=5.0):
    t = tokens(d)
    pts, i, cur, start, cmd = [], 0, (0, 0), (0, 0), None
    def take(n):
        nonlocal i
        vals = t[i:i + n]; i += n
        return vals
    while i < len(t):
        if isinstance(t[i], str):
            cmd = t[i]; i += 1
            if cmd == "Z":
                pts += line_pts(cur, start, step); cur = start
            continue
        if cmd == "M":
            x, y = take(2); cur = start = (x, y); pts.append(cur); cmd = "L"
        elif cmd == "L":
            x, y = take(2); pts += line_pts(cur, (x, y), step); cur = (x, y)
        elif cmd == "C":
            x1, y1, x2, y2, x, y = take(6)
            pts += curve_pts([cur, (x1, y1), (x2, y2), (x, y)], step); cur = (x, y)
        elif cmd == "Q":
            x1, y1, x, y = take(4)
            pts += curve_pts([cur, (x1, y1), (x, y)], step); cur = (x, y)
        else:
            raise ValueError(cmd)
    return pts


def line_pts(a, b, step):
    n = max(1, int(math.dist(a, b) / step))
    return [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(1, n + 1)]


def bez(p, s):
    if len(p) == 3:
        return tuple((1 - s) ** 2 * p[0][j] + 2 * (1 - s) * s * p[1][j] + s * s * p[2][j] for j in (0, 1))
    return tuple((1 - s) ** 3 * p[0][j] + 3 * (1 - s) ** 2 * s * p[1][j] + 3 * (1 - s) * s * s * p[2][j]
                 + s ** 3 * p[3][j] for j in (0, 1))


def curve_pts(p, step):
    approx = sum(math.dist(p[k], p[k + 1]) for k in range(len(p) - 1))
    n = max(2, int(approx / step))
    return [bez(p, k / n) for k in range(1, n + 1)]


def wobble(d, amp=2.2, step=5.0, overshoot=True, closed=False):
    """Hand-drawn version: smooth random sideways drift, a small overshoot at
    the end (the line does not meet itself), coordinates to one decimal."""
    pts = sample(d, step)
    if closed and overshoot:
        pts = pts + pts[1:4]          # draw a little past the start, like a child does
    ph = [random.uniform(0, 6.28) for _ in range(3)]
    fr = [random.uniform(0.02, 0.05), random.uniform(0.07, 0.12), random.uniform(0.18, 0.3)]
    out = []
    for k, (x, y) in enumerate(pts):
        a, b = pts[max(k - 1, 0)], pts[min(k + 1, len(pts) - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy) or 1
        nx, ny = -dy / ln, dx / ln
        off = amp * (math.sin(k * fr[0] * 6 + ph[0]) * 0.6 + math.sin(k * fr[1] * 6 + ph[1]) * 0.3
                     + math.sin(k * fr[2] * 6 + ph[2]) * 0.1)
        out.append((x + nx * off, y + ny * off))
    return "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in out)


def scribble(bbox, angle_deg, gap, amp_jitter=1.5):
    """Back-and-forth crayon hatching across a bounding box (clipped later)."""
    x0, y0, x1, y1 = bbox
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = math.hypot(x1 - x0, y1 - y0) / 2 + 6
    a = math.radians(angle_deg)
    ux, uy = math.cos(a), math.sin(a)      # stroke direction
    vx, vy = -uy, ux                       # advance direction
    pts, s, flip = [], -r, False
    while s <= r:
        e1 = (cx + vx * s - ux * r, cy + vy * s - uy * r)
        e2 = (cx + vx * s + ux * r, cy + vy * s + uy * r)
        p, q = (e2, e1) if flip else (e1, e2)
        j = random.uniform(-amp_jitter, amp_jitter)
        pts += [(p[0] + j, p[1] + j), (q[0] - j, q[1] + j)]
        s += gap * random.uniform(0.8, 1.2); flip = not flip
    return "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)


def bbox_of(d):
    p = sample(d, 4)
    xs, ys = [q[0] for q in p], [q[1] for q in p]
    return min(xs), min(ys), max(xs), max(ys)


# ---------- build the SVG ----------
sk = []  # sketch paths: (id or None, d)
sk.append(("sk-outline", wobble(BODY, 2.4, closed=True)))
sk.append((None, wobble(TAIL, 2.0, closed=True)))
for cx, cy, rx, ry in EYES:
    sk.append((None, wobble(ellipse_d(cx, cy, rx, ry), 1.8, step=4, closed=True)))
for s_ in SPOTS:
    sk.append((None, wobble(s_, 1.6, step=4, closed=True)))
sk.append((None, wobble(MOUTH, 1.0, step=3)))
for w in WHISKERS + LEGS:
    sk.append((None, wobble(w, 1.6, step=4)))

pupils_sketch = [wobble(ellipse_d(*p), 1.2, step=3, closed=True) for p in PUPILS]
scr = [("clip-body", scribble(bbox_of(BODY), -32, 9), "#facc15", 0.55, 7),
       ("clip-tail", scribble(bbox_of(TAIL), 40, 6), "#92400e", 0.8, 5)]
for k, s_ in enumerate(SPOTS):
    scr.append((f"clip-spot{k}", scribble(bbox_of(s_), 50 + k * 17, 5), "#92400e", 0.85, 5))
for k, p in enumerate(PUPILS):
    scr.append((f"clip-pupil{k}", scribble(bbox_of(ellipse_d(*p)), 70, 3.5), "#1f2937", 0.95, 4))

L = []
w = L.append
w('<svg class="story-svg" viewBox="0 0 400 500" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">')
w('<defs>')
w('<filter id="crayon" x="-5%" y="-5%" width="110%" height="110%">'
  '<feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="3" result="n"/>'
  '<feDisplacementMap in="SourceGraphic" in2="n" scale="3.5" xChannelSelector="R" yChannelSelector="G"/></filter>')
w('<filter id="felt" x="0" y="0" width="100%" height="100%">'
  '<feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="3" seed="8" result="noise"/>'
  '<feColorMatrix in="noise" type="matrix" values="0 0 0 0 0.45  0 0 0 0 0.35  0 0 0 0 0.25  0 0 0 0.2 0" result="fibers"/>'
  '<feComposite in="fibers" in2="SourceAlpha" operator="in" result="fibersIn"/>'
  '<feMerge><feMergeNode in="SourceGraphic"/><feMergeNode in="fibersIn"/></feMerge></filter>')
w('<filter id="soft" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>')
w('<radialGradient id="puff" cx="38%" cy="30%" r="75%">'
  '<stop offset="0" stop-color="#fff" stop-opacity="0.45"/>'
  '<stop offset="0.45" stop-color="#fff" stop-opacity="0"/>'
  '<stop offset="0.85" stop-color="#78350f" stop-opacity="0.18"/>'
  '<stop offset="1" stop-color="#78350f" stop-opacity="0.32"/></radialGradient>')
w('<pattern id="notebook" width="400" height="24" patternUnits="userSpaceOnUse">'
  '<line x1="0" y1="23.5" x2="400" y2="23.5" stroke="#bfdbfe" stroke-width="1"/></pattern>')
w(f'<clipPath id="clip-body"><path d="{BODY}"/></clipPath>')
w(f'<clipPath id="clip-tail"><path d="{TAIL}"/></clipPath>')
for k, s_ in enumerate(SPOTS):
    w(f'<clipPath id="clip-spot{k}"><path d="{s_}"/></clipPath>')
for k, p in enumerate(PUPILS):
    w(f'<clipPath id="clip-pupil{k}"><path d="{ellipse_d(*p)}"/></clipPath>')
# mask that reveals the dashed stitches as the solid copies are "drawn"
w('<mask id="stitch-mask" maskUnits="userSpaceOnUse" x="0" y="0" width="400" height="500">')
stitch_paths = [BODY, TAIL] + SPOTS + [ellipse_d(*e) for e in EYES] + [MOUTH] + WHISKERS + LEGS
for d in stitch_paths:
    w(f'<path class="st-reveal" d="{d}" fill="none" stroke="#fff" stroke-width="9" stroke-linecap="round"/>')
w('</mask>')
w('</defs>')

# paper
w('<g id="s-paper">'
  '<rect x="22" y="18" width="356" height="464" rx="6" fill="#fffdf7" stroke="#e5e7eb" stroke-width="2"/>'
  '<rect x="22" y="42" width="356" height="440" fill="url(#notebook)"/>'
  '<line x1="350" y1="18" x2="350" y2="482" stroke="#fda4af" stroke-width="1.5"/></g>')
w('<ellipse id="s-floor" cx="200" cy="462" rx="112" ry="13" fill="#1f2937" opacity="0" filter="url(#soft)"/>')

# doll group (everything that tilts / puffs together)
w('<g id="s-doll">')

# cut pattern (dashed cutting line + dimension marks)
w('<g id="s-cut" opacity="0">'
  f'<path id="cut-outline" d="{BODY}" fill="none" stroke="#2563eb" stroke-width="2" stroke-dasharray="9 6" '
  'transform="translate(200 270) scale(1.06) translate(-200 -270)"/>'
  f'<path d="{TAIL}" fill="none" stroke="#2563eb" stroke-width="2" stroke-dasharray="9 6" '
  'transform="translate(296 388) scale(1.12) translate(-296 -388)"/>'
  '<g class="dim" stroke="#2563eb" stroke-width="1.5" fill="none">'
  '<path d="M 44 72 L 44 446"/><path d="M 38 72 L 50 72"/><path d="M 38 446 L 50 446"/>'
  '<path d="M 44 72 L 40 82 M 44 72 L 48 82 M 44 446 L 40 436 M 44 446 L 48 436"/>'
  '<path d="M 82 470 L 320 470"/><path d="M 82 464 L 82 476"/><path d="M 320 464 L 320 476"/></g></g>')

# felt pieces
w('<g id="s-felt" opacity="0" filter="url(#felt)">')
w(f'<path id="f-tail" class="felt-piece" d="{TAIL}" fill="#7c4a1e"/>')
w(f'<path id="f-body" class="felt-piece" d="{BODY}" fill="#f2dfaa"/>')
w('<g id="f-spots" clip-path="url(#clip-body)">')
for k, s_ in enumerate(SPOTS):
    w(f'<path class="felt-piece f-spot" d="{s_}" fill="#6b3f1d"/>')
w('</g>')
w('</g>')

# shading + shine (the "3D" depth)
w(f'<g id="s-shade" opacity="0"><path d="{BODY}" fill="url(#puff)"/>'
  f'<path d="{TAIL}" fill="url(#puff)"/></g>')
w('<g id="s-eyes" opacity="0"><g id="f-eyes" class="felt-piece">')
for e in EYES:
    w(f'<path d="{ellipse_d(*e)}" fill="#ffffff"/>')
for p in PUPILS:
    w(f'<path d="{ellipse_d(*p)}" fill="#1c1917"/>')
w('</g></g>')
w('<g id="s-shine" opacity="0" fill="#fff">'
  '<circle cx="170" cy="201" r="5"/><circle cx="242" cy="201" r="5"/>'
  '<circle cx="159" cy="220" r="2"/><circle cx="231" cy="220" r="2"/></g>')

# stitches (dashed thread, revealed through the mask)
w('<g id="s-stitch" mask="url(#stitch-mask)" fill="none" stroke-linecap="round">')
for d in [BODY, TAIL] + SPOTS:
    w(f'<path d="{d}" stroke="#5b3416" stroke-width="2" stroke-dasharray="5 5"/>')
for e in EYES:
    w(f'<path d="{ellipse_d(*e)}" stroke="#a8a29e" stroke-width="1.6" stroke-dasharray="3 4"/>')
for d in [MOUTH] + WHISKERS + LEGS:
    w(f'<path d="{d}" stroke="#5b3416" stroke-width="2.6"/>')
w('</g>')

# needle + thread tail
w('<g id="s-needle" opacity="0"><g id="needle-body">'
  '<path d="M -16 0 L 14 0" stroke="#9ca3af" stroke-width="2.6" stroke-linecap="round"/>'
  '<ellipse cx="-11" cy="0" rx="3" ry="1.2" fill="none" stroke="#6b7280" stroke-width="1"/>'
  '<path d="M -13 0 C -22 6 -30 -4 -38 4" stroke="#b45309" stroke-width="1.4" fill="none"/></g></g>')

# the child's sketch (on top, fades out later)
w('<g id="s-scribble">')
for clip, d, color, op, sw in scr:
    w(f'<path class="scr" d="{d}" clip-path="url(#{clip})" fill="none" stroke="{color}" '
      f'stroke-opacity="{op}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>')
w('</g>')
w('<g id="s-sketch" filter="url(#crayon)" fill="none" stroke="#3f3f46" stroke-width="3.6" '
  'stroke-linecap="round" stroke-linejoin="round">')
for ident, d in sk:
    idattr = f' id="{ident}"' if ident else ""
    w(f'<path class="sk"{idattr} d="{d}"/>')
w('</g>')

w('</g>')  # s-doll
w('</svg>')
sys.stdout.write("\n".join(L) + "\n")
