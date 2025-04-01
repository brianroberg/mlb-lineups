import requests
from datetime import datetime
import pytz
import argparse
import sys

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

def get_team_game(team_id, date=None):
    """
    Fetch a team's game information from the MLB Stats API for a specific date
    
    Args:
        team_id (int): The MLB team ID
        date (str, optional): Date in YYYY-MM-DD format. Defaults to today's date.
    """
    # Get today's date in the format required by the API (YYYY-MM-DD) if not provided
    if date is None:
        eastern = pytz.timezone('US/Eastern')
        date = datetime.now(eastern).strftime('%Y-%m-%d')
    
    # MLB Stats API endpoint for the schedule with venue information
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date}&teamId={team_id}&hydrate=venue"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Check if there are any games for the specified date
        if data['totalGames'] == 0:
            return None, None, None, "No game scheduled for the selected team on this date."
        
        # Get the game information from the first (and likely only) game
        game = data['dates'][0]['games'][0]
        game_id = game['gamePk']
        game_status = game['status']['detailedState']
        
        # Get team names for both teams
        home_team = game['teams']['home']['team']['name']
        away_team = game['teams']['away']['team']['name']
        team_names = {'home': home_team, 'away': away_team}
        
        # Get venue information if available
        venue_name = None
        if 'venue' in game and 'name' in game['venue']:
            venue_name = game['venue']['name']
        
        return game_id, game_status, venue_name, team_names
    except requests.exceptions.RequestException as e:
        return None, None, None, f"Error fetching game data: {e}"

def get_pitcher_details(pitcher_id):
    """
    Fetch detailed information about a pitcher from the MLB Stats API
    
    Args:
        pitcher_id (int): The MLB ID of the pitcher
        
    Returns:
        dict: Pitcher details including name, jersey number, and handedness
    """
    url = f"https://statsapi.mlb.com/api/v1/people/{pitcher_id}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if not data.get('people'):
            return None
            
        person = data['people'][0]
        details = {
            'name': person.get('fullName', ''),
            'jersey': person.get('primaryNumber', ''),
            'throws': person.get('pitchHand', {}).get('code', '')
        }
        
        # Expand throws code to descriptive text
        if details['throws'] == 'R':
            details['throws_desc'] = 'RHP'
        elif details['throws'] == 'L':
            details['throws_desc'] = 'LHP'
        else:
            details['throws_desc'] = 'Unknown'
            
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
    # For completed games, we need to check the boxscore
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
                    # If game is completed, look for the pitcher who pitched
                    if status in ["Final", "In Progress"] and 'stats' in player and 'pitching' in player['stats']:
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
        print(f"Error fetching probable pitchers: {e}")
        return None

def get_lineup(game_id, team_id):
    """
    Fetch the starting lineup for a specific game
    
    Args:
        game_id (int): The game ID
        team_id (int): The MLB team ID for the team of interest
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
    
    print("Fetching lineup information...")
    lineup_data, error = get_lineup(game_id, team_id)
    
    if error:
        print(error)
        sys.exit(1)
    
    # Get starting pitchers
    print("Fetching starting pitchers...")
    pitchers = get_probable_pitchers(game_id, game_status, team_id)
    
    # Get umpire information
    print("Fetching umpire information...")
    umpires = get_umpires(game_id)
    
    # Print the lineups
    date_header = "TODAY'S GAME" if args.date is None else f"GAME FOR {args.date}"
    print(f"\n===== {date_header} =====")
    print(f"{lineup_data['team']['name']} vs {lineup_data['opponent']['team']}")
    if venue_name:
        print(f"Ballpark: {venue_name}")
    
    print(f"\n----- {team_abbr} LINEUP -----")
    for player in lineup_data['team']['lineup']:
        jersey_display = f"#{player['jersey']} " if player['jersey'] else ''
        print(f"{player['batting_order']}. {jersey_display}{player['name']} ({player['position']})")
    
    print("\n----- OPPONENT LINEUP -----")
    for player in lineup_data['opponent']['lineup']:
        jersey_display = f"#{player['jersey']} " if player['jersey'] else ''
        print(f"{player['batting_order']}. {jersey_display}{player['name']} ({player['position']})")
    
    # Print starting pitchers if available
    if pitchers:
        print("\n----- STARTING PITCHERS -----")
        
        # Our team's pitcher
        if pitchers['team']:
            jersey_display = f"#{pitchers['team']['jersey']} " if pitchers['team'].get('jersey') else ''
            throws = f" ({pitchers['team']['throws_desc']})" if pitchers['team'].get('throws_desc') else ''
            print(f"{pitchers['team_name']}: {jersey_display}{pitchers['team']['name']}{throws}")
        else:
            print(f"{pitchers['team_name']}: Starting pitcher information not available")
            
        # Opponent pitcher
        if pitchers['opponent']:
            jersey_display = f"#{pitchers['opponent']['jersey']} " if pitchers['opponent'].get('jersey') else ''
            throws = f" ({pitchers['opponent']['throws_desc']})" if pitchers['opponent'].get('throws_desc') else ''
            print(f"{pitchers['opponent_team']}: {jersey_display}{pitchers['opponent']['name']}{throws}")
        else:
            print(f"{pitchers['opponent_team']}: Starting pitcher information not available")
    
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