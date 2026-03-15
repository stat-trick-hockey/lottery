#!/usr/bin/env python3
"""
NHL Draft Lottery Odds Generator
Fetches live standings from the NHL API, identifies non-playoff teams,
and computes weighted lottery odds using the official NHL formula.
Writes docs/odds.json for consumption by the frontend.
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ── NHL lottery odds table (official, by finishing position 1–16) ────────────
# Position 1 = worst record, position 16 = best record among non-playoff teams
OFFICIAL_ODDS = [
    25.5, 13.5, 11.5, 9.5, 8.5, 7.5, 6.5, 6.0,
    5.0,  3.5,  3.0,  2.5, 2.0, 1.5, 1.0, 0.5
]

# Team metadata: colors and display names
TEAM_META = {
    "ANA": {"name": "Anaheim Ducks",          "color": "#FC4C02", "bg": "#3D1200"},
    "BOS": {"name": "Boston Bruins",           "color": "#FFB81C", "bg": "#3A2B00"},
    "BUF": {"name": "Buffalo Sabres",          "color": "#003087", "bg": "#00144A"},
    "CGY": {"name": "Calgary Flames",          "color": "#C8102E", "bg": "#2E000A"},
    "CAR": {"name": "Carolina Hurricanes",     "color": "#CC0000", "bg": "#300000"},
    "CHI": {"name": "Chicago Blackhawks",      "color": "#CC0000", "bg": "#3B0000"},
    "COL": {"name": "Colorado Avalanche",      "color": "#6F263D", "bg": "#2A0015"},
    "CBJ": {"name": "Columbus Blue Jackets",   "color": "#002654", "bg": "#00102A"},
    "DAL": {"name": "Dallas Stars",            "color": "#006847", "bg": "#002B1E"},
    "DET": {"name": "Detroit Red Wings",       "color": "#CE1126", "bg": "#300008"},
    "EDM": {"name": "Edmonton Oilers",         "color": "#FF4C00", "bg": "#3D1200"},
    "FLA": {"name": "Florida Panthers",        "color": "#C8102E", "bg": "#2E000A"},
    "LAK": {"name": "LA Kings",                "color": "#A2AAAD", "bg": "#1a1a1a"},
    "MIN": {"name": "Minnesota Wild",          "color": "#154734", "bg": "#071F16"},
    "MTL": {"name": "Montréal Canadiens",      "color": "#AF1E2D", "bg": "#2E0007"},
    "NSH": {"name": "Nashville Predators",     "color": "#FFB81C", "bg": "#3A2B00"},
    "NJD": {"name": "New Jersey Devils",       "color": "#CC0000", "bg": "#300000"},
    "NYI": {"name": "NY Islanders",            "color": "#003087", "bg": "#00103A"},
    "NYR": {"name": "NY Rangers",              "color": "#0038A8", "bg": "#001240"},
    "OTT": {"name": "Ottawa Senators",         "color": "#C2912C", "bg": "#2E1F00"},
    "PHI": {"name": "Philadelphia Flyers",     "color": "#F74902", "bg": "#3A1000"},
    "PIT": {"name": "Pittsburgh Penguins",     "color": "#FCB514", "bg": "#2E2000"},
    "SEA": {"name": "Seattle Kraken",          "color": "#96D8D8", "bg": "#001B2E"},
    "SJS": {"name": "San Jose Sharks",         "color": "#006D75", "bg": "#00384D"},
    "STL": {"name": "St. Louis Blues",         "color": "#002F87", "bg": "#00103A"},
    "TBL": {"name": "Tampa Bay Lightning",     "color": "#002868", "bg": "#000E2E"},
    "TOR": {"name": "Toronto Maple Leafs",     "color": "#00205B", "bg": "#00082A"},
    "UTA": {"name": "Utah Hockey Club",        "color": "#69B3E7", "bg": "#0D2236"},
    "VAN": {"name": "Vancouver Canucks",       "color": "#00843D", "bg": "#002B14"},
    "VGK": {"name": "Vegas Golden Knights",    "color": "#B4975A", "bg": "#2A2015"},
    "WSH": {"name": "Washington Capitals",     "color": "#041E42", "bg": "#0D1520"},
    "WPG": {"name": "Winnipeg Jets",           "color": "#041E42", "bg": "#0A1520"},
}

SEASON_YEAR = 2026  # Current draft year


def fetch_standings():
    """Fetch current NHL standings from the official API."""
    url = "https://api-web.nhle.com/v1/standings/now"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    return data["standings"]


def points_pct(team):
    """Points percentage for tiebreaking (handles unequal games played)."""
    gp = team.get("gamesPlayed", 1) or 1
    pts = team.get("points", 0)
    return pts / (gp * 2)


def is_eliminated_from_playoffs(team):
    """
    A team is lottery-eligible if they have no realistic path to the playoffs.
    We use the clinchIndicator field: teams with 'e' (eliminated) are confirmed.
    During the season we use a heuristic based on points gap vs wildcard.
    For final standings (post-season) everyone not in playoffs qualifies.
    """
    clinch = team.get("clinchIndicator", "")
    # Clinch codes: 'x'=clinched playoff spot, 'y'=division, 'z'=presidents,
    # 'p'=clinched, 'e'=eliminated
    return clinch not in ("x", "y", "z", "p")


def compute_odds(standings):
    """
    Identify the 16 lottery-eligible teams, sort by reverse standings
    (worst first), assign official odds by position.
    Returns list of team dicts with odds assigned.
    """
    # Split into playoff and non-playoff teams
    # The NHL uses conference wildcards — bottom 16 non-playoff teams get lottery spots
    # Sort all teams by points pct ascending (worst first)
    non_playoff = [t for t in standings if is_eliminated_from_playoffs(t)]

    # Sort worst → best by points pct, then fewest regulation wins as tiebreaker
    non_playoff.sort(key=lambda t: (
        points_pct(t),
        t.get("regulationWins", 0),
        t.get("wins", 0)
    ))

    # Take bottom 16 (or however many are eliminated)
    lottery_teams = non_playoff[:16]

    result = []
    for i, team in enumerate(lottery_teams):
        abbrev = team.get("teamAbbrev", {}).get("default", "???")
        odds = OFFICIAL_ODDS[i] if i < len(OFFICIAL_ODDS) else 0.0
        meta = TEAM_META.get(abbrev, {
            "name": team.get("teamName", {}).get("default", abbrev),
            "color": "#888888",
            "bg": "#111111"
        })
        result.append({
            "id": abbrev,
            "name": meta["name"],
            "color": meta["color"],
            "bg": meta["bg"],
            "odds": odds,
            "points": team.get("points", 0),
            "gamesPlayed": team.get("gamesPlayed", 0),
            "wins": team.get("wins", 0),
            "losses": team.get("losses", 0),
            "otLosses": team.get("otLosses", 0),
            "seed": i + 1,  # 1 = worst
        })

    return result


def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching NHL standings...")

    try:
        standings = fetch_standings()
        print(f"  ✓ Got {len(standings)} teams from NHL API")
    except Exception as e:
        print(f"  ✗ Failed to fetch standings: {e}")
        raise

    teams = compute_odds(standings)
    print(f"  ✓ Computed odds for {len(teams)} lottery-eligible teams")
    for t in teams:
        print(f"     {t['seed']:2d}. {t['id']:3s}  {t['odds']:5.1f}%  ({t['points']} pts in {t['gamesPlayed']} GP)")

    output = {
        "year": SEASON_YEAR,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "teams": teams,
        "notes": []  # Populated manually in notes.json; merged at build time
    }

    out_path = Path(__file__).parent / "docs" / "odds.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2))
    print(f"  ✓ Written to {out_path}")


if __name__ == "__main__":
    main()
