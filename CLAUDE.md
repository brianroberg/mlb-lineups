# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build/Test Commands
- Install all dependencies (runtime + dev): `uv sync --frozen`
- Install with production server: `uv sync --frozen --group prod`
- Update dependencies (re-resolve and regenerate lock file): `uv sync`
- Add a new runtime dependency: `uv add <package>`
- Add a new dev dependency: `uv add --group dev <package>`
- Run Flask app (development): `uv run python app.py`
- Run all tests: `uv run pytest`
- Run unit tests only: `uv run pytest -m unit`
- Run integration tests only: `uv run pytest -m integration`
- Run specific test: `uv run pytest tests/test_unit.py::TestMLBTeams::test_mlb_teams_has_30_teams`
- Lint code: `uv run ruff check app.py mlb/*.py`

## Flask Web Application

### Running the App
- Development server: `uv run python app.py` (runs on http://localhost:5000)
- Production: `uv sync --frozen --group prod && uv run gunicorn -w 4 -b 0.0.0.0:5000 app:app`

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
- IMPORTANT: Always run the Ruff linter before committing changes: `uv run ruff check --fix app.py mlb/*.py`
