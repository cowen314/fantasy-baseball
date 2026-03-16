# Fantasy Baseball Draft Prep Tool

A Python-based auction valuation engine for 12-team H2H Categories leagues on ESPN.

## Your League Settings

- **Format:** Head-to-Head Categories, Auction ($260)
- **Teams:** 12
- **Hitting cats:** R, HR, RBI, SB, OBP
- **Pitching cats:** K, W, SV, ERA, WHIP
- **Roster:** C, 1B, 2B, 3B, SS, IF, 3×OF, UTIL, 5×SP, 3×RP, 3×BE, 3×IL

## Quick Start

### 1. Get Projection Data
Download free Steamer projections from FanGraphs:

**Hitters:**
1. Go to https://www.fangraphs.com/projections
2. Select **Steamer** (or ATC for blended projections)
3. Set to **Hitters**, current season
4. Click **Export Data** (CSV download)
5. Save as `inputs/hitters.csv`

**Pitchers:**
1. Same page, switch to **Pitchers**
2. Export and save as `inputs/pitchers.csv`

### 2. Run the Tool

```bash
cd fantasy-baseball
python main.py --hitters inputs/hitters.csv --pitchers inputs/pitchers.csv
```

### 3. Review Outputs

- `output/cheatsheet.csv` — Full ranked list with dollar values and tiers
- `output/hitters_valued.csv` — Detailed hitter breakdown
- `output/pitchers_valued.csv` — Detailed pitcher breakdown
- `output/draft_summary.txt` — Quick reference for draft day

## How It Works

### Valuation Method: Z-Score Auction Dollars

1. **Filter** players by minimum playing time (200 PA hitters, 30 IP pitchers)
2. **Z-score** each category relative to the draftable player pool
   - Counting stats (R, HR, RBI, SB, K, W, SV): standard z-score
   - Rate stats (OBP, ERA, WHIP): marginal value approach weighted by playing time
     so a .400 OBP over 600 PA is worth more than .400 OBP over 200 PA
3. **Sum** z-scores equally across 5 categories for a total value
4. **Convert** to auction dollars:
   - Split budget 67% hitters / 33% pitchers
   - Reserve $1 per roster slot (minimum bid)
   - Distribute remaining $ proportional to z-score share
5. **Tier** players using quantile breaks for quick draft-day reference

### Key Design Decisions

- **OBP over AVG:** Your league uses OBP, so high-walk players get a value boost
  that most generic rankings miss.
- **Marginal rate stats:** A reliever with a 2.50 ERA over 60 IP is less valuable
  to your ERA category than an SP with 3.20 ERA over 180 IP. The marginal approach
  captures this correctly.
- **IF slot flexibility:** The IF slot reduces scarcity at individual infield positions.
  The tool accounts for this in the pool sizing.

## Customization

### CLI Options

```bash
python main.py --hitters data/h.csv --pitchers data/p.csv \
    --min-pa 150          # Lower PA threshold to include more hitters
    --min-ip 20           # Lower IP threshold to include more pitchers
    --hitter-budget-pct 0.70  # Spend 70% on hitters instead of 67%
```

### Config Tweaks
Edit `config.py` to adjust:
- Budget split between hitters/pitchers
- Number of players drafted at each position
- Minimum playing time thresholds
- Column mappings if using non-FanGraphs data sources

---

## Module 2: Lineup Manager

Daily lineup optimization, matchup tracking, and pitching planning.

### Usage

**Basic (start of week, no matchup data):**
```bash
python manage.py --roster-file data/my_roster.txt \
    --hitters data/hitters.csv --pitchers data/pitchers.csv
```

**Mid-week (with matchup data):**
```bash
python manage.py --roster-file data/my_roster.txt \
    --hitters data/hitters.csv --pitchers data/pitchers.csv \
    --my-stats "R=25,HR=8,RBI=22,SB=4,OBP=.285,K=48,W=3,SV=2,ERA=3.15,WHIP=1.12" \
    --opp-stats "R=30,HR=10,RBI=28,SB=2,OBP=.270,K=42,W=2,SV=4,ERA=3.80,WHIP=1.25"
```

### Roster Input
Create a text file with one player name per line:
```
Cal Raleigh
Bobby Witt Jr.
Tarik Skubal
Mason Miller
...
```

### What It Does

1. **Roster Display** — Shows your full roster with positions, dollar values, and projected stats
2. **Start/Sit Recommendations** — Ranks all your players by daily composite score and assigns them to optimal roster slots respecting position eligibility
3. **Matchup Tracker** — Enter your weekly stats and your opponent's to see which categories you're winning/losing, with strategic recommendations
4. **Adaptive Weights** — When matchup data is provided, the lineup optimizer shifts weights to chase categories you're closely losing and deprioritize ones you're safely winning
5. **Pitching Planner** — Rates your SPs by K/start, W/start, and ERA risk. Identifies top streaming candidates from the free agent pool.

### Module Files
- `manage.py` — Main CLI entry point
- `roster.py` — Roster loading, name matching, display
- `lineup.py` — Lineup optimizer with position-aware slot filling
- `matchup.py` — Weekly H2H category tracker and strategy engine
- `pitching.py` — SP analysis, risk classification, streaming candidates
