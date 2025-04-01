import pytest
import json
from unittest.mock import patch, MagicMock
import sys
import os
import requests

# Add the parent directory to the path to allow importing the main script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from print_lineups import (
    MLB_TEAMS,
    get_team_game,
    get_lineup,
    get_pitcher_details,
    get_probable_pitchers,
    get_umpires
)

# Sample data for mocking responses
@pytest.fixture
def mock_schedule_response():
    """Fixture for a mock schedule API response"""
    with open(os.path.join(os.path.dirname(__file__), 'fixtures', 'schedule_response.json'), 'r') as f:
        return json.load(f)

@pytest.fixture
def mock_boxscore_response():
    """Fixture for a mock boxscore API response"""
    with open(os.path.join(os.path.dirname(__file__), 'fixtures', 'boxscore_response.json'), 'r') as f:
        return json.load(f)

@pytest.fixture
def mock_player_response():
    """Fixture for a mock player API response"""
    with open(os.path.join(os.path.dirname(__file__), 'fixtures', 'player_response.json'), 'r') as f:
        return json.load(f)

# Unit Tests
class TestMLBTeams:
    """Tests for the MLB_TEAMS dictionary"""

    def test_mlb_teams_has_30_teams(self):
        """Test that MLB_TEAMS contains all 30 MLB teams"""
        assert len(MLB_TEAMS) == 30
        
    def test_mlb_teams_contains_expected_keys(self):
        """Test that MLB_TEAMS contains expected team abbreviations"""
        expected_teams = ["NYM", "NYY", "LAD", "STL", "CHC"]
        for team in expected_teams:
            assert team in MLB_TEAMS
            
    def test_mlb_teams_values_are_integers(self):
        """Test that all team IDs are integers"""
        for team_id in MLB_TEAMS.values():
            assert isinstance(team_id, int)

class TestGetTeamGame:
    """Tests for the get_team_game function"""
    
    @patch('requests.get')
    def test_get_team_game_success(self, mock_get, mock_schedule_response):
        """Test successful game retrieval"""
        # Configure the mock
        mock_response = MagicMock()
        mock_response.json.return_value = mock_schedule_response
        mock_get.return_value = mock_response
        
        # Call the function
        game_id, game_status, venue_name, team_names = get_team_game(121)  # 121 is NYM
        
        # Assertions
        assert game_id == 778518
        assert game_status == "Final"
        assert venue_name == "Daikin Park"
        assert "New York Mets" in [team_names["home"], team_names["away"]]
        
    @patch('requests.get')
    def test_get_team_game_no_games(self, mock_get):
        """Test handling when no games are scheduled"""
        # Configure the mock for no games
        mock_response = MagicMock()
        mock_response.json.return_value = {"totalGames": 0}
        mock_get.return_value = mock_response
        
        # Call the function
        result = get_team_game(121)
        
        # Assertions
        assert result[0] is None  # game_id should be None
        assert "No game scheduled" in result[3]  # Error message
        
    @patch('requests.get')
    def test_get_team_game_uses_date_parameter(self, mock_get):
        """Test that date parameter is used in API URL"""
        # Configure the mock
        mock_response = MagicMock()
        mock_response.json.return_value = {"totalGames": 0}
        mock_get.return_value = mock_response
        
        # Call with a specific date
        get_team_game(121, "2025-04-01")
        
        # Verify the URL used contains the date
        args, kwargs = mock_get.call_args
        assert "date=2025-04-01" in args[0]
        
    @patch('requests.get')
    def test_get_team_game_exception_handling(self, mock_get):
        """Test exception handling in get_team_game"""
        # Configure the mock to raise a RequestException instead of a generic Exception
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        # Call the function
        game_id, game_status, venue_name, error_msg = get_team_game(121)
        
        # Assertions
        assert game_id is None
        assert game_status is None
        assert venue_name is None
        assert "Error" in error_msg

class TestGetLineup:
    """Tests for the get_lineup function"""
    
    @patch('requests.get')
    def test_get_lineup_success(self, mock_get, mock_boxscore_response):
        """Test successful lineup retrieval"""
        # Create a custom response with necessary structure
        custom_response = {
            "teams": {
                "away": {
                    "team": {
                        "id": 121,
                        "name": "New York Mets"
                    },
                    "battingOrder": [1, 2, 3],
                    "players": {
                        "ID1": {
                            "person": {"fullName": "Player 1"},
                            "position": {"abbreviation": "SS"},
                            "jerseyNumber": "10"
                        },
                        "ID2": {
                            "person": {"fullName": "Player 2"},
                            "position": {"abbreviation": "CF"},
                            "jerseyNumber": "20"
                        },
                        "ID3": {
                            "person": {"fullName": "Player 3"},
                            "position": {"abbreviation": "1B"},
                            "jerseyNumber": "30"
                        }
                    }
                },
                "home": {
                    "team": {
                        "id": 117,
                        "name": "Houston Astros"
                    },
                    "battingOrder": [4, 5, 6],
                    "players": {
                        "ID4": {
                            "person": {"fullName": "Player 4"},
                            "position": {"abbreviation": "P"},
                            "jerseyNumber": "40"
                        },
                        "ID5": {
                            "person": {"fullName": "Player 5"},
                            "position": {"abbreviation": "C"},
                            "jerseyNumber": "50"
                        },
                        "ID6": {
                            "person": {"fullName": "Player 6"},
                            "position": {"abbreviation": "3B"},
                            "jerseyNumber": "60"
                        }
                    }
                }
            }
        }
        
        # Configure the mock
        mock_response = MagicMock()
        mock_response.json.return_value = custom_response
        mock_get.return_value = mock_response
        
        # Call the function
        lineup_data, error = get_lineup(778518, 121)  # Using game_id and NYM team_id
        
        # Assertions
        assert error is None
        assert 'team' in lineup_data
        assert 'opponent' in lineup_data
        assert len(lineup_data['team']['lineup']) > 0
        assert len(lineup_data['opponent']['lineup']) > 0
        
    @patch('requests.get')
    def test_get_lineup_no_batting_order(self, mock_get, mock_boxscore_response):
        """Test handling when batting order isn't available"""
        # Modify the response to remove batting order
        modified_response = mock_boxscore_response.copy()
        for side in ['home', 'away']:
            if 'battingOrder' in modified_response['teams'][side]:
                del modified_response['teams'][side]['battingOrder']
        
        # Configure the mock
        mock_response = MagicMock()
        mock_response.json.return_value = modified_response
        mock_get.return_value = mock_response
        
        # Call the function
        lineup_data, error = get_lineup(778518, 121)
        
        # Assertions
        assert lineup_data is None
        assert "not yet available" in error

class TestGetPitcherDetails:
    """Tests for the get_pitcher_details function"""
    
    @patch('requests.get')
    def test_get_pitcher_details_success(self, mock_get, mock_player_response):
        """Test successful pitcher details retrieval"""
        # Configure the mock
        mock_response = MagicMock()
        mock_response.json.return_value = mock_player_response
        mock_get.return_value = mock_response
        
        # Call the function
        pitcher_details = get_pitcher_details(123456)
        
        # Assertions
        assert pitcher_details is not None
        assert pitcher_details['name'] == "Test Pitcher"
        assert pitcher_details['jersey'] == "21"
        assert pitcher_details['throws'] == "R"
        assert pitcher_details['throws_desc'] == "RHP"
        
    @patch('requests.get')
    def test_get_pitcher_details_left_handed(self, mock_get, mock_player_response):
        """Test for left-handed pitcher"""
        # Modify response for left-handed pitcher
        modified_response = mock_player_response.copy()
        modified_response['people'][0]['pitchHand']['code'] = "L"
        
        # Configure the mock
        mock_response = MagicMock()
        mock_response.json.return_value = modified_response
        mock_get.return_value = mock_response
        
        # Call the function
        pitcher_details = get_pitcher_details(123456)
        
        # Assertions
        assert pitcher_details['throws'] == "L"
        assert pitcher_details['throws_desc'] == "LHP"

class TestGetProbablePitchers:
    """Tests for the get_probable_pitchers function"""
    
    @patch('print_lineups.get_pitcher_details')
    @patch('requests.get')
    def test_get_probable_pitchers(self, mock_get, mock_get_pitcher_details, mock_boxscore_response):
        """Test probable pitchers retrieval"""
        # Configure the mocks
        mock_response = MagicMock()
        mock_response.json.return_value = mock_boxscore_response
        mock_get.return_value = mock_response
        
        # Mock pitcher details return
        pitcher_details = {
            'name': 'Test Pitcher',
            'jersey': '21',
            'throws': 'R',
            'throws_desc': 'RHP'
        }
        mock_get_pitcher_details.return_value = pitcher_details
        
        # Call the function
        pitchers = get_probable_pitchers(778518, "Final", 121)
        
        # Assertions
        assert pitchers is not None
        assert 'team' in pitchers
        assert 'opponent' in pitchers
        assert pitchers['team'] == pitcher_details or pitchers['opponent'] == pitcher_details

class TestGetUmpires:
    """Tests for the get_umpires function"""
    
    @patch('requests.get')
    def test_get_umpires_success(self, mock_get, mock_boxscore_response):
        """Test successful umpire information retrieval"""
        # Make sure boxscore response includes officials
        modified_response = mock_boxscore_response.copy()
        modified_response['officials'] = [
            {
                'official': {'fullName': 'John Smith'},
                'officialType': 'Home Plate'
            },
            {
                'official': {'fullName': 'Jane Doe'},
                'officialType': 'First Base'
            }
        ]
        
        # Configure the mock
        mock_response = MagicMock()
        mock_response.json.return_value = modified_response
        mock_get.return_value = mock_response
        
        # Call the function
        umpires = get_umpires(778518)
        
        # Assertions
        assert umpires is not None
        assert len(umpires) == 2
        assert umpires[0]['officialType'] == 'Home Plate'
        assert umpires[0]['official']['fullName'] == 'John Smith'
        
    @patch('requests.get')
    def test_get_umpires_no_officials(self, mock_get):
        """Test handling when no officials data is available"""
        # Configure response with no officials
        mock_response = MagicMock()
        mock_response.json.return_value = {'teams': {}}
        mock_get.return_value = mock_response
        
        # Call the function
        umpires = get_umpires(778518)
        
        # Assertions
        assert umpires is None