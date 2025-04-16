import pytest
import os
import sys
from unittest.mock import patch, MagicMock
import json
from io import StringIO

# Add the parent directory to the path to allow importing the main script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import print_lineups

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

# Integration Tests
class TestCommandLineOptions:
    """Integration tests for command line options"""
    
    @patch('print_lineups.get_team_game')
    def test_default_team_option(self, mock_get_team_game):
        """Test default team (NYM) is used when no --team option is provided"""
        # Configure the mock to return None values to short-circuit the function
        mock_get_team_game.return_value = (None, None, None, None, "No games")
        
        # Set up sys.argv
        sys.argv = ['print_lineups.py']
        
        # Run main function with patched stdout
        with patch('sys.stdout', new=StringIO()):
            with pytest.raises(SystemExit):
                print_lineups.main()
            
            # Check that mock was called with NYM team ID (121)
            mock_get_team_game.assert_called_once()
            args, kwargs = mock_get_team_game.call_args
            assert args[0] == 121
    
    @patch('print_lineups.get_team_game')
    def test_specified_team_option(self, mock_get_team_game):
        """Test specified team is used when --team option is provided"""
        # Configure the mock
        mock_get_team_game.return_value = (None, None, None, None, "No games")
        
        # Test with different teams
        test_cases = [
            ('STL', 138),
            ('LAD', 119),
            ('NYY', 147)
        ]
        
        for abbr, team_id in test_cases:
            # Set up sys.argv
            sys.argv = ['print_lineups.py', '--team', abbr]
            
            # Run main function with patched stdout
            with patch('sys.stdout', new=StringIO()):
                with pytest.raises(SystemExit):
                    print_lineups.main()
                
                # Check that mock was called with the correct team ID
                mock_get_team_game.assert_called_with(team_id, None)
    
    @patch('print_lineups.get_team_game')
    def test_date_option(self, mock_get_team_game):
        """Test specified date is used when --date option is provided"""
        # Configure the mock
        mock_get_team_game.return_value = (None, None, None, None, "No games")
        
        # Set up sys.argv with a date
        sys.argv = ['print_lineups.py', '--date', '2025-04-15']
        
        # Run main function with patched stdout
        with patch('sys.stdout', new=StringIO()):
            with pytest.raises(SystemExit):
                print_lineups.main()
            
            # Check that mock was called with the correct date
            mock_get_team_game.assert_called_with(121, '2025-04-15')
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_invalid_team_error(self, mock_stdout):
        """Test error message when an invalid team is provided"""
        # Set up sys.argv with an invalid team
        sys.argv = ['print_lineups.py', '--team', 'XYZ']
        
        # Run main function 
        with pytest.raises(SystemExit):
            print_lineups.main()
        
        # Check output for error message
        output = mock_stdout.getvalue()
        assert "Invalid team abbreviation" in output
        assert "Valid options are" in output

class TestEndToEndWithMocks:
    """Integration tests mocking API responses to simulate end-to-end behavior"""

    # Mock argparse to prevent parsing from command line
    @pytest.fixture(autouse=True)
    def mock_argparse(self, monkeypatch):
        """Mock argparse to avoid command line parsing issues in tests"""
        mock_args = MagicMock()
        mock_args.date = None
        mock_args.team = 'NYM'
        
        # Create a mock parser that returns our predefined args
        mock_parser = MagicMock()
        mock_parser.parse_args.return_value = mock_args
        
        # Patch ArgumentParser to return our mock parser
        monkeypatch.setattr('argparse.ArgumentParser', lambda **kwargs: mock_parser)
    
    @patch('print_lineups.get_umpires')
    @patch('print_lineups.get_probable_pitchers')
    @patch('print_lineups.get_lineup')
    @patch('print_lineups.get_team_game')
    @patch('sys.exit')  # Mock sys.exit to prevent actual exit
    def test_successful_lineup_display(self, mock_exit, mock_get_team_game, mock_get_lineup, 
                                       mock_get_probable_pitchers, mock_get_umpires):
        """Test successful end-to-end flow with mocked responses"""
        # Configure mocks
        mock_get_team_game.return_value = (
            778518,  # game_id
            "Final",  # game_status
            "Test Ballpark",  # venue_name
            {'home': 'New York Mets', 'away': 'Test Opponent'},  # team_names
            "2025-04-15T18:10:00Z"  # game_time
        )
        
        mock_get_lineup.return_value = (
            {
                'team': {
                    'name': 'New York Mets',
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
                'throws_desc': 'Right'
            },
            'opponent': {
                'name': 'Opponent Pitcher', 
                'jersey': '40', 
                'throws': 'L', 
                'throws_desc': 'Left'
            },
            'team_name': 'New York Mets',
            'opponent_team': 'Test Opponent'
        }
        
        mock_get_umpires.return_value = [
            {'official': {'fullName': 'Ump One'}, 'officialType': 'Home Plate'},
            {'official': {'fullName': 'Ump Two'}, 'officialType': 'First Base'}
        ]
        
        # Set up sys.argv 
        sys.argv = ['print_lineups.py']
        
        # Run main function with patched stdout
        with patch('sys.stdout', new=StringIO()) as fake_output:
            print_lineups.main()
            
            # Check output contains expected sections
            output = fake_output.getvalue()
            
            # Game header
            assert "Test Ballpark" in output
            assert "Test Opponent vs. New York Mets" in output
            
            # Check both lineups are present
            assert "LINEUP (HOME)" in output
            assert "LINEUP (AWAY)" in output
            assert "Test Player 1" in output
            assert "#10" in output
            assert "Opponent 1" in output
            assert "#5" in output
            
            # Pitchers
            assert "STARTING PITCHERS" in output
            assert "Test Pitcher" in output
            assert "(Right)" in output
            assert "Opponent Pitcher" in output
            assert "(Left)" in output
            
            # Umpires
            assert "UMPIRES" in output
            assert "Ump One" in output
            assert "Home Plate" in output
    
    @patch('print_lineups.get_team_game')
    @patch('sys.exit')  # Mock sys.exit to prevent actual exit
    def test_no_games_scheduled(self, mock_exit, mock_get_team_game):
        """Test behavior when no games are scheduled"""
        # Configure mock to return None values that trigger exit
        message = "None"
        mock_get_team_game.return_value = (None, None, None, None, message)
        
        # Set up an exit handler to capture the exit
        def side_effect(code):
            # Check that we're exiting with status code 1
            assert code == 1
            # Raise an exception to stop execution
            raise SystemExit(code)
        
        # Configure the mock exit to use our side effect
        mock_exit.side_effect = side_effect
        
        # Run main function with patched stdout
        with patch('sys.stdout', new=StringIO()) as fake_output:
            # Call main with SystemExit expected
            with pytest.raises(SystemExit):
                print_lineups.main()
            
            # Check that the message was printed
            output = fake_output.getvalue()
            assert message in output
            
    @patch('print_lineups.get_umpires')
    @patch('print_lineups.get_probable_pitchers')
    @patch('print_lineups.get_lineup')
    @patch('print_lineups.get_team_game')
    @patch('sys.exit')  # Mock sys.exit to prevent actual exit
    def test_lineup_not_available(self, mock_exit, mock_get_team_game, mock_get_lineup, 
                                 mock_get_probable_pitchers, mock_get_umpires):
        """Test behavior when lineup is not available"""
        # Configure mocks
        mock_get_team_game.return_value = (
            778518,  # game_id
            "Scheduled",  # game_status
            "Test Ballpark",  # venue_name
            {'home': 'New York Mets', 'away': 'Test Opponent'},  # team_names
            "2025-04-15T18:10:00Z"  # game_time
        )
        
        error_message = "Lineup not yet available for this game against Test Opponent"
        mock_get_lineup.return_value = (None, error_message)
        
        # Add pitcher information 
        mock_get_probable_pitchers.return_value = {
            'team': {
                'name': 'Test Pitcher', 
                'jersey': '30', 
                'throws': 'R', 
                'throws_desc': 'Right'
            },
            'opponent': {
                'name': 'Opponent Pitcher', 
                'jersey': '40', 
                'throws': 'L', 
                'throws_desc': 'Left'
            },
            'team_name': 'New York Mets',
            'opponent_team': 'Test Opponent'
        }
        
        mock_get_umpires.return_value = None
        
        # Set up sys.argv
        sys.argv = ['print_lineups.py']
        
        # Run main function with patched stdout
        with patch('sys.stdout', new=StringIO()) as fake_output:
            # Run main without expecting SystemExit (our updated code doesn't exit on missing lineup)
            print_lineups.main()
            
            # Check output
            output = fake_output.getvalue()
            assert "Test Opponent vs. New York Mets" in output
            assert "STARTING PITCHERS" in output
            assert "Test Pitcher" in output
            assert "Lineups not yet available" in output