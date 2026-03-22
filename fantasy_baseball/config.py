"""
Fantasy Baseball League Configuration
--------------------------------------
12-team H2H Categories, Auction ($260), ESPN
"""

# === League Structure ===
NUM_TEAMS = 12
AUCTION_BUDGET = 260
TOTAL_LEAGUE_BUDGET = NUM_TEAMS * AUCTION_BUDGET  # $3120

# === Roster Slots ===
# Positions and how many starters at each
HITTER_SLOTS = {
    "C": 1,
    "1B": 1,
    "2B": 1,
    "3B": 1,
    "SS": 1,
    "IF": 1,  # any infielder
    "OF": 3,
    "UTIL": 1,  # any hitter
}
PITCHER_SLOTS = {
    "SP": 5,
    "RP": 3,
}
BENCH_SLOTS = 3
IL_SLOTS = 3

TOTAL_HITTER_SLOTS = sum(HITTER_SLOTS.values())  # 10
TOTAL_PITCHER_SLOTS = sum(PITCHER_SLOTS.values())  # 8
TOTAL_STARTER_SLOTS = TOTAL_HITTER_SLOTS + TOTAL_PITCHER_SLOTS  # 18
TOTAL_ROSTER = TOTAL_STARTER_SLOTS + BENCH_SLOTS + IL_SLOTS  # 24

# How many hitters/pitchers drafted league-wide (starters + ~60/40 bench split)
HITTERS_DRAFTED = NUM_TEAMS * (TOTAL_HITTER_SLOTS + 2)  # ~144 (assume 2 bench hitters)
PITCHERS_DRAFTED = NUM_TEAMS * (
    TOTAL_PITCHER_SLOTS + 1
)  # ~108 (assume 1 bench pitcher)

# === Scoring Categories ===
HITTING_CATEGORIES = {
    "R": {"display": "Runs", "type": "counting", "higher_is_better": True},
    "HR": {"display": "Home Runs", "type": "counting", "higher_is_better": True},
    "RBI": {"display": "RBI", "type": "counting", "higher_is_better": True},
    "SB": {"display": "Stolen Bases", "type": "counting", "higher_is_better": True},
    "OBP": {"display": "On-Base Pct", "type": "rate", "higher_is_better": True},
}

PITCHING_CATEGORIES = {
    "K": {"display": "Strikeouts", "type": "counting", "higher_is_better": True},
    "W": {"display": "Wins", "type": "counting", "higher_is_better": True},
    "SV": {"display": "Saves", "type": "counting", "higher_is_better": True},
    "ERA": {"display": "ERA", "type": "rate", "higher_is_better": False},
    "WHIP": {"display": "WHIP", "type": "rate", "higher_is_better": False},
}

# === Budget Split ===
# Standard auction heuristic: ~65-70% on hitters, 30-35% on pitchers
HITTER_BUDGET_PCT = 0.67
PITCHER_BUDGET_PCT = 1 - HITTER_BUDGET_PCT

# Minimum bid per player ($1)
MIN_BID = 1

# === Position Eligibility Mapping ===
# Which positions can fill which roster slots
# (used for positional scarcity calculations)
SLOT_ELIGIBILITY = {
    "C": ["C", "UTIL"],
    "1B": ["1B", "IF", "UTIL"],
    "2B": ["2B", "IF", "UTIL"],
    "3B": ["3B", "IF", "UTIL"],
    "SS": ["SS", "IF", "UTIL"],
    "OF": ["OF", "UTIL"],
    "DH": ["UTIL"],
    "SP": ["SP"],
    "RP": ["RP"],
}

# === FanGraphs CSV Column Mappings ===
# Map our category names to common FanGraphs column headers
FANGRAPHS_HITTER_COLS = {
    "name": "Name",
    "team": "Team",
    "positions": "POS",  # might not exist; we'll handle it
    "PA": "PA",
    "AB": "AB",
    "R": "R",
    "HR": "HR",
    "RBI": "RBI",
    "SB": "SB",
    "OBP": "OBP",
    "H": "H",
    "BB": "BB",
}

FANGRAPHS_PITCHER_COLS = {
    "name": "Name",
    "team": "Team",
    "IP": "IP",
    "K": "SO",  # FanGraphs uses SO for strikeouts
    "W": "W",
    "SV": "SV",
    "ERA": "ERA",
    "WHIP": "WHIP",
    "ER": "ER",
    "H": "H",
    "BB": "BB",
}

# === Minimum Playing Time Thresholds ===
# Filter out players below these thresholds
MIN_PA = 200  # plate appearances for hitters
MIN_IP = 30  # innings pitched for pitchers
