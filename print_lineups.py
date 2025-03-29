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
    
    # MLB Stats API endpoint for the schedule
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date}&teamId=121"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Check if there are any games today
        if data['totalGames'] == 0:
            return None, "No Mets game scheduled for today."
        
        # Get the game ID from the first (and likely only) game
        game_id = data['dates'][0]['games'][0]['gamePk']
        game_status = data['dates'][0]['games'][0]['status']['detailedState']
        
        return game_id, game_status
    except requests.exceptions.RequestException as e:
        return None, f"Error fetching game data: {e}"

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
                'batting_order': len(mets_lineup) + 1
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
                'batting_order': len(opponent_lineup) + 1
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
    game_id, game_status = get_mets_game(args.date)
    
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
    
    # Print the lineups
    date_header = "TODAY'S GAME" if args.date is None else f"GAME FOR {args.date}"
    print(f"\n===== {date_header} =====")
    print(f"{lineup_data['mets']['team']} vs {lineup_data['opponent']['team']}")
    
    print("\n----- METS LINEUP -----")
    for player in lineup_data['mets']['lineup']:
        print(f"{player['batting_order']}. {player['name']} ({player['position']})")
    
    print("\n----- OPPONENT LINEUP -----")
    for player in lineup_data['opponent']['lineup']:
        print(f"{player['batting_order']}. {player['name']} ({player['position']})")

if __name__ == "__main__":
    main()