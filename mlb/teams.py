"""MLB team constants and validation utilities."""

# MLB team abbreviations to team IDs mapping
MLB_TEAMS = {
    "ARI": 109,  # Arizona Diamondbacks
    "ATL": 144,  # Atlanta Braves
    "BAL": 110,  # Baltimore Orioles
    "BOS": 111,  # Boston Red Sox
    "CHC": 112,  # Chicago Cubs
    "CIN": 113,  # Cincinnati Reds
    "CLE": 114,  # Cleveland Guardians
    "COL": 115,  # Colorado Rockies
    "CWS": 145,  # Chicago White Sox
    "DET": 116,  # Detroit Tigers
    "HOU": 117,  # Houston Astros
    "KC": 118,   # Kansas City Royals
    "LAA": 108,  # Los Angeles Angels
    "LAD": 119,  # Los Angeles Dodgers
    "MIA": 146,  # Miami Marlins
    "MIL": 158,  # Milwaukee Brewers
    "MIN": 142,  # Minnesota Twins
    "NYM": 121,  # New York Mets
    "NYY": 147,  # New York Yankees
    "OAK": 133,  # Oakland Athletics
    "PHI": 143,  # Philadelphia Phillies
    "PIT": 134,  # Pittsburgh Pirates
    "SD": 135,   # San Diego Padres
    "SEA": 136,  # Seattle Mariners
    "SF": 137,   # San Francisco Giants
    "STL": 138,  # St. Louis Cardinals
    "TB": 139,   # Tampa Bay Rays
    "TEX": 140,  # Texas Rangers
    "TOR": 141,  # Toronto Blue Jays
    "WSH": 120,  # Washington Nationals
}


def is_valid_team(abbr: str) -> bool:
    """
    Check if a team abbreviation is valid.

    Args:
        abbr: Team abbreviation (e.g., 'NYM', 'LAD')

    Returns:
        True if valid, False otherwise
    """
    return abbr.upper() in MLB_TEAMS


def get_team_id(abbr: str) -> int | None:
    """
    Get the MLB team ID from an abbreviation.

    Args:
        abbr: Team abbreviation (e.g., 'NYM', 'LAD')

    Returns:
        Team ID if valid, None otherwise
    """
    return MLB_TEAMS.get(abbr.upper())
