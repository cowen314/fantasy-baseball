# Fantasy Baseball Management System

A Python toolkit for drafting and managing a fantasy baseball team in a 12-team H2H Categories league on ESPN. Built to reduce the daily time commitment of running a competitive team.

## League Settings

| Setting | Value |
|---|---|
| Platform | ESPN |
| Format | Head-to-Head Categories |
| Draft | Auction ($260) |
| Teams | 12 |
| Hitting | R, HR, RBI, SB, OBP |
| Pitching | K, W, SV, ERA, WHIP |
| Roster | C, 1B, 2B, 3B, SS, IF, 3×OF, UTIL, 5×SP, 3×RP, 3×BE, 3×IL |

## Getting Started

### 1. Download Projections

Go to [FanGraphs Projections](https://www.fangraphs.com/projections), select Steamer or ATC, and export CSVs for both hitters and pitchers. Save them as `inputs/hitters.csv` and `inputs/pitchers.csv`.

### 2. Generate Your Draft Cheat Sheet

```bash
python draft.py --hitters inputs/hitters.csv --pitchers inputs/pitchers.csv
```

This outputs auction dollar values, tiered rankings, and positional breakdowns into the `output/` directory.

### 3. Manage Your Team During the Season

```bash
python manage.py --roster-file inputs/my_roster.txt \
    --hitters inputs/hitters.csv --pitchers inputs/pitchers.csv \
    --injuries inputs/injuries.json
```

---

## Module 1: Draft Prep

**Entry point:** `draft.py`

Converts raw FanGraphs projections into auction dollar values calibrated to your league.

### How the Valuation Works

Player values are computed using z-scores across all 10 categories. Counting stats (R, HR, RBI, SB, K, W, SV) use standard z-scores. Rate stats (OBP, ERA, WHIP) use a marginal value approach weighted by playing time — a .400 OBP over 600 PA contributes more to your team's OBP than .400 over 200 PA, and the model accounts for that.

Z-scores are converted to auction dollars by splitting the league budget 67/33 between hitters and pitchers, reserving $1 per roster slot as a minimum bid, and distributing the rest proportionally. Players are assigned to tiers using quantile breaks.

Position eligibility is mapped via MLBAMID lookup (333/333 draftable hitters covered). The IF slot reduces infield scarcity, and the model accounts for this in pool sizing.

### Outputs

| File | Description |
|---|---|
| `output/cheatsheet.csv` | Full ranked list with dollar values, tiers, z-scores, and category strengths |
| `output/hitters_valued.csv` | Detailed hitter valuations |
| `output/pitchers_valued.csv` | Detailed pitcher valuations |
| `output/draft_summary.txt` | Quick reference with top players by position and budget strategy |
| `output/auction_board.txt` | Searchable draft board grouped by dollar value |

### CLI Options

```bash
python draft.py --hitters inputs/hitters.csv --pitchers inputs/pitchers.csv \
    --min-pa 150              # Lower PA threshold (default 200)
    --min-ip 20               # Lower IP threshold (default 30)
    --hitter-budget-pct 0.70  # Adjust budget split (default 0.67)
    --output output_dir       # Custom output directory
```

### Key Files

| File | Purpose |
|---|---|
| `config.py` | League settings, roster slots, categories, column mappings |
| `valuations.py` | Z-score engine, dollar conversion, tier assignment |
| `positions.py` | MLBAMID-to-position lookup (ESPN eligibility) |
| `draft.py` | CLI entry point for draft prep |
| `generate_sample_data.py` | Creates fake projection data for testing |

---

## Module 2: Lineup Manager

**Entry point:** `manage.py`

Daily lineup optimization, weekly matchup tracking, pitching planning, and injury awareness.

### Daily Workflow

**Start of week (no matchup data yet):**
```bash
python manage.py --roster-file inputs/my_roster.txt \
    --hitters inputs/hitters.csv --pitchers inputs/pitchers.csv \
    --injuries inputs/injuries.json
```

**Mid-week (with current matchup stats):**
```bash
python manage.py --roster-file inputs/my_roster.txt \
    --hitters inputs/hitters.csv --pitchers inputs/pitchers.csv \
    --injuries inputs/injuries.json \
    --my-stats "R=25,HR=8,RBI=22,SB=4,OBP=.285,K=48,W=3,SV=2,ERA=3.15,WHIP=1.12" \
    --opp-stats "R=30,HR=10,RBI=28,SB=2,OBP=.270,K=42,W=2,SV=4,ERA=3.80,WHIP=1.25"
```

### Roster Input

Create `inputs/my_roster.txt` with one player per line. The parser handles position prefixes, team abbreviations, numbered lists, and accented characters.

```
Cal Raleigh
Bobby Witt Jr.
Jose Altuve
Tarik Skubal
Mason Miller
```

### Features

**Start/Sit Optimizer** — Scores every player using per-game rates, then assigns them to roster slots with a constrained-first algorithm (fills C before UTIL, SS before IF) so positional eligibility is always respected.

**Matchup Tracker** — Enter your weekly stats and your opponent's to see a category-by-category scoreboard. The strategy engine classifies each category:
- CHASE: losing by a small margin (still flippable)
- HOLD: slim lead worth protecting
- SAFE: comfortable lead, can deprioritize
- PUNT: too far behind to realistically catch up

**Adaptive Lineup Weights** — When matchup data is provided, category weights shift automatically and the lineup reshuffles. Chasing HR and R? Power hitters get bumped up. Saves locked in? RP contributions deprioritized.

**Pitching Planner** — Rates your SP staff by K/start, W/start, and ERA risk tier (Elite through Sit). Shows the top streaming candidates from the free agent pool.

**Injury Integration** — IL players are excluded from lineup recommendations. DTD and OUT players stay eligible but get flagged with warnings. Full injury report shows status, return date, and details for affected roster players.

### Key Files

| File | Purpose |
|---|---|
| `manage.py` | CLI entry point for daily management |
| `roster.py` | Roster loading, fuzzy name matching, display |
| `lineup.py` | Lineup optimizer with position-aware slot filling |
| `matchup.py` | Weekly H2H category tracker and strategy engine |
| `pitching.py` | SP analysis, risk tiers, streaming candidates |
| `injuries.py` | Injury data parsing, roster matching, display |

---

## Injury Tracking

**Entry point:** `fetch_injuries.py` (run locally with internet access)

Three data sources, in priority order:

1. **MLB Stats API** — `fetch_injuries.py` pulls recent IL transactions and filters out players who were subsequently activated.
2. **ESPN** — Richer data with status classifications, estimated return dates, and comments. Requires `beautifulsoup4`.
3. **Manual** — Edit `inputs/injuries.json` directly. The format is simple and documented.

A pre-seeded snapshot with ~27 injuries (current as of mid-March 2026) is included.

### Refreshing Injury Data

```bash
python fetch_injuries.py --source mlb    # MLB Stats API
python fetch_injuries.py --source espn   # ESPN (requires beautifulsoup4)
python fetch_injuries.py --source both   # Merged from both
```

---

## Customization

**`config.py`** — All league-specific settings: teams, budget, roster slots, scoring categories, budget split, playing time thresholds, and FanGraphs column mappings. This is the only file you need to edit to adapt the system for a different league.

**`positions.py`** — MLBAMID-to-position map covering all draftable hitters. Add or correct entries by editing the `POSITION_MAP` dictionary.

---

## Project Roadmap

- [x] Module 1: Draft Prep — Auction valuations and cheat sheet
- [x] Module 2: Lineup Manager — Daily optimization, matchup tracking, pitching planner
- [x] Injury Tracking — MLB Stats API + ESPN integration, roster flagging
- [ ] Module 3: Waiver Wire — Free agent recommendations based on category needs
- [ ] Module 4: Trade Evaluator — Analyze trades against category strengths and weaknesses