import argparse
import sys

from .chesscom import ChessComError, get_player_games


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Retrieve a player's completed Chess.com games."
    )
    parser.add_argument("username", help="Chess.com username")
    args = parser.parse_args(argv)
    username = args.username.strip()
    if not username:
        parser.error("A Chess.com username is required.")

    print(f"Fetching games for {username}...", flush=True)
    try:
        games = get_player_games(username)
    except (ChessComError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Download cancelled.", file=sys.stderr)
        return 130

    print(f"Total games: {len(games)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
