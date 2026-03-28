"""Flask application for MLB lineup information."""

import logging
from datetime import datetime

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from mlb.api_client import (
    get_lineup,
    get_probable_pitchers,
    get_team_game,
    get_umpires,
)
from mlb.cache import cache_manager, rate_limiter
from mlb.formatters import convert_utc_to_edt, format_pitcher_info, format_player_info
from mlb.teams import MLB_TEAMS

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route('/')
def index():
    """Homepage showing today's Mets lineup."""
    team_abbr = 'NYM'
    team_id = MLB_TEAMS[team_abbr]

    try:
        game_id, game_status, venue_name, team_names, game_time_or_error = get_team_game(team_id)

        if game_id is None:
            return render_template('no_game.html', team=team_abbr)

        lineup_data, lineup_error = get_lineup(game_id, team_id)
        pitchers = get_probable_pitchers(game_id, game_status, team_id)
        umpires = get_umpires(game_id)

        is_home = team_names.get('home') == (
            pitchers.get('team_name') if pitchers else
            lineup_data.get('team', {}).get('name') if lineup_data else None
        ) if team_names else False

        game_time = game_time_or_error
        response_data = {
            'game': {
                'id': game_id,
                'status': game_status,
                'venue': venue_name,
                'game_time': game_time,
                'game_time_formatted': convert_utc_to_edt(game_time) if game_time else None,
                'home_team': team_names.get('home'),
                'away_team': team_names.get('away'),
            },
            'requested_team': {
                'abbreviation': team_abbr,
                'is_home': is_home,
            },
            'pitchers': pitchers,
            'lineup': lineup_data,
            'lineup_error': lineup_error,
            'umpires': umpires,
        }

        return render_template(
            'lineup.html',
            data=response_data,
            format_pitcher_info=format_pitcher_info,
            format_player_info=format_player_info,
        )

    except Exception as e:
        logger.exception(f"Error loading homepage: {e}")
        return render_template('no_game.html', team=team_abbr, error=str(e))


@app.route('/search')
def search():
    """Team and date selector form."""
    return render_template('index.html', teams=sorted(MLB_TEAMS.keys()))


@app.route('/api/lineup')
def get_lineup_api():
    """
    Fetch MLB lineup information.

    Query Parameters:
        team (str): Team abbreviation (required, e.g., NYM, LAD, NYY)
        date (str): Game date in YYYY-MM-DD format (optional, defaults to today)
        format (str): Response format - 'json' or 'html' (optional, defaults to json)

    Returns:
        JSON or HTML response with lineup, pitchers, umpires, and game info.
        Returns appropriate HTTP status codes on errors:
        - 400: Invalid team or date format
        - 404: No game found
        - 500: Server error
    """
    team_abbr = request.args.get('team', '').upper()
    date = request.args.get('date')
    output_format = request.args.get('format', 'json').lower()

    # Validate team parameter
    if not team_abbr:
        return error_response('Missing required parameter: team', 400, output_format)

    if team_abbr not in MLB_TEAMS:
        valid_teams = ', '.join(sorted(MLB_TEAMS.keys()))
        return error_response(
            f"Invalid team abbreviation '{team_abbr}'. Valid options: {valid_teams}",
            400,
            output_format
        )

    # Validate date format if provided
    if date:
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return error_response('Invalid date format. Use YYYY-MM-DD', 400, output_format)

    team_id = MLB_TEAMS[team_abbr]

    try:
        # Fetch game information
        game_id, game_status, venue_name, team_names, game_time_or_error = get_team_game(team_id, date)

        if game_id is None:
            # When game_id is None, game_time_or_error contains the error message
            return error_response(game_time_or_error, 404, output_format)

        # Fetch lineup, pitchers, and umpires
        lineup_data, lineup_error = get_lineup(game_id, team_id)
        pitchers = get_probable_pitchers(game_id, game_status, team_id)
        umpires = get_umpires(game_id)

        # Determine home/away for the requested team based on team_names
        is_home = team_names.get('home') == (
            pitchers.get('team_name') if pitchers else
            lineup_data.get('team', {}).get('name') if lineup_data else None
        ) if team_names else False

        # Build response data (game_time_or_error contains game_time when successful)
        game_time = game_time_or_error
        response_data = {
            'game': {
                'id': game_id,
                'status': game_status,
                'venue': venue_name,
                'game_time': game_time,
                'game_time_formatted': convert_utc_to_edt(game_time) if game_time else None,
                'home_team': team_names.get('home'),
                'away_team': team_names.get('away'),
            },
            'requested_team': {
                'abbreviation': team_abbr,
                'is_home': is_home,
            },
            'pitchers': pitchers,
            'lineup': lineup_data,
            'lineup_error': lineup_error,
            'umpires': umpires,
        }

        if output_format == 'html':
            return render_template(
                'lineup.html',
                data=response_data,
                format_pitcher_info=format_pitcher_info,
                format_player_info=format_player_info,
            )

        return jsonify(response_data)

    except Exception as e:
        logger.exception(f"Error processing lineup request: {e}")
        return error_response(f"Internal server error: {str(e)}", 500, output_format)


def error_response(message, status_code, output_format='json'):
    """
    Return an error response in the appropriate format.

    Args:
        message (str): Error message
        status_code (int): HTTP status code
        output_format (str): 'json' or 'html'

    Returns:
        Flask response with error information
    """
    if output_format == 'html':
        return render_template(
            'error.html',
            error=message,
            status_code=status_code
        ), status_code

    return jsonify({'error': message}), status_code


@app.route('/api/cache-stats')
def cache_stats():
    """
    Get cache and rate limiter statistics.

    Returns:
        JSON with cache hits/misses and rate limiter status
    """
    return jsonify({
        'cache': cache_manager.get_stats(),
        'rate_limiter': rate_limiter.get_stats()
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
