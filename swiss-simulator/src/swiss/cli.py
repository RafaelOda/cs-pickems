from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .simulator import ProbabilityMatrices, ReplayOutcome, SimulationError, SwissSimulator


def _read_json(path: str) -> Any:
    try:
        with Path(path).open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise SimulationError(f"could not read JSON from {path!r}: {error}") from error


def _parse_seeds(payload: Any) -> dict[str, int]:
    if isinstance(payload, dict) and "seeds" in payload:
        payload = payload["seeds"]
    if isinstance(payload, dict):
        try:
            return {str(team): int(seed) for team, seed in payload.items()}
        except (TypeError, ValueError) as error:
            raise SimulationError("invalid map-based seed input") from error
    if isinstance(payload, list):
        try:
            return {
                str(item.get("team_id", item.get("team"))): int(item["seed"])
                for item in payload
            }
        except (KeyError, TypeError, ValueError) as error:
            raise SimulationError("invalid list-based seed input") from error
    raise SimulationError("seeds must be an object or a list of team/seed objects")


def _parse_replay(payload: Any) -> list[ReplayOutcome]:
    if isinstance(payload, dict):
        payload = payload.get("matches", payload.get("outcomes"))
    if not isinstance(payload, list):
        raise SimulationError("replay input must be a list or contain a matches list")
    try:
        return [
            ReplayOutcome(
                int(item.get("round_number", item.get("round"))),
                str(item["team_a"]),
                str(item["team_b"]),
                str(item["winner"]),
            )
            for item in payload
        ]
    except (KeyError, TypeError, ValueError) as error:
        raise SimulationError("invalid replay match entry") from error


def _write_result(path: str | None, result: dict[str, Any]) -> None:
    serialized = json.dumps(result, indent=2) + "\n"
    if path:
        try:
            Path(path).write_text(serialized, encoding="utf-8")
        except OSError as error:
            raise SimulationError(f"could not write output to {path!r}: {error}") from error
    else:
        sys.stdout.write(serialized)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simulate a CS Major Swiss stage")
    subparsers = parser.add_subparsers(dest="command", required=True)

    simulate = subparsers.add_parser("simulate", help="run a probabilistic simulation")
    simulate.add_argument("--input", required=True, help="probability-engine JSON")
    simulate.add_argument("--seeds", required=True, help="initial seeds JSON")
    simulate.add_argument("--random-seed", type=int)
    simulate.add_argument("--output")

    replay = subparsers.add_parser("replay", help="replay predetermined historical results")
    replay.add_argument("--results", required=True, help="historical results JSON")
    replay.add_argument("--seeds", required=True, help="initial seeds JSON")
    replay.add_argument("--output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        seeds = _parse_seeds(_read_json(args.seeds))
        if args.command == "simulate":
            matrices = ProbabilityMatrices.from_json(_read_json(args.input))
            result = SwissSimulator(
                seeds, matrices, random_seed=args.random_seed
            ).simulate()
        else:
            outcomes = _parse_replay(_read_json(args.results))
            result = SwissSimulator(seeds).replay(outcomes)
        _write_result(args.output, result.to_dict())
        return 0
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
