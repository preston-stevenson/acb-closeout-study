# Closeouts, beats and help defence: an ACB tracking study

How should a defender close out, and what actually happens when he gets beaten? This project answers both from broadcast tracking of 10 Liga ACB 2025-26 games (SkillCorner open data). It builds its own definitions of "beaten" and "help" from player positions and tests them against outcomes.

## Key findings

**1. Getting there matters more than anything else, for every type of shooter.** A closeout within 6 ft half a second after the catch:
- cuts three-point attempts by about 40 percentage points
- cuts the catcher's own scoring by about 0.3 points
- cuts points per chance by about 0.2

This holds whether the catcher is a pure shooter, a driver or both. The tight closeout also triples how often the defender gets beaten, and scoring still goes down.

| Catcher type | Takes a three, tight vs loose | Beaten, tight vs loose | Points per chance, tight vs loose |
|---|---|---|---|
| Korver (shooter) | 19% vs 78% | 19% vs 2% | 0.92 vs 0.66 |
| Curry (shooter and driver) | 27% vs 74% | 36% vs 12% | 0.73 vs 1.32 |
| Westbrook (driver, decent shooter) | 9% vs 50% | 30% vs 10% | 0.48 vs 1.00 |
| Rondo (driver, weak shooter) | 18% vs 58% | 36% vs 8% | 0.68 vs 1.11 |

**2. ACB defenders don't close out by type.** End distance and speed are the same whether the catcher is a Korver or a Rondo. In this league nearly every heavy driver still takes threes, so "give the driver space" gives away threes.

**3. Momentum is what gets defenders beaten.** On drives without a screen, a defender still closing at 5+ ft/s half a second after the catch is beaten 55% of the time, vs 29% for one who has slowed down. On pick-and-roll drives it makes no difference, because the screen does the work.

**4. Most beats are erased by help.**
- A second defender is already between the driver and the rim in 78% of beats.
- Two-thirds of beats happen 20+ ft from the rim, where they score no more than an ordinary touch.
- A beat inside 20 ft with no helper set is the costly one: about 1.3 points per chance.

**5. The attack starts about half a second before a defender is visibly beaten.**

**6. Spacing.** Simple spread predicts scoring: the area of the shape the five attackers make, and players beyond the arc, each add about +0.1 points per chance per standard deviation. Zone entropy and floor-control measures don't.

## Validation

The tracking rules were checked against blind labels from a former college player on 50 closeout clips, shown without any of the rules' answers.

- **The beaten rule agreed with his calls 84% of the time** (Cohen's kappa 0.68). SkillCorner's own blowby flag agreed 46% (kappa 0.12).
- **The moment he marked as "beaten" matched the rule's crossing** to within about 0.05 s. The rule's earlier "attack start" sits about 0.5 s before it.
- **Distance cleanly separates late closeouts** (8.8 ft vs about 5.8 ft half a second after the catch).
- **"Flew out" vs "under control" is still open.** Defenders labeled as flying out were barely slowing on arrival (−1.5 vs −4.9 ft/s²), which points to deceleration as the measure, but 28 clips aren't enough to confirm it.

The labeling tool isn't part of this repo; the results are summarized here.

## How it works

All positions are in feet with the origin at centre court. Every play is rotated so the offense attacks the same basket (`possessions.leftHoop`).

| Concept | Definition | Code |
|---|---|---|
| Cushion | Attacker's distance to the rim minus his defender's (smoothed). Positive means the defender is goal-side. | `geometry.cushion` |
| Beaten | Cushion of −1 ft or worse for 0.2 s with both players on camera | `geometry.crossing` |
| Attack start | Walk back from the crossing while the attacker moves to the rim at 3+ ft/s and faster than his defender | `geometry.attack_start` |
| Closing speed | Defender's velocity toward the catcher 0.5 s after the catch | `geometry.closing_speed` |
| Help | Distance from each other defender to the attacker's line to the rim. "Helper set" means one is goal-side and within 4 ft of that line. | `geometry.help_state` |
| Shooter types | Season three-point volume and accuracy (shrunk toward league average) and drives per game, over 293 games | `players.shooter_types` |

Statistics:
- Least-squares models with game or team controls and robust standard errors, clustered by chance where several snapshots share a possession.
- Fisher exact tests and bootstrap intervals for small comparisons.
- Leave-one-game-out and alternative-threshold checks for robustness.

## Layout

```
src/acbtrack/        shared code: config, file reading, geometry and rules, player types, stats helpers
scripts/             download the tracking, then build cached tables in one pass each
studies/             one script per study; each writes tables to results/
pages/               builders and templates for the two interactive replay pages
results/             tables from the last run (CSV and Markdown)
```

## Running it

Python 3.10+.

```bash
pip install -r requirements.txt
git clone --depth 1 https://github.com/SkillCorner/opendata-basketball   # GIT_LFS_SKIP_SMUDGE=1 to skip the large files
./run_all.sh
```

`run_all.sh`:
1. downloads the 10 tracking files (~360 MB)
2. builds the caches (about 5 minutes)
3. runs the five studies
4. builds the two pages into `pages/out/`

Paths can be changed with `ACB_DATA`, `ACB_TRACKING`, `ACB_CACHE` and `ACB_RESULTS` (see `src/acbtrack/config.py`).

| Study | Script | Main outputs |
|---|---|---|
| Spacing measures vs outcomes | `studies/spacing.py` | `spacing_chance_points`, `spacing_all_outcomes` |
| Closeout distance and speed | `studies/closeout_distance.py` | `closeout_by_distance`, `closeout_distance_controlled` |
| The beaten rule on every touch | `studies/beaten.py` | `beaten_by_action`, `beaten_timing`, `beaten_momentum` |
| Help after beats | `studies/help.py` | `help_by_location`, `help_by_action`, `help_x_closeout_speed` |
| Closeouts by shooter type | `studies/shooter_types.py` | `types_how_defenders_close`, `types_tight_vs_loose`, `types_pooled` |

## Limitations

- **Ten games.** Points per chance has a standard deviation of 1.27, so a 0.15-point difference needs about 1,100 plays per group. Shot-choice outcomes (threes taken, drives, beats) are far more reliable here than points.
- **One point per player.** Tracking is accurate to about 1 ft on camera and 4–5 ft off camera, with no limbs or hips. Acceleration is noisy.
- **"Beaten" uses rim distance as a stand-in for goal-side position,** which can misjudge baseline drives.
- **Some inputs are SkillCorner model labels:** closeout events, drives and contest levels. A few of their closeouts aren't true closeouts (rotations, a defender already on the catcher).
- **Not measured:** drive direction (baseline vs middle) and whether a beat was "allowed" into help on purpose.

## Data

Tracking and events: [SkillCorner Open Data, Basketball](https://github.com/SkillCorner/opendata-basketball) (MIT licence). Liga ACB 2025-26.
