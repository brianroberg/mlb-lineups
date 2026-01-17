"""Formatting helpers for MLB lineup data display."""

from datetime import datetime

import pytz


def format_pitcher_info(pitcher):
    """
    Format pitcher information for display.

    Args:
        pitcher (dict): Pitcher information dictionary with keys:
            - name: Pitcher's full name
            - jersey: Jersey number (optional)
            - throws_desc: Throwing hand description (optional)

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
    Format player information for display.

    Args:
        player (dict): Player information dictionary with keys:
            - batting_order: Position in batting order
            - name: Player's full name
            - position: Field position abbreviation
            - jersey: Jersey number (optional)

    Returns:
        str: Formatted player information string
    """
    jersey_display = f"#{player['jersey']} " if player.get('jersey') else ''
    return f"{player['batting_order']}. {jersey_display}{player['name']} ({player['position']})"


def convert_utc_to_edt(utc_time_str):
    """
    Convert UTC time string to EDT time string.

    Args:
        utc_time_str (str): UTC time string in ISO 8601 format

    Returns:
        str: Time in EDT in format "h:MM PM/AM EDT", or empty string on failure
    """
    if not utc_time_str:
        return ''

    try:
        utc_time = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
        eastern = pytz.timezone('US/Eastern')
        edt_time = utc_time.astimezone(eastern)
        return edt_time.strftime('%-I:%M %p EDT').lstrip('0')
    except Exception:
        return ''
