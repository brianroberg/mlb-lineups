# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build/Test Commands
- Install dependencies: `pip install -r requirements.txt`
- Run Flask app (development): `python app.py`
- Run all tests: `pytest`
- Run unit tests only: `pytest -m unit`
- Run integration tests only: `pytest -m integration`
- Run specific test: `pytest tests/test_unit.py::TestMLBTeams::test_mlb_teams_has_30_teams`
- Lint code: `ruff check app.py mlb/*.py`

## Flask Web Application

### Running the App
- Development server: `python app.py` (runs on http://localhost:5000)
- Production: `gunicorn -w 4 -b 0.0.0.0:5000 app:app`

### API Endpoints
- `GET /api/lineup?team=NYM&date=2025-04-15` - Get lineup data as JSON
- `GET /api/lineup?team=NYM&format=html` - Get lineup data as HTML page
- `GET /` - Landing page with team selector form

Query Parameters:
- `team` (required): 3-letter team abbreviation (e.g., NYM, LAD, NYY)
- `date` (optional): Date in YYYY-MM-DD format, defaults to today
- `format` (optional): Response format, 'json' (default) or 'html'

## Project Structure
- `app.py` - Flask application entry point
- `mlb/` - Core MLB data modules
  - `teams.py` - Team constants and validation
  - `api_client.py` - MLB Stats API client functions
  - `formatters.py` - Display formatting helpers
- `templates/` - Jinja2 HTML templates
- `tests/` - Test suite (unit and integration tests)

## Code Style Guidelines
- Follow PEP 8 conventions for Python code
- Imports: standard library first, then third-party, then local modules
- Use type hints in function signatures
- Include docstrings for all functions and classes
- Error handling: use try/except blocks for external API calls
- Use descriptive variable names
- Organize constants at the top of modules
- Maintain test coverage for new features
- IMPORTANT: Always run the Ruff linter before committing changes: `ruff check --fix app.py mlb/*.py`
