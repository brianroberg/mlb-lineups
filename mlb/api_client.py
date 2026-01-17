"""MLB Stats API client - all data fetching functions."""

import logging
from datetime import datetime
from typing import Any

import pytz
import requests
import statsapi

from mlb.cache import cached, get_ttl_for_game_status, rate_limiter

logger = logging.getLogger(__name__)

# Pitcher handedness mapping
THROWS_MAP: dict[str, str] = {
    'R': 'RHP',
    'L': 'LHP',
}


def get_today_date_eastern() -> str:
    """
    Get today's date in Eastern time, formatted as YYYY-MM-DD.

    Returns:
        Today's date in YYYY-MM-DD format (Eastern Time)
    """
    eastern = pytz.timezone('US/Eastern')
    return datetime.now(eastern).strftime('%Y-%m-%d')


@cached(lambda team_id, date=None: get_ttl_for_game_status('Scheduled'))
def get_team_game(
    team_id: int,
    date: str | None = None
) -> tuple[int | None, str | None, str | None, dict[str, str] | None, str]:
    """
    Fetch a team's game information from the MLB Stats API for a specific date.

    Args:
        team_id: The MLB team ID
        date: Date in YYYY-MM-DD format. Defaults to today's date.

    Returns:
        Tuple of (game_id, game_status, venue_name, team_names, game_time_or_error)
        Returns (None, None, None, None, error_message) on failure
    """
    if date is None:
        date = get_today_date_eastern()

    try:
        schedule_data = statsapi.schedule(date=date, team=team_id, sportId=1)

        if not schedule_data or len(schedule_data) == 0:
            return None, None, None, None, "No game scheduled for the selected team on this date."

        game = schedule_data[0]
        game_id = game['game_id']
        game_status = game['status']

        team_names = {
            'home': game['home_name'],
            'away': game['away_name']
        }

        venue_name = game.get('venue_name')
        game_time = game.get('game_datetime', '')

        return game_id, game_status, venue_name, team_names, game_time
    except Exception as e:
        logger.error(f"Error fetching game data: {e}")
        return None, None, None, None, f"Error fetching game data: {e}"


@cached(86400)  # 24 hours - player data rarely changes
def get_player_details(player_id: int) -> dict[str, str] | None:
    """
    Fetch detailed information about a player from the MLB Stats API.

    Args:
        player_id: The MLB ID of the player

    Returns:
        Player details including name and jersey number, or None on failure
    """
    url = f"https://statsapi.mlb.com/api/v1/people/{player_id}"

    try:
        rate_limiter.acquire()
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get('people'):
            return None

        person = data['people'][0]

        details = {
            'name': person.get('fullName', ''),
            'jersey': person.get('primaryNumber', '')
        }

        return details
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching player details: {e}")
        return None


@cached(86400)  # 24 hours - pitcher data rarely changes
def get_pitcher_details(pitcher_id: int) -> dict[str, str] | None:
    """
    Fetch detailed information about a pitcher from the MLB Stats API.

    Args:
        pitcher_id: The MLB ID of the pitcher

    Returns:
        Pitcher details including name, jersey number, and handedness,
        or None on failure
    """
    url = f"https://statsapi.mlb.com/api/v1/people/{pitcher_id}"

    try:
        rate_limiter.acquire()
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get('people'):
            return None

        person = data['people'][0]
        throws_code = person.get('pitchHand', {}).get('code', '')

        details = {
            'name': person.get('fullName', ''),
            'jersey': person.get('primaryNumber', ''),
            'throws': throws_code,
            'throws_desc': THROWS_MAP.get(throws_code, 'Unknown')
        }

        return details
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching pitcher details: {e}")
        return None


@cached(lambda game_id: get_ttl_for_game_status('Scheduled'))
def get_umpires(game_id: int) -> list[dict[str, Any]] | None:
    """
    Fetch umpire information for a game.

    Args:
        game_id: The game ID

    Returns:
        Umpire information including names and positions, or None on failure
    """
    url = f"https://statsapi.mlb.com/api/v1/game/{game_id}/boxscore"

    try:
        rate_limiter.acquire()
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if 'officials' in data and data['officials']:
            return data['officials']
        else:
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching umpire data: {e}")
        return None


@cached(lambda game_id, status, team_id: get_ttl_for_game_status(status))
def get_probable_pitchers(
    game_id: int,
    status: str,
    team_id: int
) -> dict[str, Any] | None:
    """
    Fetch the probable starting pitchers for a game.

    Args:
        game_id: The game ID
        status: The game status
        team_id: The MLB team ID for the team of interest

    Returns:
        Pitcher information for both teams, or None on failure
    """
    if status in ["Final", "In Progress", "Game Over"]:
        return get_pitchers_from_boxscore(game_id, team_id)
    else:
        return get_pitchers_from_schedule(game_id, team_id)


def get_pitchers_from_schedule(
    game_id: int,
    team_id: int
) -> dict[str, Any] | None:
    """
    Fetch probable pitchers from the schedule endpoint for upcoming games.

    Args:
        game_id: The game ID
        team_id: The MLB team ID for the team of interest

    Returns:
        Pitcher information for both teams, or None on failure
    """
    try:
        schedule_data = statsapi.schedule(game_id=game_id, sportId=1)

        if not schedule_data or len(schedule_data) == 0:
            return None

        game = schedule_data[0]
        home_team_id = game.get('home_id')

        team_side, opponent_side = _determine_team_sides(team_id, home_team_id)

        pitchers: dict[str, Any] = {
            'team': None,
            'opponent': None,
            'team_name': game.get(f'{team_side}_name'),
            'opponent_team': game.get(f'{opponent_side}_name')
        }

        def create_pitcher_info(name: str | None) -> dict[str, str] | None:
            return {
                'name': name,
                'jersey': '',
                'throws': '',
                'throws_desc': ''
            } if name else None

        home_probable_pitcher = game.get('home_probable_pitcher')
        away_probable_pitcher = game.get('away_probable_pitcher')

        pitcher_map = {
            'home': home_probable_pitcher,
            'away': away_probable_pitcher
        }

        pitchers['team'] = create_pitcher_info(pitcher_map.get(team_side))
        pitchers['opponent'] = create_pitcher_info(pitcher_map.get(opponent_side))

        return pitchers
    except Exception as e:
        logger.error(f"Error fetching probable pitchers from schedule: {e}")
        return None


def get_pitchers_from_boxscore(
    game_id: int,
    team_id: int
) -> dict[str, Any] | None:
    """
    Fetch pitchers from the boxscore endpoint for completed games.

    Args:
        game_id: The game ID
        team_id: The MLB team ID for the team of interest

    Returns:
        Pitcher information for both teams, or None on failure
    """
    url = f"https://statsapi.mlb.com/api/v1/game/{game_id}/boxscore"

    try:
        rate_limiter.acquire()
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        teams = data['teams']
        home_team_id = teams['home']['team']['id']
        team_side, opponent_side = _determine_team_sides(team_id, home_team_id)

        pitchers: dict[str, Any] = {
            'team': None,
            'opponent': None,
            'team_name': teams[team_side]['team']['name'],
            'opponent_team': teams[opponent_side]['team']['name']
        }

        sides = {'team': team_side, 'opponent': opponent_side}

        for team_key, side in sides.items():
            max_innings = 0.0
            pitcher_id = None

            for player_id, player in teams[side]['players'].items():
                if player['position']['abbreviation'] == 'P':
                    if 'stats' in player and 'pitching' in player['stats']:
                        try:
                            innings = float(player['stats']['pitching'].get('inningsPitched', 0))
                            if innings > max_innings:
                                max_innings = innings
                                pitcher_id = player['person']['id']
                        except (ValueError, TypeError):
                            pass

            if pitcher_id:
                pitchers[team_key] = get_pitcher_details(pitcher_id)

        return pitchers
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching pitchers from boxscore: {e}")
        return None


def _determine_team_sides(
    team_id: int,
    home_team_id: int
) -> tuple[str, str]:
    """
    Determine which side (home/away) the team is on.

    Args:
        team_id: The team ID to check
        home_team_id: The home team's ID

    Returns:
        Tuple of (team_side, opponent_side) - each is 'home' or 'away'
    """
    if team_id == home_team_id:
        return 'home', 'away'
    return 'away', 'home'


@cached(lambda game_id, team_id: get_ttl_for_game_status('Scheduled'))
def get_lineup(
    game_id: int,
    team_id: int
) -> tuple[dict[str, Any] | None, str | None]:
    """
    Fetch the starting lineup for a specific game with automatic fallback.

    Tries statsapi first, falls back to direct HTTP if needed.

    Args:
        game_id: The game ID
        team_id: The MLB team ID for the team of interest

    Returns:
        Tuple of (lineup_data dict, error_message) or (None, error) on failure
    """
    # Try primary method
    lineup, error = _fetch_lineup_statsapi(game_id, team_id)
    if lineup:
        return lineup, None

    # Fallback to direct API
    return _fetch_lineup_direct(game_id, team_id)


def _fetch_lineup_statsapi(
    game_id: int,
    team_id: int
) -> tuple[dict[str, Any] | None, str | None]:
    """
    Fetch lineup using statsapi library (primary method).

    Args:
        game_id: The game ID
        team_id: The MLB team ID for the team of interest

    Returns:
        Tuple of (lineup_data, error_message)
    """
    try:
        boxscore = statsapi.boxscore_data(game_id)

        team_info = boxscore['teamInfo']
        home_team_id = team_info['home']['id']
        team_side, opponent_side = _determine_team_sides(team_id, home_team_id)

        our_batters = boxscore[f'{team_side}Batters']
        opponent_batters = boxscore[f'{opponent_side}Batters']

        our_team_name = team_info[team_side]['teamName']
        opponent_team_name = team_info[opponent_side]['teamName']

        # Build lineups using shared helper
        team_lineup = _build_lineup_from_statsapi_batters(our_batters, boxscore)
        opponent_lineup = _build_lineup_from_statsapi_batters(opponent_batters, boxscore)

        if not team_lineup or not opponent_lineup:
            return None, "Incomplete lineup data"

        return {
            'team': {
                'name': our_team_name,
                'lineup': team_lineup
            },
            'opponent': {
                'team': opponent_team_name,
                'lineup': opponent_lineup
            }
        }, None

    except Exception as e:
        logger.debug(f"statsapi lineup fetch failed: {e}")
        return None, str(e)


def _fetch_lineup_direct(
    game_id: int,
    team_id: int
) -> tuple[dict[str, Any] | None, str | None]:
    """
    Fetch lineup using direct HTTP API (fallback method).

    Args:
        game_id: The game ID
        team_id: The MLB team ID for the team of interest

    Returns:
        Tuple of (lineup_data, error_message)
    """
    url = f"https://statsapi.mlb.com/api/v1/game/{game_id}/boxscore"

    try:
        rate_limiter.acquire()
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        teams = data['teams']
        home_team_id = teams['home']['team']['id']
        team_side, opponent_side = _determine_team_sides(team_id, home_team_id)

        our_team = teams[team_side]
        opponent_team = teams[opponent_side]

        if 'battingOrder' not in our_team or not our_team['battingOrder']:
            return None, f"Lineup not yet available for this game against {opponent_team['team']['name']}"

        team_lineup = _build_lineup_from_batting_order(our_team)
        opponent_lineup = _build_lineup_from_batting_order(opponent_team)

        return {
            'team': {
                'name': our_team['team']['name'],
                'lineup': team_lineup
            },
            'opponent': {
                'team': opponent_team['team']['name'],
                'lineup': opponent_lineup
            }
        }, None

    except requests.exceptions.RequestException as e:
        return None, f"Error fetching lineup data: {e}"
    except KeyError as e:
        return None, f"Lineup data not available yet: {e}"


def _build_lineup_from_statsapi_batters(
    batters: list[dict[str, Any]],
    boxscore: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Build lineup list from batters data (statsapi format).

    Args:
        batters: List of batter dictionaries from statsapi
        boxscore: Full boxscore data for player info lookup

    Returns:
        List of player dictionaries with name, position, batting_order, jersey
    """
    lineup: list[dict[str, Any]] = []

    # Filter and sort starters
    starters = [
        b for b in batters
        if b.get('personId', 0) > 0 and not b.get('substitution')
    ]
    starters.sort(key=lambda x: x.get('battingOrder', '999'))

    for i, player in enumerate(starters):
        if 'position' not in player or not player['position']:
            continue

        player_id_key = f"ID{player['personId']}"
        full_name = boxscore['playerInfo'].get(player_id_key, {}).get(
            'fullName', player['name']
        )

        # Fetch detailed player info for jersey number
        player_details = get_player_details(player['personId'])
        jersey_number = player_details.get('jersey', '') if player_details else ''

        lineup.append({
            'name': full_name,
            'position': player['position'],
            'batting_order': i + 1,
            'jersey': jersey_number
        })

    return lineup


def _build_lineup_from_batting_order(
    team_data: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Build lineup list from battingOrder data (direct API format).

    Args:
        team_data: Team data dictionary containing battingOrder and players

    Returns:
        List of player dictionaries with name, position, batting_order, jersey
    """
    lineup: list[dict[str, Any]] = []

    for player_id in team_data['battingOrder']:
        if player_id == 0:
            continue

        player = team_data['players'][f'ID{player_id}']
        position = player['position']['abbreviation']

        lineup.append({
            'name': player['person']['fullName'],
            'position': position,
            'batting_order': len(lineup) + 1,
            'jersey': player.get('jerseyNumber', '')
        })

    return lineup
