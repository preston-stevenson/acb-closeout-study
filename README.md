# Closeouts, beats and help defense, ACB tracking study

How should a defender close out, and what actually happens when he gets beaten? This project answers both from broadcast tracking of 10 Liga ACB 2025-26 games (SkillCorner open data). It builds its own definitions of "beaten" and "help" from player positions and tests them against outcomes.

## Key findings

**1- Getting within 6 feet matters more than anything else, for every type of shooter.** A closeout within 6 ft half a second after the catch:
- cuts three-point attempts by about 40 percentage points
- cuts the catcher's own scoring by about 0.3 points
- cuts points per chance by about 0.2

This holds whether the catcher is a pure shooter, a driver or both. 
I stole some archetypes that PC used when I was a manager, and then grouped players based on drive and shooting tendencies from the 293 games into one of four buckets.
The idea was Rondo -> Korver the distance you close out to before chopping your feet to defend changes depending on the shooter's ability.
Doing 4 names was an easy way to remember numbers and names to quickly decide how to defend player X. 
The tight closeout also triples how often the defender gets beaten, and scoring still goes down.

| Catcher type | Takes a three, tight vs loose | Beaten, tight vs loose | Points per chance, tight vs loose |
|---|---|---|---|
| Korver (shooter) | 19% vs 78% | 19% vs 2% | 0.92 vs 0.66 |
| Lillard (shoot first, drive second) | 27% vs 74% | 36% vs 12% | 0.73 vs 1.32 |
| Westbrook (drive first, shoot second) | 9% vs 50% | 30% vs 10% | 0.48 vs 1.00 |
| Rondo (driver, non-shooter) | 18% vs 58% | 36% vs 8% | 0.68 vs 1.11 |

**2- ACB defenders close out speed does not drastically vary by type.** End distance and speed are the same whether the catcher is a Korver or a Rondo. This is partly because we have a limited dataset, and also, compared to when I was a manager 6 years ago, there are very few guys that can't make an open 3. 

**3- Momentum is what gets defenders beaten.** On drives without a screen, a defender still closing at 5+ ft/s half a second after the catch is beaten 55% of the time, vs 29% for one who has chopped their feet and stayed under control. 

**4- Most blow-bys are covered by help (Shoutout to no def 3 seconds).**
- A second defender is already between the driver and the rim in 78% of blow-bys.
- Two-thirds of blow-bys happen 20+ ft from the rim, where they score no more than an ordinary touch.
- A beat inside 20 ft with no low man obviously works out well, about 1.3 points per chance.

**5- The attack starts about half a second before a defender is visibly beaten.**

**6- Spacing.** Simple spread predicts scoring: the area of the shape the five attackers make, and players beyond the arc, each add about +0.1 points per chance per standard deviation. Zone entropy and floor-control measures don't.

## Validation

I blind labeled 50 tracking examples, including whether there was a guy was beaten, time of blow by where applicable, and close out type.

- **The original beaten rule agreed with my calls 84% of the time** (Cohen's kappa 0.68). SkillCorner's own blowby flag agreed 46% (kappa 0.12). 
- **The moment I marked as "beaten" matched the rule's crossing** to within about 0.05 s. The rule's earlier "attack start" sits about 0.5 s before it.
- **There was a significant difference in average distance to defender on late closeouts** (8.8 ft vs about 5.8 ft half a second after the catch).
- **"Flew out" vs "under control" is still harder to see in recreated clips from the tracking data.** Defenders labeled as flying out were barely slowing on arrival (−1.5 vs −4.9 ft/s²), which points to deceleration as the measure, but it is hard to say whether they got blown by because of a bad closeout, or they are just not a good defender.


## How it works

All positions are in feet with the origin at centre court. Every play is rotated so the offense attacks the same basket (`possessions.leftHoop`).

| Concept | Definition | Code |
|---|---|---|
| Cushion | Attacker's distance to the rim minus his defender's (smoothed). Positive means the defender is in front of the goal. | `geometry.cushion` |
| Beaten | Cushion of −1 ft or worse for 0.2 s with both players on camera (there is a identified flag) | `geometry.crossing` |
| Attack start | Walk back from the crossing while the attacker moves to the rim at 3+ ft/s and faster than his defender | `geometry.attack_start` |
| Closing speed | Defender's velocity toward the catcher 0.5 s after the catch | `geometry.closing_speed` |
| Help | Distance from each other defender to the attacker's line to the rim. "Helper set" means one is goal-side and within 4 ft of that line. | `geometry.help_state` |
| Shooter types | Season three-point volume and accuracy (shrunk toward league average) and drives per game, over 293 games | `players.shooter_types` |

Statistics:
- Least-squares models with game or team controls and robust standard errors, clustered by chance where several snapshots share a possession.
- Fisher exact tests and bootstrap intervals for small comparisons.
- Leave-one-game-out and alternative-threshold checks for robustness.


| Study | Script | Main outputs |
|---|---|---|
| Spacing measures vs outcomes | `studies/spacing.py` | `spacing_chance_points`, `spacing_all_outcomes` |
| Closeout distance and speed | `studies/closeout_distance.py` | `closeout_by_distance`, `closeout_distance_controlled` |
| The beaten rule on every touch | `studies/beaten.py` | `beaten_by_action`, `beaten_timing`, `beaten_momentum` |
| Help after beats | `studies/help.py` | `help_by_location`, `help_by_action`, `help_x_closeout_speed` |
| Closeouts by shooter type | `studies/shooter_types.py` | `types_how_defenders_close`, `types_tight_vs_loose`, `types_pooled` |

## Limitations

- **Ten games.** Points per chance has a standard deviation of 1.27, so a 0.15-point difference needs about 1,100 plays per group. Shot-choice outcomes (threes taken, drives, blow-bys) are far more reliable here than points.
- **One point per player.** Tracking is accurate to about 1 ft on camera and 4–5 ft off camera, with no limbs or hips. Acceleration is noisy.
- **"Beaten" uses rim distance as a stand-in for goal-side position,** which can misjudge baseline drives.
- **Some inputs are SkillCorner model labels:** closeout events, drives and contest levels. A few of their closeouts aren't true closeouts (defender already on the catcher, defense in rotation and "closeout" comes from the side or behind).
- **Not measured:** drive direction (baseline vs middle) and whether a beat was "allowed" into help on purpose.

## Data

Tracking and events: [SkillCorner Open Data, Basketball](https://github.com/SkillCorner/opendata-basketball) (MIT license). Liga ACB 2025-26.
