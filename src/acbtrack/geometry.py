"""Court geometry and the tracking rules.

Coordinates are feet, origin at centre court. A possession's `leftHoop` flag says
which basket the offense attacks: True means the hoop at x = -40.76.
"""
import math

import numpy as np
from scipy.spatial import ConvexHull

from .config import ARC_R, BASELINE_X, CORNER_Y, FPS, HOOP_X, KEY_HALF_W, KEY_LEN


# ---------------------------------------------------------------- basics

def hoop_for(possession):
    """Position of the basket this possession attacks."""
    return np.array([-HOOP_X if possession["leftHoop"] else HOOP_X, 0.0])


def attack_sign(possession):
    """Multiply x and y by this to rotate a play so the offense always attacks x = -40.76."""
    return 1 if possession["leftHoop"] else -1


def smooth(a, k=5):
    """Centred moving average that skips missing values (NaN)."""
    a = np.asarray(a, float)
    out = np.full_like(a, np.nan)
    for i in range(len(a)):
        w = a[max(0, i - k // 2): i + k // 2 + 1]
        w = w[~np.isnan(w)]
        if len(w):
            out[i] = w.mean()
    return out


def segdist(p, a, b):
    """Distance from point p to the segment a-b."""
    p, a, b = (np.asarray(v, float) for v in (p, a, b))
    ab = b - a
    t = np.clip(np.dot(p - a, ab) / max(np.dot(ab, ab), 1e-9), 0, 1)
    return float(np.linalg.norm(p - (a + t * ab)))


def is_three(p, hoop_x=-HOOP_X):
    """Beyond the arc or in a corner (offense attacking hoop_x)."""
    return math.hypot(p[0] - hoop_x, p[1]) >= ARC_R or abs(p[1]) >= CORNER_Y


def in_key(p, hoop):
    sgn = np.sign(hoop[0])
    return abs(p[1]) < KEY_HALF_W and abs(p[0] - sgn * BASELINE_X) < KEY_LEN


# ---------------------------------------------------------------- the beaten rule

def cushion(A, D, hoop):
    """Attacker's distance to the rim minus his defender's, per frame (smoothed).
    Positive: the defender is between his man and the basket."""
    raw = np.linalg.norm(A - hoop, axis=1) - np.linalg.norm(D - hoop, axis=1)
    return smooth(raw)


def rimward_speed(P, hoop):
    """Speed toward the rim (ft/s, smoothed). Positive = moving toward the basket."""
    d = smooth(np.linalg.norm(P - hoop, axis=1))
    return -np.gradient(d) * FPS


def crossing(sm, detected, margin=1.0, frames=5):
    """First frame of the crossing: the cushion stays at -margin ft or worse for `frames`
    consecutive frames with both players seen on camera. Returns None if never beaten.

    margin=1.0, frames=5 (0.2 s) is the rule a former player's labels validated (84% agreement).
    margin=2.0, frames=8 is the stricter variant (agrees less: it misses about half of real beats)."""
    run = 0
    for i in range(len(sm)):
        run = run + 1 if (sm[i] <= -margin and detected[i]) else 0
        if run >= frames:
            j = i - run + 1
            while j > 0 and sm[j - 1] < 0:   # back up to where the cushion first went negative
                j -= 1
            return j
    return None


def attack_start(cross, vA, vD, min_speed=3.0, floor=0):
    """Start of the attack that ends in the crossing: walk back while the attacker moves
    toward the rim at `min_speed`+ ft/s and faster than his defender.
    (Validation: a viewer's 'beaten' moment sits at the crossing, ~0.5 s after this.)"""
    j = cross
    while j > floor and not np.isnan(vA[j - 1]) and vA[j - 1] >= min_speed and vA[j - 1] > vD[j - 1]:
        j -= 1
    return j


def closing_speed(A, D, k, back=3):
    """Defender's velocity toward the attacker at frame k (ft/s), from the last `back` frames."""
    v = (D[k] - D[k - back]) * FPS / back
    u = (A[k] - D[k]) / max(np.linalg.norm(A[k] - D[k]), 1e-6)
    return float(v @ u)


# ---------------------------------------------------------------- help defence

def help_state(attacker, helpers, hoop):
    """Help picture around the ball handler.
    path  : nearest helper's distance to the attacker-to-rim segment (ft)
    near  : nearest helper's distance to the attacker
    inkey : helpers standing in the key
    wall  : helpers closer to the rim than the attacker and within 4 ft of his path"""
    A = np.asarray(attacker, float)
    rimA = np.linalg.norm(A - hoop)
    return dict(
        path=min(segdist(h, A, hoop) for h in helpers),
        near=min(float(np.linalg.norm(h - A)) for h in helpers),
        inkey=sum(1 for h in helpers if in_key(h, hoop)),
        wall=sum(1 for h in helpers if np.linalg.norm(h - hoop) < rimA and segdist(h, A, hoop) < 4),
        rim=float(rimA),
    )


# ---------------------------------------------------------------- spacing (offense attacking -x)

def zone(p, hoop_x=-HOOP_X):
    """Coarse frontcourt zone for entropy."""
    d = math.hypot(p[0] - hoop_x, p[1])
    ang = math.degrees(math.atan2(p[1], p[0] - hoop_x))
    if d > 30:
        return "deep"
    if d < 8 or (abs(p[1]) < KEY_HALF_W and p[0] < hoop_x + KEY_LEN - 5.17):
        return "paint"
    side = "L" if ang > 30 else ("R" if ang < -30 else "M")
    if is_three(p, hoop_x):
        if abs(p[1]) >= CORNER_Y - 1 and p[0] < hoop_x + 10:
            return "c3" + side
        return "w3" + side if side != "M" else "top3"
    return "mid" + side


def hull_area(points):
    return float(ConvexHull(np.asarray(points)).volume)


def frontcourt_grid(step=1.0):
    gx, gy = np.meshgrid(np.arange(-45.4, 0, step), np.arange(-24.1, 24.6, step))
    return np.c_[gx.ravel(), gy.ravel()]


def floor_control(offense, defense, grid, weights=None):
    """Share of grid points nearest to an attacker (optionally weighted by value)."""
    P = np.vstack([offense, defense])
    d = np.hypot(grid[:, None, 0] - P[None, :, 0], grid[:, None, 1] - P[None, :, 1])
    own = d.argmin(1) < len(offense)
    if weights is None:
        return float(own.mean())
    return float((weights * own).sum() / weights.sum())
