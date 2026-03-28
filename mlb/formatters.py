"""Formatting helpers for MLB lineup data display."""

from datetime import datetime
from typing import Any

import pytz


def format_pitcher_info(pitcher: dict[str, Any] | None) -> str:
    """
    Format pitcher information for display.

    Args:
        pitcher: Pitcher information dictionary with keys:
            - name: Pitcher's full name
            - jersey: Jersey number (optional)
            - throws_desc: Throwing hand description (optional)

    Returns:
        Formatted pitcher information string
    """
    if not pitcher:
        return "Starting pitcher information not available"

    jersey_display = f"#{pitcher['jersey']} " if pitcher.get('jersey') else ''
    throws = f" ({pitcher['throws_desc']})" if pitcher.get('throws_desc') else ''
    return f"{jersey_display}{pitcher['name']}{throws}"


def format_player_info(player: dict[str, Any]) -> str:
    """
    Format player information for display.

    Args:
        player: Player information dictionary with keys:
            - batting_order: Position in batting order
            - name: Player's full name
            - position: Field position abbreviation
            - jersey: Jersey number (optional)

    Returns:
        Formatted player information string
    """
    jersey_display = f"#{player['jersey']} " if player.get('jersey') else ''
    return f"{player['batting_order']}. {jersey_display}{player['name']} ({player['position']})"


def convert_utc_to_edt(utc_time_str: str | None) -> str:
    """
    Convert UTC time string to EDT time string.

    Args:
        utc_time_str: UTC time string in ISO 8601 format

    Returns:
        Time in EDT in format "h:MM PM/AM EDT", or empty string on failure
    """
    if not utc_time_str:
        return ''

    try:
        utc_time = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
        eastern = pytz.timezone('US/Eastern')
        edt_time = utc_time.astimezone(eastern)
        return edt_time.strftime('%b %-d, %-I:%M %p EDT')
    except Exception:
        return ''
