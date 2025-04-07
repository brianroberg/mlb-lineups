# MLB Lineups

A command-line tool for displaying MLB game lineups, starting pitchers, and umpire information.

## Features

- Display lineups for any MLB team
- Show batting order with player positions and jersey numbers
- View starting pitchers with jersey numbers and throwing arm (left/right)
- See game venue and umpire information
- Specify a date to look up past or future games
- No scores shown, so no risk of spoilers when watching time-shifted
- **New:** Shows probable pitchers even when lineups aren't yet available

## Why I Wrote This
I enjoy scoring baseball games that I watch on TV, which means I need starting lineups. This script provides convenient access to all the information that needs to go onto a scorecard.

## Requirements

- Python 3.6+
- Required packages:
  - requests
  - pytz
  - MLB-StatsAPI
  - pytest (for test suite)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/mlb-lineups.git
   cd mlb-lineups
   ```

2. Create and activate a virtual environment (recommended):
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

Run the script with:

```
python print_lineups.py [options]
```

### Command-line Options

- `--team TEAM`: Team abbreviation (default: NYM)
  - Examples: NYM, STL, LAD, NYY, CHC, etc.
  - All 30 MLB teams are supported

- `--date DATE`: Game date in YYYY-MM-DD format
  - If not specified, defaults to today's date

### Examples

Display today's Mets lineup:
```
python print_lineups.py
```

Display today's Cardinals lineup:
```
python print_lineups.py --team STL
```

Display the Dodgers lineup for a specific date:
```
python print_lineups.py --team LAD --date 2025-04-15
```

## Output

The program displays:
- Teams playing, with venue
- Starting pitchers for both teams, with jersey numbers and throwing arm (when available)
- Selected team's lineup with jersey numbers and positions (when available)
- Opponent lineup with jersey numbers and positions (when available)
- Umpire crew with positions (when available)

### Example output with complete information:
```
===== TODAY'S GAME =====
Miami Marlins vs New York Mets
Ballpark: loanDepot park

----- STARTING PITCHERS -----
Miami Marlins: #47 Cal Quantrill (RHP)
New York Mets: #23 David Peterson (LHP)

----- MIA LINEUP -----
1. #9 Xavier Edwards (SS)
2. #6 Otto Lopez (2B)
3. #33 Eric Wagaman (DH)
4. #3 Derek Hill (CF)
5. #41 Jonah Bride (1B)
6. #54 Dane Myers (RF)
7. #34 Liam Hicks (C)
8. #46 Javier Sanoja (LF)
9. #21 Graham Pauley (3B)

----- OPPONENT LINEUP -----
1. #6 Starling Marte (DH)
2. #22 Juan Soto (RF)
3. #20 Pete Alonso (1B)
4. #9 Brandon Nimmo (LF)
5. #27 Mark Vientos (3B)
6. #13 Luis Torrens (C)
7. #7 Brett Baty (2B)
8. #2 Luisangel Acuña (SS)
9. #19 Jose Siri (CF)

----- UMPIRES -----
Home Plate: Nate Tomlinson
First Base: Mark Wegner
Second Base: Bruce Dreckman
Third Base: Shane Livensparger
```

### Example output for a future game:
```
===== GAME FOR 2025-04-15 =====
Los Angeles Dodgers vs San Francisco Giants
Ballpark: Dodger Stadium

----- STARTING PITCHERS -----
Los Angeles Dodgers: Yoshinobu Yamamoto (RHP)
San Francisco Giants: Logan Webb (RHP)

Lineups not yet available.
```

## Note

This tool uses the MLB Stats API to retrieve game data. For upcoming games, probable pitchers are usually announced several days in advance, while lineups typically become available a few hours before game time.

## Development

### Testing
The project includes unit and integration tests. Run them with:
```
python -m pytest
```

Or run specific test categories:
```
python -m pytest -m unit
python -m pytest -m integration
```

## License

MIT