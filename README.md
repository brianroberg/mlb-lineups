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
New York Mets vs. Minnesota Twins
Ballpark: Target Field
Game Time: 7:40 PM EDT

----- STARTING PITCHERS -----
New York Mets (AWAY): #35 Clay Holmes (RHP)
Minnesota Twins (HOME): #41 Joe Ryan (RHP)

----- NYM LINEUP (AWAY) -----
1. #12 Francisco Lindor (SS)
2. #22 Juan Soto (RF)
3. #20 Pete Alonso (1B)
4. #9 Brandon Nimmo (LF)
5. #27 Mark Vientos (3B)
6. #3 Jesse Winker (DH)
7. #13 Luis Torrens (C)
8. #15 Tyrone Taylor (CF)
9. #2 Luisangel Acuña (2B)

----- Twins LINEUP (HOME) -----
1. #47 Edouard Julien (DH)
2. #25 Byron Buxton (CF)
3. #50 Willi Castro (2B)
4. #38 Matt Wallner (RF)
5. #4 Carlos Correa (SS)
6. #9 Trevor Larnach (LF)
7. #13 Ty France (1B)
8. #2 Brooks Lee (3B)
9. #8 Christian Vázquez (C)

----- UMPIRES -----
Home Plate: Adam Hamari
First Base: Nestor Ceja
Second Base: Todd Tichenor
Third Base: Hunter Wendelstedt
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