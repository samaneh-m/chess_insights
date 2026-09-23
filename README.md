# Chess Insights
Chess Insights is a Python command-line application that downloads a player's completed games from Chess.com, analyzes their results, and saves six charts and a text report. Chess.com is used as the only source of game data.

## Requirements
- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- An internet connection to download the games
- A Chess.com username

## Installation
Open a terminal in the project directory, where `/pyproject.toml` is located. Run each command separately:
```sh
uv venv --python 3.12
uv pip install -e .
```
The first command creates a local `.venv` environment using Python 3.12. The second command installs the project and its dependencies in editable mode.

## Usage
Replace `YOUR_USERNAME` with the Chess.com username to analyze:
```sh
uv run -m chess_insights YOUR_USERNAME
```
For example:
```sh
uv run -m chess_insights mbehzad
```
To see the available command-line options:
```sh
uv run -m chess_insights --help
```
The program downloads the available monthly game archives one by one, processes the games, and generates the outputs. Accounts with long histories may take longer to process.

## Outputs
The generated files are saved in the `outputs/` directory, relative to where the program is run. Running the program again replaces files with the same names, even when a different username is used.

| File | Contents |
| --- | --- |
| `overall_results.png` | Counts of wins, losses, and draws |
| `color_results.png` | Results when playing White and Black |
| `opening_results.png` | Win rates and game counts by ECO opening code |
| `rating_trend.png` | Rating history, with separate panels for each time class |
| `hourly_results.png` | Win rates and game counts by start hour in UTC |
| `duration_results.png` | Win rates and game counts by elapsed duration |
| `report.txt` | Text summary of the analyses |
The report summarizes up to five of the most-played known opening groups, while the opening chart includes all available groups.

## How results are calculated
- Results and ratings are calculated from the selected player's point of view.
- Win rate is `wins / (wins + losses + draws) * 100`. 
- Games with unknown results are not included in the win rate calculation, but they are still included in the total number of games.
- `N/A` means there are no known results from which to calculate a win rate; it is different from 0%.
- Games are grouped by ECO code when comparing openings. Missing or invalid ECO codes are grouped as `unknown`.
- Rating trends only use rated games with valid ratings, timestamps, and time classes. Bullet, blitz, rapid, and daily ratings are kept separate.
- Hourly statistics use the game's start time in UTC. Games without a valid start time are excluded from this analysis.
- Game duration is calculated using the time between the recorded start and end of the game.
- Live games are grouped as:
  - short: under 5 minutes
  - medium: 5 to under 15 minutes
  - long: 15 minutes or more
- Daily games and games with unknown duration or type are kept in separate groups.
These statistics describe the results only. Groups with only a few games may give misleading percentages.

## Reusing the package
The analysis functions can also be imported and used directly in Python:
```python
from chess_insights import calculate_overall_stats, get_processed_games
games = get_processed_games("mbehzad")
stats = calculate_overall_stats(games)
print(stats)
```

## Project structure
| Module | Responsibility |
| --- | --- |
| `chesscom.py` | Download monthly game archives |
| `parsing.py` | Extract player details, results, ratings, openings, and times |
| `processing.py` | Combine downloading and parsing |
| `analysis.py` | Calculate grouped statistics and rating trends |
| `visualization.py` | Create and save PNG charts |
| `reporting.py` | Generate the text summary |
| `__main__.py` | Run the application from the command line |

All modules are inside `/src/chess_insights`.

## Errors and limitations
- Invalid usernames or connection problems may cause the program to stop with an error message.
- Some game information may be missing from the Chess.com data.
- Opening charts may become large when many ECO groups are available.
- The program does not use a chess engine, so it does not evaluate individual moves.

## Data source
Game data is obtained through the [Chess.com Published Data API](https://www.chess.com/news/view/published-data-api).
