from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from swiss.buchholz import buchholz_score
from swiss.pairing import pair_round
from swiss.simulator import ReplayOutcome, SwissSimulator


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "fixtures"
    / "austin_2025_stage1_replay.json"
)


def _load_fixture() -> dict[str, Any]:
    with FIXTURE_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _pair(team_a: str, team_b: str) -> frozenset[str]:
    return frozenset((team_a, team_b))


def test_austin_2025_stage_one_historical_replay() -> None:
    fixture = _load_fixture()
    seeds = {
        team_id: initial_seed
        for initial_seed, team_id in enumerate(fixture["initialSeeds"], start=1)
    }
    simulator = SwissSimulator(seeds)
    matches_by_round: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for match in fixture["matches"]:
        matches_by_round[match["round"]].append(match)

    verified_matches = 0
    for round_number in range(1, 6):
        # Generate from current records, Buchholz, initial seeds, and opponent
        # history only. Fixture pairings are used solely as expected values.
        generated = pair_round(round_number, simulator.teams)
        expected_matches = matches_by_round[round_number]
        expected_by_pair = {
            _pair(match["teamA"], match["teamB"]): match
            for match in expected_matches
        }

        generated_pairs = {_pair(team_a, team_b) for team_a, team_b in generated}
        assert generated_pairs == set(expected_by_pair), (
            f"round {round_number} pairing mismatch: "
            f"missing={set(expected_by_pair) - generated_pairs}, "
            f"unexpected={generated_pairs - set(expected_by_pair)}"
        )
        assert len(generated) == len(expected_matches)

        for team_a, team_b in generated:
            historical = expected_by_pair[_pair(team_a, team_b)]
            team = simulator.teams[team_a]
            expected_format = (
                "bo3" if team.wins == 2 or team.losses == 2 else "bo1"
            )
            assert historical["format"] == expected_format, (
                f"round {round_number} format mismatch for {team_a} vs {team_b}: "
                f"generated {expected_format}, fixture has {historical['format']}"
            )

            winner = historical["winner"]
            loser = team_b if winner == team_a else team_a
            assert winner in (team_a, team_b)
            simulator._record_result(winner, loser)
            verified_matches += 1

        # Buchholz is dynamic: after every completed round, independently sum
        # each prior opponent's current record and compare with the implementation.
        for team in simulator.teams.values():
            independently_calculated = sum(
                simulator.teams[opponent].wins - simulator.teams[opponent].losses
                for opponent in team.opponents
            )
            assert buchholz_score(team, simulator.teams) == independently_calculated

    assert verified_matches == 33
    assert all(not team.active for team in simulator.teams.values())

    actual_final_records: dict[str, set[str]] = defaultdict(set)
    for team in simulator.teams.values():
        actual_final_records[f"{team.wins}-{team.losses}"].add(team.team_id)
    assert actual_final_records == {
        record: set(team_ids)
        for record, team_ids in fixture["expectedFinalRecords"].items()
    }

    # Exercise the public replay API with the same fixture after the independent
    # round-by-round validation, including its emitted match formats and standings.
    outcomes = [
        ReplayOutcome(
            match["round"], match["teamA"], match["teamB"], match["winner"]
        )
        for match in fixture["matches"]
    ]
    result = SwissSimulator(seeds).replay(outcomes)
    assert len(result.matches) == 33
    expected_formats = {
        (match["round"], _pair(match["teamA"], match["teamB"])): match["format"]
        for match in fixture["matches"]
    }
    assert all(
        match.format
        == expected_formats[(match.round_number, _pair(match.team_a, match.team_b))]
        for match in result.matches
    )
    assert {
        f"{team.wins}-{team.losses}": {
            item.team_id
            for item in result.teams.values()
            if item.record == team.record
        }
        for team in result.teams.values()
    } == actual_final_records
