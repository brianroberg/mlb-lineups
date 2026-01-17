"""MLB Stats API client - all data fetching functions."""

import logging
from datetime import datetime

import pytz
import requests
import statsapi

logger = logging.getLogger(__name__)


def get_today_date_eastern():
    """
    Get today's date in Eastern time, formatted as YYYY-MM-DD.

    Returns:
        str: Today's date in YYYY-MM-DD format (Eastern Time)
    """
    eastern = pytz.timezone('US/Eastern')
    return datetime.now(eastern).strftime('%Y-%m-%d')


def get_team_game(team_id, date=None):
    """
    Fetch a team's game information from the MLB Stats API for a specific date.

    Args:
        team_id (int): The MLB team ID
        date (str, optional): Date in YYYY-MM-DD format. Defaults to today's date.

    Returns:
        tuple: (game_id, game_status, venue_name, team_names, game_time)
               or (None, None, None, None, error_message) on failure
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


def get_player_details(player_id):
    """
    Fetch detailed information about a player from the MLB Stats API.

    Args:
        player_id (int): The MLB ID of the player

    Returns:
        dict: Player details including name and jersey number, or None on failure
    """
    url = f"https://statsapi.mlb.com/api/v1/people/{player_id}"

    try:
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


def get_pitcher_details(pitcher_id):
    """
    Fetch detailed information about a pitcher from the MLB Stats API.

    Args:
        pitcher_id (int): The MLB ID of the pitcher

    Returns:
        dict: Pitcher details including name, jersey number, and handedness,
              or None on failure
    """
    THROWS_MAP = {
        'R': 'RHP',
        'L': 'LHP'
    }

    url = f"https://statsapi.mlb.com/api/v1/people/{pitcher_id}"

    try:
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


def get_umpires(game_id):
    """
    Fetch umpire information for a game.

    Args:
        game_id (int): The game ID

    Returns:
        list: Umpire information including names and positions, or None on failure
    """
    url = f"https://statsapi.mlb.com/api/v1/game/{game_id}/boxscore"

    try:
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


def get_probable_pitchers(game_id, status, team_id):
    """
    Fetch the probable starting pitchers for a game.

    Args:
        game_id (int): The game ID
        status (str): The game status
        team_id (int): The MLB team ID for the team of interest

    Returns:
        dict: Pitcher information for both teams, or None on failure
    """
    if status in ["Final", "In Progress"]:
        return get_pitchers_from_boxscore(game_id, team_id)
    else:
        return get_pitchers_from_schedule(game_id, team_id)


def get_pitchers_from_schedule(game_id, team_id):
    """
    Fetch probable pitchers from the schedule endpoint for upcoming games.

    Args:
        game_id (int): The game ID
        team_id (int): The MLB team ID for the team of interest

    Returns:
        dict: Pitcher information for both teams, or None on failure
    """
    try:
        schedule_data = statsapi.schedule(game_id=game_id, sportId=1)

        if not schedule_data or len(schedule_data) == 0:
            return None

        game = schedule_data[0]
        home_team_id = game.get('home_id')

        if team_id == home_team_id:
            team_side = 'home'
            opponent_side = 'away'
        else:
            team_side = 'away'
            opponent_side = 'home'

        pitchers = {
            'team': None,
            'opponent': None,
            'team_name': game.get(f'{team_side}_name'),
            'opponent_team': game.get(f'{opponent_side}_name')
        }

        def create_pitcher_info(name):
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


def get_pitchers_from_boxscore(game_id, team_id):
    """
    Fetch pitchers from the boxscore endpoint for completed games.

    Args:
        game_id (int): The game ID
        team_id (int): The MLB team ID for the team of interest

    Returns:
        dict: Pitcher information for both teams, or None on failure
    """
    url = f"https://statsapi.mlb.com/api/v1/game/{game_id}/boxscore"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        teams = data['teams']
        team_side = 'home' if teams['home']['team']['id'] == team_id else 'away'
        opponent_side = 'away' if team_side == 'home' else 'home'

        pitchers = {
            'team': None,
            'opponent': None,
            'team_name': teams[team_side]['team']['name'],
            'opponent_team': teams[opponent_side]['team']['name']
        }

        sides = {'team': team_side, 'opponent': opponent_side}

        for team_key, side in sides.items():
            max_innings = 0
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


def get_lineup(game_id, team_id):
    """
    Fetch the starting lineup for a specific game.

    Args:
        game_id (int): The game ID
        team_id (int): The MLB team ID for the team of interest

    Returns:
        tuple: (lineup_data, error_message) where lineup_data is a dict
               or None on failure
    """
    try:
        boxscore = statsapi.boxscore_data(game_id)

        team_info = boxscore['teamInfo']
        is_home = team_info['home']['id'] == team_id

        our_batters = boxscore['homeBatters'] if is_home else boxscore['awayBatters']
        opponent_batters = boxscore['awayBatters'] if is_home else boxscore['homeBatters']

        our_team_name = team_info['home']['teamName'] if is_home else team_info['away']['teamName']
        opponent_team_name = team_info['away']['teamName'] if is_home else team_info['home']['teamName']

        team_lineup = []
        opponent_lineup = []

        starters = [b for b in our_batters
                    if b.get('personId', 0) > 0 and not b.get('substitution')]

        starters.sort(key=lambda x: x.get('battingOrder', '999'))

        for i, player in enumerate(starters):
            if 'position' not in player or not player['position']:
                continue

            player_id_key = f"ID{player['personId']}"
            full_name = boxscore['playerInfo'].get(player_id_key, {}).get('fullName', player['name'])

            player_details = get_player_details(player['personId'])
            jersey_number = player_details.get('jersey', '') if player_details else ''

            team_lineup.append({
                'name': full_name,
                'position': player['position'],
                'batting_order': i + 1,
                'jersey': jersey_number
            })

        opponent_starters = [b for b in opponent_batters
                            if b.get('personId', 0) > 0 and not b.get('substitution')]

        opponent_starters.sort(key=lambda x: x.get('battingOrder', '999'))

        for i, player in enumerate(opponent_starters):
            if 'position' not in player or not player['position']:
                continue

            player_id_key = f"ID{player['personId']}"
            full_name = boxscore['playerInfo'].get(player_id_key, {}).get('fullName', player['name'])

            player_details = get_player_details(player['personId'])
            jersey_number = player_details.get('jersey', '') if player_details else ''

            opponent_lineup.append({
                'name': full_name,
                'position': player['position'],
                'batting_order': i + 1,
                'jersey': jersey_number
            })

        if not team_lineup or not opponent_lineup:
            return fallback_get_lineup(game_id, team_id)

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

    except Exception:
        return fallback_get_lineup(game_id, team_id)


def fallback_get_lineup(game_id, team_id):
    """
    Fallback method to fetch lineup using direct API call.

    Args:
        game_id (int): The game ID
        team_id (int): The MLB team ID for the team of interest

    Returns:
        tuple: (lineup_data, error_message)
    """
    url = f"https://statsapi.mlb.com/api/v1/game/{game_id}/boxscore"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        teams = data['teams']
        team_side = 'home' if teams['home']['team']['id'] == team_id else 'away'
        opponent_side = 'away' if team_side == 'home' else 'home'

        our_team = teams[team_side]
        opponent_team = teams[opponent_side]

        team_lineup = []
        opponent_lineup = []

        if 'battingOrder' not in our_team or not our_team['battingOrder']:
            return None, f"Lineup not yet available for this game against {opponent_team['team']['name']}"

        for player_id in our_team['battingOrder']:
            if player_id == 0:
                continue
            player = our_team['players'][f'ID{player_id}']
            position = player['position']['abbreviation']
            team_lineup.append({
                'name': player['person']['fullName'],
                'position': position,
                'batting_order': len(team_lineup) + 1,
                'jersey': player.get('jerseyNumber', '')
            })

        for player_id in opponent_team['battingOrder']:
            if player_id == 0:
                continue
            player = opponent_team['players'][f'ID{player_id}']
            position = player['position']['abbreviation']
            opponent_lineup.append({
                'name': player['person']['fullName'],
                'position': position,
                'batting_order': len(opponent_lineup) + 1,
                'jersey': player.get('jerseyNumber', '')
            })

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
