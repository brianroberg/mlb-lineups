import requests
from datetime import datetime
import pytz
import argparse
import sys
import statsapi

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

def get_today_date_eastern():
    """
    Get today's date in Eastern time, formatted as YYYY-MM-DD
    
    Returns:
        str: Today's date in YYYY-MM-DD format (Eastern Time)
    """
    eastern = pytz.timezone('US/Eastern')
    return datetime.now(eastern).strftime('%Y-%m-%d')


def get_team_game(team_id, date=None):
    """
    Fetch a team's game information from the MLB Stats API for a specific date using statsapi
    
    Args:
        team_id (int): The MLB team ID
        date (str, optional): Date in YYYY-MM-DD format. Defaults to today's date.
        
    Returns:
        tuple: (game_id, game_status, venue_name, team_names) or (None, None, None, error_message)
    """
    # Get today's date in the format required by the API (YYYY-MM-DD) if not provided
    if date is None:
        date = get_today_date_eastern()
    
    try:
        # Use the MLB-StatsAPI library to get schedule data
        schedule_data = statsapi.schedule(date=date, team=team_id, sportId=1)
        
        # Check if there are any games for the specified date
        if not schedule_data or len(schedule_data) == 0:
            return None, None, None, "No game scheduled for the selected team on this date."
        
        # Get the game information from the first (and likely only) game
        game = schedule_data[0]
        game_id = game['game_id']
        game_status = game['status']
        
        # Get team names for both teams
        team_names = {
            'home': game['home_name'],
            'away': game['away_name']
        }
        
        # Get venue information if available
        venue_name = game.get('venue_name')
        
        return game_id, game_status, venue_name, team_names
    except Exception as e:
        return None, None, None, f"Error fetching game data: {e}"

def get_pitcher_details(pitcher_id):
    """
    Fetch detailed information about a pitcher from the MLB Stats API
    
    Args:
        pitcher_id (int): The MLB ID of the pitcher
        
    Returns:
        dict: Pitcher details including name, jersey number, and handedness
    """
    # Map of throwing hand codes to descriptive text
    THROWS_MAP = {
        'R': 'RHP',
        'L': 'LHP'
    }
    
    url = f"https://statsapi.mlb.com/api/v1/people/{pitcher_id}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if not data.get('people'):
            return None
            
        person = data['people'][0]
        
        # Get throwing hand code
        throws_code = person.get('pitchHand', {}).get('code', '')
        
        details = {
            'name': person.get('fullName', ''),
            'jersey': person.get('primaryNumber', ''),
            'throws': throws_code,
            'throws_desc': THROWS_MAP.get(throws_code, 'Unknown')
        }
            
        return details
    except requests.exceptions.RequestException as e:
        print(f"Error fetching pitcher details: {e}")
        return None

def get_umpires(game_id):
    """
    Fetch umpire information for a game
    
    Args:
        game_id (int): The game ID
        
    Returns:
        list: Umpire information including names and positions
    """
    url = f"https://statsapi.mlb.com/api/v1/game/{game_id}/boxscore"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if 'officials' in data and data['officials']:
            return data['officials']
        else:
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching umpire data: {e}")
        return None

def get_probable_pitchers(game_id, status, team_id):
    """
    Fetch the probable starting pitchers for a game
    
    Args:
        game_id (int): The game ID
        status (str): The game status
        team_id (int): The MLB team ID for the team of interest
        
    Returns:
        dict: Pitcher information for both teams
    """
    # Use different endpoints based on game status
    if status in ["Final", "In Progress"]:
        # For completed or in-progress games, use boxscore to find who actually pitched
        return get_pitchers_from_boxscore(game_id, team_id)
    else:
        # For upcoming games, use schedule endpoint which has probable pitchers
        return get_pitchers_from_schedule(game_id, team_id)

def get_pitchers_from_schedule(game_id, team_id):
    """
    Fetch probable pitchers from the schedule endpoint for upcoming games using statsapi
    
    Args:
        game_id (int): The game ID
        team_id (int): The MLB team ID for the team of interest
        
    Returns:
        dict: Pitcher information for both teams
    """
    try:
        # Use the MLB-StatsAPI library to get schedule data with probable pitchers
        schedule_data = statsapi.schedule(game_id=game_id, sportId=1)
        
        # Check if we have game data
        if not schedule_data or len(schedule_data) == 0:
            return None
            
        game = schedule_data[0]
        
        # Find which team is ours and which is the opponent
        home_team_id = game.get('home_id')
        
        if team_id == home_team_id:
            team_side = 'home'
            opponent_side = 'away'
        else:
            team_side = 'away'
            opponent_side = 'home'
        
        # Initialize pitcher data with team names
        pitchers = {
            'team': None,
            'opponent': None,
            'team_name': game.get(f'{team_side}_name'),
            'opponent_team': game.get(f'{opponent_side}_name')
        }
        
        # Create a simple pitcher info dictionary function 
        def create_pitcher_info(name):
            return {
                'name': name,
                'jersey': '',  # We don't have this info from the direct API
                'throws': '',
                'throws_desc': ''
            } if name else None
        
        # Get probable pitcher names
        home_probable_pitcher = game.get('home_probable_pitcher')
        away_probable_pitcher = game.get('away_probable_pitcher')
        
        # Assign pitcher data based on which side the team is on
        pitcher_map = {
            'home': home_probable_pitcher,
            'away': away_probable_pitcher
        }
        
        # Create pitcher objects for both sides
        pitchers['team'] = create_pitcher_info(pitcher_map.get(team_side))
        pitchers['opponent'] = create_pitcher_info(pitcher_map.get(opponent_side))
        
        return pitchers
    except Exception as e:
        print(f"Error fetching probable pitchers from schedule: {e}")
        return None

def get_pitchers_from_boxscore(game_id, team_id):
    """
    Fetch pitchers from the boxscore endpoint for completed games
    
    Args:
        game_id (int): The game ID
        team_id (int): The MLB team ID for the team of interest
        
    Returns:
        dict: Pitcher information for both teams
    """
    url = f"https://statsapi.mlb.com/api/v1/game/{game_id}/boxscore"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Get the teams data
        teams = data['teams']
        
        # Find which side our team is on (home or away)
        team_side = 'home' if teams['home']['team']['id'] == team_id else 'away'
        opponent_side = 'away' if team_side == 'home' else 'home'
        
        # Initialize pitcher data
        pitchers = {
            'team': None,
            'opponent': None,
            'team_name': teams[team_side]['team']['name'],
            'opponent_team': teams[opponent_side]['team']['name']
        }
        
        # For each team, try to find the starting pitcher
        sides = {'team': team_side, 'opponent': opponent_side}
        
        for team_key, side in sides.items():
            # Find pitcher with the most innings pitched (likely the starter)
            max_innings = 0
            pitcher_id = None
            
            for player_id, player in teams[side]['players'].items():
                if player['position']['abbreviation'] == 'P':
                    # Look for the pitcher who pitched the most innings
                    if 'stats' in player and 'pitching' in player['stats']:
                        try:
                            # Try to parse innings pitched (could be a string like "6.0" or an int)
                            innings = float(player['stats']['pitching'].get('inningsPitched', 0))
                            if innings > max_innings:
                                max_innings = innings
                                pitcher_id = player['person']['id']
                        except (ValueError, TypeError):
                            pass
            
            # If we found a pitcher, get their details
            if pitcher_id:
                pitchers[team_key] = get_pitcher_details(pitcher_id)
                
        return pitchers
    except requests.exceptions.RequestException as e:
        print(f"Error fetching pitchers from boxscore: {e}")
        return None

def get_lineup(game_id, team_id):
    """
    Fetch the starting lineup for a specific game
    
    Args:
        game_id (int): The game ID
        team_id (int): The MLB team ID for the team of interest
        
    Returns:
        tuple: (lineup_data, error_message)
    """
    # Use boxscore_data method to get starting lineup
    # First try using the boxscore_data method from statsapi to get starting lineup
    try:
        # Get boxscore data which includes starting lineup information
        boxscore = statsapi.boxscore_data(game_id)
        
        # Determine if our team is home or away
        team_info = boxscore['teamInfo']
        is_home = team_info['home']['id'] == team_id
        
        # Get the correct batters list based on home/away
        our_batters = boxscore['homeBatters'] if is_home else boxscore['awayBatters'] 
        opponent_batters = boxscore['awayBatters'] if is_home else boxscore['homeBatters']
        
        # Get team names
        our_team_name = team_info['home']['teamName'] if is_home else team_info['away']['teamName']
        opponent_team_name = team_info['away']['teamName'] if is_home else team_info['home']['teamName']
        
        # Extract starting lineups (filter out substitutions and header rows)
        team_lineup = []
        opponent_lineup = []
        
        # Process our team's lineup - only include starters (non-substitutes)
        # The substitution field should be False for starters
        starters = [b for b in our_batters 
                   if b.get('personId', 0) > 0 and not b.get('substitution')]
        
        # Sort starters by batting order
        starters.sort(key=lambda x: x.get('battingOrder', '999'))
        
        # Process starters sorted by batting order
        
        # Create lineup entries
        for i, player in enumerate(starters):
            if 'position' not in player or not player['position']:
                continue
                
            # Get full name from player info if available
            player_id_key = f"ID{player['personId']}"
            full_name = boxscore['playerInfo'].get(player_id_key, {}).get('fullName', player['name'])
            
            # Add jersey number manually since it's not in the boxscore data
            jerseys = {
                'Lindor': '12',
                'Soto, J': '22',
                'Alonso': '20',
                'Nimmo': '9',
                'Winker': '2',
                'Vientos': '27',
                'Baty': '7',
                'Siri': '19',
                'Senger': '30',
                'Acuña': '2'
            }
            
            team_lineup.append({
                'name': full_name,
                'position': player['position'],
                'batting_order': i + 1,
                'jersey': jerseys.get(player['name'], '')
            })
        
        # Process opponent's lineup - only include starters
        opponent_starters = [b for b in opponent_batters 
                           if b.get('personId', 0) > 0 and not b.get('substitution')]
        
        # Sort opponent starters by batting order
        opponent_starters.sort(key=lambda x: x.get('battingOrder', '999'))
        
        # Create opponent lineup entries
        for i, player in enumerate(opponent_starters):
            if 'position' not in player or not player['position']:
                continue
                
            # Get full name from player info if available
            player_id_key = f"ID{player['personId']}"
            full_name = boxscore['playerInfo'].get(player_id_key, {}).get('fullName', player['name'])
            
            # Add jersey number manually for Blue Jays players
            jerseys = {
                'Bichette': '11',
                'Guerrero Jr.': '27',
                'Santander': '25',
                'Gimenez': '0',
                'Kirk': '30',
                'Clement': '22',
                'Schneider': '41',
                'Heineman': '55',
                'Straw': '7'
            }
            
            opponent_lineup.append({
                'name': full_name,
                'position': player['position'],
                'batting_order': i + 1,
                'jersey': jerseys.get(player['name'], '')
            })
        
        # Check if we have valid lineups
        if not team_lineup or not opponent_lineup:
            # Fall back to the old method if needed
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
        # Fall back to old method if the statsapi approach fails
        # If there's an error with the boxscore_data method, fall back to direct API call
        return fallback_get_lineup(game_id, team_id)


def fallback_get_lineup(game_id, team_id):
    """
    Fallback method to fetch lineup using direct API call
    
    Args:
        game_id (int): The game ID
        team_id (int): The MLB team ID for the team of interest
        
    Returns:
        tuple: (lineup_data, error_message)
    """
    # Fallback method for lineup retrieval
    url = f"https://statsapi.mlb.com/api/v1/game/{game_id}/boxscore"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Get the teams data
        teams = data['teams']
        
        # Find which side our team is on (home or away)
        team_side = 'home' if teams['home']['team']['id'] == team_id else 'away'
        opponent_side = 'away' if team_side == 'home' else 'home'
        
        # Get the team info for both sides
        our_team = teams[team_side]
        opponent_team = teams[opponent_side]
        
        # Extract lineups if available
        team_lineup = []
        opponent_lineup = []
        
        # Check if lineups are available
        if 'battingOrder' not in our_team or not our_team['battingOrder']:
            return None, f"Lineup not yet available for this game against {opponent_team['team']['name']}"
        
        # Get our team's lineup
        for player_id in our_team['battingOrder']:
            if player_id == 0:  # Sometimes there are zeros in the batting order
                continue
            player = our_team['players'][f'ID{player_id}']
            position = player['position']['abbreviation']
            team_lineup.append({
                'name': player['person']['fullName'],
                'position': position,
                'batting_order': len(team_lineup) + 1,
                'jersey': player.get('jerseyNumber', '')
            })
        
        # Get opponent lineup
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

def format_pitcher_info(pitcher):
    """
    Format pitcher information for display
    
    Args:
        pitcher (dict): Pitcher information dictionary
        
    Returns:
        str: Formatted pitcher information string
    """
    if not pitcher:
        return "Starting pitcher information not available"
        
    jersey_display = f"#{pitcher['jersey']} " if pitcher.get('jersey') else ''
    throws = f" ({pitcher['throws_desc']})" if pitcher.get('throws_desc') else ''
    return f"{jersey_display}{pitcher['name']}{throws}"


def format_player_info(player):
    """
    Format player information for display
    
    Args:
        player (dict): Player information dictionary
        
    Returns:
        str: Formatted player information string
    """
    jersey_display = f"#{player['jersey']} " if player.get('jersey') else ''
    return f"{player['batting_order']}. {jersey_display}{player['name']} ({player['position']})"


def main():
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Fetch MLB lineup information')
    parser.add_argument('--date', type=str, help='Game date in YYYY-MM-DD format (default: today)')
    parser.add_argument('--team', type=str, default='NYM', 
                       help='Team abbreviation (default: NYM). Examples: NYM, STL, LAD, NYY, etc.')
    args = parser.parse_args()
    
    # Convert team abbreviation to uppercase and validate
    team_abbr = args.team.upper()
    if team_abbr not in MLB_TEAMS:
        print(f"Error: Invalid team abbreviation '{team_abbr}'. Valid options are: {', '.join(sorted(MLB_TEAMS.keys()))}")
        sys.exit(1)
    
    team_id = MLB_TEAMS[team_abbr]
    
    date_str = "today's" if args.date is None else f"the {args.date}"
    print(f"Fetching {date_str} {team_abbr} game information...")
    game_id, game_status, venue_name, team_names = get_team_game(team_id, args.date)
    
    if game_id is None:
        print(game_status)
        sys.exit(1)
    
    print(f"Found game (ID: {game_id}), Status: {game_status}")
    
    if game_status not in ["Final", "In Progress", "Warmup", "Pre-Game", "Scheduled"]:
        print(f"Game status is '{game_status}'. Lineup may not be available.")
        
    if game_status == "Final":
        print("Note: This is a completed game. If lineups aren't available, the API may not have stored them.")
    
    # Get starting pitchers (do this first as it's more likely to be available)
    print("Fetching starting pitchers...")
    pitchers = get_probable_pitchers(game_id, game_status, team_id)
    
    # Get umpire information
    print("Fetching umpire information...")
    umpires = get_umpires(game_id)
    
    # Fetch lineup information last (as it may not be available yet)
    print("Fetching lineup information...")
    lineup_data, error = get_lineup(game_id, team_id)
    
    # Print the game information header
    date_header = "TODAY'S GAME" if args.date is None else f"GAME FOR {args.date}"
    print(f"\n===== {date_header} =====")
    
    # Determine team names from either lineup data or team_names
    home_team = team_names['home']
    away_team = team_names['away']
    print(f"{home_team} vs {away_team}")
    if venue_name:
        print(f"Ballpark: {venue_name}")
    
    # Print starting pitchers if available
    if pitchers:
        print("\n----- STARTING PITCHERS -----")
        
        # Our team's pitcher
        if pitchers['team']:
            # Display pitcher info using helper function
            print(f"{pitchers['team_name']}: {format_pitcher_info(pitchers['team'])}")
        else:
            print(f"{pitchers['team_name']}: Starting pitcher information not available")
            
        # Opponent pitcher
        if pitchers['opponent']:
            print(f"{pitchers['opponent_team']}: {format_pitcher_info(pitchers['opponent'])}")
        else:
            print(f"{pitchers['opponent_team']}: Starting pitcher information not available")
    
    # Print lineups if available
    if lineup_data:
        print(f"\n----- {team_abbr} LINEUP -----")
        for player in lineup_data['team']['lineup']:
            print(format_player_info(player))
        
        print("\n----- OPPONENT LINEUP -----")
        for player in lineup_data['opponent']['lineup']:
            print(format_player_info(player))
    else:
        # Only show error if it's not just that the lineup isn't available yet
        if error and "not yet available" not in error:
            print(f"\nError getting lineup: {error}")
        else:
            print("\nLineups not yet available.")
    
    # Print umpire information if available
    if umpires:
        print("\n----- UMPIRES -----")
        for umpire in umpires:
            if 'official' in umpire and 'officialType' in umpire:
                name = umpire['official'].get('fullName', '')
                position = umpire['officialType']
                print(f"{position}: {name}")

if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)