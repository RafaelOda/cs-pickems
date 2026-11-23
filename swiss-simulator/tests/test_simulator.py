from __future__ import annotations

import random

import pytest

from swiss.simulator import (
    ProbabilityMatrices,
    ReplayOutcome,
    SimulationError,
    SwissSimulator,
)


def test_complete_stage_invariants(
    seeds: dict[str, int], even_probabilities: ProbabilityMatrices
) -> None:
    result = SwissSimulator(seeds, even_probabilities, random_seed=42).simulate()
    assert len(result.three_zero) == 2
    assert len(result.advanced_three_one_or_two) == 6
    assert len(result.advanced) == 8
    assert len(result.zero_three) == 2
    assert len(result.eliminated) == 8
    assert len(result.matches) == 33
    assert all(team.wins == 3 or team.losses == 3 for team in result.teams.values())
    assert all(match.winner in (match.team_a, match.team_b) for match in result.matches)


def test_match_formats_and_no_play_after_terminal_record(
    seeds: dict[str, int], even_probabilities: ProbabilityMatrices
) -> None:
    result = SwissSimulator(seeds, even_probabilities, random_seed=7).simulate()
    records = {team: [0, 0] for team in seeds}
    for match in result.matches:
        expected = "bo3" if any(
            records[team][0] == 2 or records[team][1] == 2
            for team in (match.team_a, match.team_b)
        ) else "bo1"
        assert match.format == expected
        assert all(records[team][0] < 3 and records[team][1] < 3 for team in (match.team_a, match.team_b))
        records[match.winner][0] += 1
        records[match.loser][1] += 1


def test_fixed_seed_is_deterministic(
    seeds: dict[str, int], even_probabilities: ProbabilityMatrices
) -> None:
    first = SwissSimulator(seeds, even_probabilities, random_seed=123).simulate().to_dict()
    second = SwissSimulator(seeds, even_probabilities, random_seed=123).simulate().to_dict()
    assert first == second


def test_injected_rng_is_supported(
    seeds: dict[str, int], even_probabilities: ProbabilityMatrices
) -> None:
    result = SwissSimulator(seeds, even_probabilities, rng=random.Random(4)).simulate()
    assert len(result.matches) == 33


def test_replay_validates_pairings(
    seeds: dict[str, int], even_probabilities: ProbabilityMatrices
) -> None:
    generated = SwissSimulator(seeds, even_probabilities, random_seed=8).simulate()
    replay = [
        ReplayOutcome(match.round_number, match.team_b, match.team_a, match.winner)
        for match in generated.matches
    ]
    random.Random(88).shuffle(replay)
    replayed = SwissSimulator(seeds).replay(replay)
    assert [(match.team_a, match.team_b) for match in replayed.matches] == [
        (match.team_a, match.team_b) for match in generated.matches
    ]


def test_replay_pairing_mismatch_fails_clearly(seeds: dict[str, int]) -> None:
    replay = [ReplayOutcome(1, "team-1", "team-10", "team-1")]
    with pytest.raises(SimulationError, match="historical pairing mismatch"):
        SwissSimulator(seeds).replay(replay)


def test_probability_parser_supports_labelled_arrays(seeds: dict[str, int]) -> None:
    teams = list(seeds)
    payload = {
        "teams": teams,
        "bo1_matrix": [[0.5] * 16 for _ in teams],
        "bo3_matrix": [[0.5] * 16 for _ in teams],
    }
    matrices = ProbabilityMatrices.from_json(payload)
    assert matrices.probability("team-1", "team-2", "bo1") == 0.5
