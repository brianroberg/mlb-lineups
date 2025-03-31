import requests
from datetime import datetime
import pytz
import argparse

def get_mets_game(date=None):
    """
    Fetch Mets game information from the MLB Stats API for a specific date
    
    Args:
        date (str, optional): Date in YYYY-MM-DD format. Defaults to today's date.
    """
    # Get today's date in the format required by the API (YYYY-MM-DD) if not provided
    if date is None:
        eastern = pytz.timezone('US/Eastern')
        date = datetime.now(eastern).strftime('%Y-%m-%d')
    
    # MLB Stats API endpoint for the schedule with venue information
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date}&teamId=121&hydrate=venue"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Check if there are any games today
        if data['totalGames'] == 0:
            return None, None, "No Mets game scheduled for today."
        
        # Get the game information from the first (and likely only) game
        game = data['dates'][0]['games'][0]
        game_id = game['gamePk']
        game_status = game['status']['detailedState']
        
        # Get venue information if available
        venue_name = None
        if 'venue' in game and 'name' in game['venue']:
            venue_name = game['venue']['name']
        
        return game_id, game_status, venue_name
    except requests.exceptions.RequestException as e:
        return None, None, f"Error fetching game data: {e}"

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
            details['throws_desc'] = 'Right'
        elif details['throws'] == 'L':
            details['throws_desc'] = 'Left'
        else:
            details['throws_desc'] = 'Unknown'
            
        return details
    except requests.exceptions.RequestException as e:
        print(f"Error fetching pitcher details: {e}")
        return None

def get_probable_pitchers(game_id, status):
    """
    Fetch the probable starting pitchers for a game
    
    Args:
        game_id (int): The game ID
        status (str): The game status
        
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
        
        # Find which side the Mets are on (home or away)
        mets_side = 'home' if teams['home']['team']['id'] == 121 else 'away'
        opponent_side = 'away' if mets_side == 'home' else 'home'
        
        # Initialize pitcher data
        pitchers = {
            'mets': None,
            'opponent': None,
            'mets_team': teams[mets_side]['team']['name'],
            'opponent_team': teams[opponent_side]['team']['name']
        }
        
        # For each team, try to find the starting pitcher
        sides = {'mets': mets_side, 'opponent': opponent_side}
        
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

def get_lineup(game_id):
    """
    Fetch the starting lineup for a specific game
    """
    url = f"https://statsapi.mlb.com/api/v1/game/{game_id}/boxscore"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Get the teams data
        teams = data['teams']
        
        # Find which side the Mets are on (home or away)
        mets_side = 'home' if teams['home']['team']['id'] == 121 else 'away'
        opponent_side = 'away' if mets_side == 'home' else 'home'
        
        # Get the Mets and opponent team info
        mets_team = teams[mets_side]
        opponent_team = teams[opponent_side]
        
        # Extract lineups if available
        mets_lineup = []
        opponent_lineup = []
        
        # Check if lineups are available
        if 'battingOrder' not in mets_team or not mets_team['battingOrder']:
            return None, f"Lineup not yet available for this game against {opponent_team['team']['name']}"
        
        # Get Mets lineup
        for player_id in mets_team['battingOrder']:
            if player_id == 0:  # Sometimes there are zeros in the batting order
                continue
            player = mets_team['players'][f'ID{player_id}']
            position = player['position']['abbreviation']
            mets_lineup.append({
                'name': player['person']['fullName'],
                'position': position,
                'batting_order': len(mets_lineup) + 1,
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
            'mets': {
                'team': mets_team['team']['name'],
                'lineup': mets_lineup
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
    parser = argparse.ArgumentParser(description='Fetch MLB lineup information for the Mets')
    parser.add_argument('--date', type=str, help='Game date in YYYY-MM-DD format (default: today)')
    args = parser.parse_args()
    
    date_str = "today's" if args.date is None else f"the {args.date}"
    print(f"Fetching {date_str} Mets game information...")
    game_id, game_status, venue_name = get_mets_game(args.date)
    
    if game_id is None:
        print(game_status)
        return
    
    print(f"Found game (ID: {game_id}), Status: {game_status}")
    
    if game_status not in ["Final", "In Progress", "Warmup", "Pre-Game", "Scheduled"]:
        print(f"Game status is '{game_status}'. Lineup may not be available.")
        
    if game_status == "Final":
        print("Note: This is a completed game. If lineups aren't available, the API may not have stored them.")
    
    print("Fetching lineup information...")
    lineup_data, error = get_lineup(game_id)
    
    if error:
        print(error)
        return
    
    # Get starting pitchers
    print("Fetching starting pitchers...")
    pitchers = get_probable_pitchers(game_id, game_status)
    
    # Print the lineups
    date_header = "TODAY'S GAME" if args.date is None else f"GAME FOR {args.date}"
    print(f"\n===== {date_header} =====")
    print(f"{lineup_data['mets']['team']} vs {lineup_data['opponent']['team']}")
    if venue_name:
        print(f"Ballpark: {venue_name}")
    
    print("\n----- METS LINEUP -----")
    for player in lineup_data['mets']['lineup']:
        jersey_display = f"#{player['jersey']} " if player['jersey'] else ''
        print(f"{player['batting_order']}. {jersey_display}{player['name']} ({player['position']})")
    
    print("\n----- OPPONENT LINEUP -----")
    for player in lineup_data['opponent']['lineup']:
        jersey_display = f"#{player['jersey']} " if player['jersey'] else ''
        print(f"{player['batting_order']}. {jersey_display}{player['name']} ({player['position']})")
    
    # Print starting pitchers if available
    if pitchers:
        print("\n----- STARTING PITCHERS -----")
        
        # Mets pitcher
        if pitchers['mets']:
            jersey_display = f"#{pitchers['mets']['jersey']} " if pitchers['mets'].get('jersey') else ''
            throws = f" ({pitchers['mets']['throws_desc']})" if pitchers['mets'].get('throws_desc') else ''
            print(f"{pitchers['mets_team']}: {jersey_display}{pitchers['mets']['name']}{throws}")
        else:
            print(f"{pitchers['mets_team']}: Starting pitcher information not available")
            
        # Opponent pitcher
        if pitchers['opponent']:
            jersey_display = f"#{pitchers['opponent']['jersey']} " if pitchers['opponent'].get('jersey') else ''
            throws = f" ({pitchers['opponent']['throws_desc']})" if pitchers['opponent'].get('throws_desc') else ''
            print(f"{pitchers['opponent_team']}: {jersey_display}{pitchers['opponent']['name']}{throws}")
        else:
            print(f"{pitchers['opponent_team']}: Starting pitcher information not available")

if __name__ == "__main__":
    main()