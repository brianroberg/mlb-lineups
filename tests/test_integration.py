import pytest
import os
import sys
from unittest.mock import patch, MagicMock
import json

# Add the parent directory to the path to allow importing the main modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app


# Fixtures for test data
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


@pytest.fixture
def client():
    """Flask test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


# Integration Tests for Flask API
@pytest.mark.integration
class TestAPIEndpoints:
    """Integration tests for API endpoints"""

    def test_index_page(self, client):
        """Test the index page returns HTML"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'MLB Lineups' in response.data
        assert b'Get Game Lineup' in response.data

    def test_missing_team_parameter(self, client):
        """Test error when team parameter is missing"""
        response = client.get('/api/lineup')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Missing required parameter: team' in data['error']

    def test_invalid_team_abbreviation(self, client):
        """Test error for invalid team abbreviation"""
        response = client.get('/api/lineup?team=XYZ')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Invalid team abbreviation' in data['error']
        assert 'Valid options' in data['error']

    def test_invalid_date_format(self, client):
        """Test error for invalid date format"""
        response = client.get('/api/lineup?team=NYM&date=04-15-2025')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Invalid date format' in data['error']

    @patch('app.get_umpires')
    @patch('app.get_probable_pitchers')
    @patch('app.get_lineup')
    @patch('app.get_team_game')
    def test_successful_lineup_json(self, mock_get_team_game, mock_get_lineup,
                                    mock_get_probable_pitchers, mock_get_umpires, client):
        """Test successful lineup retrieval returns JSON"""
        # Configure mocks
        mock_get_team_game.return_value = (
            778518,  # game_id
            "Final",  # game_status
            "Citi Field",  # venue_name
            {'home': 'New York Mets', 'away': 'Test Opponent'},  # team_names
            "2025-04-15T18:10:00Z"  # game_time
        )

        mock_get_lineup.return_value = (
            {
                'team': {
                    'name': 'Mets',
                    'lineup': [
                        {'batting_order': 1, 'name': 'Test Player 1', 'position': 'SS', 'jersey': '10'},
                        {'batting_order': 2, 'name': 'Test Player 2', 'position': 'CF', 'jersey': '20'}
                    ]
                },
                'opponent': {
                    'team': 'Test Opponent',
                    'lineup': [
                        {'batting_order': 1, 'name': 'Opponent 1', 'position': '2B', 'jersey': '5'},
                        {'batting_order': 2, 'name': 'Opponent 2', 'position': 'RF', 'jersey': '15'}
                    ]
                }
            },
            None  # No error
        )

        mock_get_probable_pitchers.return_value = {
            'team': {
                'name': 'Test Pitcher',
                'jersey': '30',
                'throws': 'R',
                'throws_desc': 'RHP'
            },
            'opponent': {
                'name': 'Opponent Pitcher',
                'jersey': '40',
                'throws': 'L',
                'throws_desc': 'LHP'
            },
            'team_name': 'New York Mets',
            'opponent_team': 'Test Opponent'
        }

        mock_get_umpires.return_value = [
            {'official': {'fullName': 'Ump One'}, 'officialType': 'Home Plate'},
            {'official': {'fullName': 'Ump Two'}, 'officialType': 'First Base'}
        ]

        # Make request
        response = client.get('/api/lineup?team=NYM')

        # Assertions
        assert response.status_code == 200
        data = response.get_json()

        # Check game info
        assert data['game']['id'] == 778518
        assert data['game']['status'] == 'Final'
        assert data['game']['venue'] == 'Citi Field'
        assert data['game']['home_team'] == 'New York Mets'
        assert data['game']['away_team'] == 'Test Opponent'

        # Check requested team info
        assert data['requested_team']['abbreviation'] == 'NYM'

        # Check lineup
        assert data['lineup'] is not None
        assert len(data['lineup']['team']['lineup']) == 2

        # Check pitchers
        assert data['pitchers'] is not None
        assert data['pitchers']['team']['name'] == 'Test Pitcher'

        # Check umpires
        assert data['umpires'] is not None
        assert len(data['umpires']) == 2

    @patch('app.get_umpires')
    @patch('app.get_probable_pitchers')
    @patch('app.get_lineup')
    @patch('app.get_team_game')
    def test_successful_lineup_html(self, mock_get_team_game, mock_get_lineup,
                                    mock_get_probable_pitchers, mock_get_umpires, client):
        """Test successful lineup retrieval returns HTML when format=html"""
        # Configure mocks
        mock_get_team_game.return_value = (
            778518, "Final", "Citi Field",
            {'home': 'New York Mets', 'away': 'Test Opponent'},
            "2025-04-15T18:10:00Z"
        )

        mock_get_lineup.return_value = (
            {
                'team': {
                    'name': 'Mets',
                    'lineup': [
                        {'batting_order': 1, 'name': 'Test Player 1', 'position': 'SS', 'jersey': '10'}
                    ]
                },
                'opponent': {
                    'team': 'Test Opponent',
                    'lineup': [
                        {'batting_order': 1, 'name': 'Opponent 1', 'position': '2B', 'jersey': '5'}
                    ]
                }
            },
            None
        )

        mock_get_probable_pitchers.return_value = {
            'team': {'name': 'Test Pitcher', 'jersey': '30', 'throws': 'R', 'throws_desc': 'RHP'},
            'opponent': {'name': 'Opponent Pitcher', 'jersey': '40', 'throws': 'L', 'throws_desc': 'LHP'},
            'team_name': 'New York Mets',
            'opponent_team': 'Test Opponent'
        }

        mock_get_umpires.return_value = [
            {'official': {'fullName': 'Ump One'}, 'officialType': 'Home Plate'}
        ]

        # Make request with format=html
        response = client.get('/api/lineup?team=NYM&format=html')

        # Assertions
        assert response.status_code == 200
        assert b'<!DOCTYPE html>' in response.data
        assert b'Test Opponent vs. New York Mets' in response.data
        assert b'Citi Field' in response.data

    @patch('app.get_team_game')
    def test_no_game_scheduled(self, mock_get_team_game, client):
        """Test 404 when no game is scheduled"""
        mock_get_team_game.return_value = (
            None, None, None, None, "No game scheduled for the selected team on this date."
        )

        response = client.get('/api/lineup?team=NYM')
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert 'No game scheduled' in data['error']

    @patch('app.get_umpires')
    @patch('app.get_probable_pitchers')
    @patch('app.get_lineup')
    @patch('app.get_team_game')
    def test_lineup_not_available(self, mock_get_team_game, mock_get_lineup,
                                  mock_get_probable_pitchers, mock_get_umpires, client):
        """Test response when lineup is not available"""
        mock_get_team_game.return_value = (
            778518, "Scheduled", "Citi Field",
            {'home': 'New York Mets', 'away': 'Test Opponent'},
            "2025-04-15T18:10:00Z"
        )

        mock_get_lineup.return_value = (None, "Lineup not yet available for this game")

        mock_get_probable_pitchers.return_value = {
            'team': {'name': 'Test Pitcher', 'jersey': '30', 'throws': 'R', 'throws_desc': 'RHP'},
            'opponent': None,
            'team_name': 'New York Mets',
            'opponent_team': 'Test Opponent'
        }

        mock_get_umpires.return_value = None

        response = client.get('/api/lineup?team=NYM')

        assert response.status_code == 200
        data = response.get_json()
        assert data['lineup'] is None
        assert data['lineup_error'] == "Lineup not yet available for this game"

    def test_cors_headers(self, client):
        """Test CORS headers are present"""
        response = client.get('/api/lineup?team=XYZ')  # Invalid team, but CORS should still work
        # flask-cors adds Access-Control-Allow-Origin header
        assert 'Access-Control-Allow-Origin' in response.headers

    def test_date_parameter_accepted(self, client):
        """Test that date parameter is accepted with valid format"""
        with patch('app.get_team_game') as mock:
            mock.return_value = (None, None, None, None, "No game scheduled")
            response = client.get('/api/lineup?team=NYM&date=2025-04-15')
            assert response.status_code == 404  # No game, but date was valid
            # Verify the function was called with the date parameter
            mock.assert_called_once()
            call_args = mock.call_args
            assert call_args[0][1] == '2025-04-15'


@pytest.mark.integration
class TestHTMLFormatErrors:
    """Tests for HTML format error responses"""

    def test_invalid_team_html_error(self, client):
        """Test error page for invalid team with HTML format"""
        response = client.get('/api/lineup?team=XYZ&format=html')
        assert response.status_code == 400
        assert b'<!DOCTYPE html>' in response.data
        assert b'Error 400' in response.data
        assert b'Invalid team abbreviation' in response.data

    @patch('app.get_team_game')
    def test_no_game_html_error(self, mock_get_team_game, client):
        """Test error page when no game scheduled with HTML format"""
        mock_get_team_game.return_value = (
            None, None, None, None, "No game scheduled for the selected team on this date."
        )

        response = client.get('/api/lineup?team=NYM&format=html')
        assert response.status_code == 404
        assert b'<!DOCTYPE html>' in response.data
        assert b'Error 404' in response.data
        assert b'No game scheduled' in response.data
