# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build/Test Commands
- Install dependencies: `pip install -r requirements.txt`
- Run script: `python print_lineups.py [--team TEAM] [--date YYYY-MM-DD]`
- Run all tests: `pytest`
- Run unit tests only: `pytest -m unit`
- Run integration tests only: `pytest -m integration`
- Run specific test: `pytest tests/test_unit.py::TestMLBTeams::test_mlb_teams_has_30_teams`
- Lint code: `ruff check print_lineups.py`

## Code Style Guidelines
- Follow PEP 8 conventions for Python code
- Imports: standard library first, then third-party, then local modules
- Use type hints in function signatures
- Include docstrings for all functions and classes
- Error handling: use try/except blocks for external API calls
- Use descriptive variable names
- Organize constants at the top of modules
- Maintain test coverage for new features
- IMPORTANT: Always run the Ruff linter before committing changes: `ruff check --fix print_lineups.py`