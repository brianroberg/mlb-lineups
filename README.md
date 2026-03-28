# MLB Lineups

A Flask web application for retrieving MLB game lineups, starting pitchers, and umpire information via a REST API.

## Features

- **REST API** for programmatic access to lineup data
- **Web interface** with team selector for quick lookups
- **Complete game information**: lineups, starting pitchers, umpires, venue
- **Spoiler-free**: no scores displayed (perfect for time-shifted viewing)
- **Smart caching**: game-status aware TTL reduces API calls
- **Rate limiting**: protects against excessive MLB API usage
- **CORS enabled**: use from any frontend application

## Why This Exists

I enjoy scoring baseball games while watching on TV, which means I need starting lineups. This app provides convenient access to all the information needed for a scorecard—without spoiling the final score.

## Installation

### Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/brianroberg/mlb-lineups.git
   cd mlb-lineups
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```
   This creates a `.venv` directory automatically and installs all runtime and dev dependencies.

## Usage

### Running the Server

**Development:**
```bash
uv run python app.py
```
The server starts at `http://localhost:5000`

**Production:**
```bash
uv sync --group prod
uv run gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Web Interface

Open `http://localhost:5000` in your browser to access the team selector form.

## API Reference

### Get Lineup

Retrieve lineup, pitchers, and game information for a team.

```
GET /api/lineup
```

#### Query Parameters

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| `team`    | string | Yes      | Team abbreviation (e.g., `NYM`, `LAD`, `NYY`) |
| `date`    | string | No       | Game date in `YYYY-MM-DD` format. Defaults to today. |
| `format`  | string | No       | Response format: `json` (default) or `html` |

#### Example Requests

```bash
# Get today's Mets lineup as JSON
curl "http://localhost:5000/api/lineup?team=NYM"

# Get Dodgers lineup for a specific date
curl "http://localhost:5000/api/lineup?team=LAD&date=2025-04-15"

# Get lineup as HTML page
curl "http://localhost:5000/api/lineup?team=NYY&format=html"
```

#### Response Format

```json
{
  "game": {
    "id": 778452,
    "status": "Final",
    "venue": "Target Field",
    "game_time": "2025-04-15T23:40:00Z",
    "game_time_formatted": "7:40 PM EDT",
    "home_team": "Minnesota Twins",
    "away_team": "New York Mets"
  },
  "requested_team": {
    "abbreviation": "NYM",
    "is_home": false
  },
  "pitchers": {
    "team": {
      "name": "Clay Holmes",
      "jersey": "35",
      "throws": "R",
      "throws_desc": "RHP"
    },
    "opponent": {
      "name": "Joe Ryan",
      "jersey": "41",
      "throws": "R",
      "throws_desc": "RHP"
    },
    "team_name": "New York Mets",
    "opponent_team": "Minnesota Twins"
  },
  "lineup": {
    "team": {
      "name": "Mets",
      "lineup": [
        {
          "name": "Francisco Lindor",
          "position": "SS",
          "batting_order": 1,
          "jersey": "12"
        }
      ]
    },
    "opponent": {
      "team": "Twins",
      "lineup": []
    }
  },
  "lineup_error": null,
  "umpires": [
    {
      "official": { "fullName": "Adam Hamari" },
      "officialType": "Home Plate"
    }
  ]
}
```

#### Error Responses

| Status | Description |
|--------|-------------|
| 400    | Invalid team abbreviation or date format |
| 404    | No game scheduled for the team on that date |
| 500    | Internal server error |

### Get Cache Statistics

Retrieve cache and rate limiter metrics for monitoring.

```
GET /api/cache-stats
```

#### Example Request

```bash
curl "http://localhost:5000/api/cache-stats"
```

#### Response Format

```json
{
  "cache": {
    "hits": 142,
    "misses": 38,
    "evictions": 0,
    "size": 38
  },
  "rate_limiter": {
    "tokens_available": 97.5,
    "capacity": 100,
    "refill_rate": 10.0,
    "acquired": 45,
    "waited": 0
  }
}
```

### Landing Page

```
GET /
```

Returns an HTML page with a team selector form for interactive use.

## Supported Teams

All 30 MLB teams are supported using standard abbreviations:

| AL East | AL Central | AL West | NL East | NL Central | NL West |
|---------|------------|---------|---------|------------|---------|
| BAL | CLE | HOU | ATL | CHC | ARI |
| BOS | CWS | LAA | MIA | CIN | COL |
| NYY | DET | OAK | NYM | MIL | LAD |
| TB  | KC  | SEA | PHI | PIT | SD  |
| TOR | MIN | TEX | WSH | STL | SF  |

## Caching

The application implements intelligent caching to minimize MLB API calls:

| Game Status | Cache TTL |
|-------------|-----------|
| In Progress | 1 minute  |
| Pre-Game / Scheduled | 5 minutes |
| Final | 1 hour |
| Postponed / Suspended | 30 minutes |

Player and pitcher details are cached for 24 hours.

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run unit tests only
uv run pytest -m unit

# Run integration tests only
uv run pytest -m integration

# Run with verbose output
uv run pytest -v
```

### Linting

```bash
uv run ruff check app.py mlb/*.py
```

### Project Structure

```
mlb-lineups/
├── app.py              # Flask application entry point
├── mlb/
│   ├── api_client.py   # MLB Stats API client
│   ├── cache.py        # Caching and rate limiting
│   ├── formatters.py   # Display formatting helpers
│   └── teams.py        # Team constants and validation
├── templates/          # Jinja2 HTML templates
├── tests/              # Test suite
└── pyproject.toml      # Project metadata and dependencies
```

## Note

This application uses the unofficial MLB Stats API. Lineup availability varies:
- **Probable pitchers**: Usually announced 1-3 days before the game
- **Starting lineups**: Typically available 1-3 hours before first pitch

## License

MIT
