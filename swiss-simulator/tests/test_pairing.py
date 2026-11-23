import pytest

from swiss.models import TeamState
from swiss.pairing import LATE_ROUND_PRIORITIES, PairingError, initial_pairings, pair_round


def _teams(count: int) -> dict[str, TeamState]:
    return {f"t{seed}": TeamState(f"t{seed}", seed) for seed in range(1, count + 1)}


def test_initial_pairings(seeds: dict[str, int]) -> None:
    teams = {team: TeamState(team, seed) for team, seed in seeds.items()}
    assert initial_pairings(teams) == [
        (f"team-{seed}", f"team-{seed + 8}") for seed in range(1, 9)
    ]


def test_round_two_uses_highest_against_lowest() -> None:
    teams = _teams(16)
    for seed in range(1, 9):
        teams[f"t{seed}"].wins = 1
    for seed in range(9, 17):
        teams[f"t{seed}"].losses = 1
    assert pair_round(2, teams) == [
        ("t1", "t8"), ("t2", "t7"), ("t3", "t6"), ("t4", "t5"),
        ("t9", "t16"), ("t10", "t15"), ("t11", "t14"), ("t12", "t13"),
    ]


def test_round_three_avoids_rematch_by_taking_next_lowest() -> None:
    teams = _teams(4)
    for team in teams.values():
        team.wins = team.losses = 1
    teams["t1"].opponents.append("t4")
    teams["t4"].opponents.append("t1")
    assert pair_round(3, teams) == [("t1", "t3"), ("t2", "t4")]


def test_round_three_looks_ahead_to_avoid_trapping_a_later_rematch() -> None:
    teams = _teams(4)
    for team in teams.values():
        team.wins = team.losses = 1
    teams["t2"].opponents.append("t3")
    teams["t3"].opponents.append("t2")
    assert pair_round(3, teams) == [("t1", "t3"), ("t2", "t4")]


def test_round_four_uses_first_legal_priority_row() -> None:
    teams = _teams(6)
    for team in teams.values():
        team.wins = 2
        team.losses = 1
    assert pair_round(4, teams) == [("t1", "t6"), ("t2", "t5"), ("t3", "t4")]


def test_round_four_falls_through_priority_table_for_rematch() -> None:
    teams = _teams(6)
    for team in teams.values():
        team.wins = 2
        team.losses = 1
        # Equal synthetic Buchholz contributions keep the intended seed order.
        team.opponents.append(team.team_id)
    teams["t2"].opponents = ["t5"]
    teams["t5"].opponents = ["t2"]
    assert pair_round(4, teams) == [("t1", "t6"), ("t2", "t4"), ("t3", "t5")]


def test_round_five_uses_same_official_table() -> None:
    assert len(LATE_ROUND_PRIORITIES) == 15
    teams = _teams(6)
    for team in teams.values():
        team.wins = team.losses = 2
    assert pair_round(5, teams) == [("t1", "t6"), ("t2", "t5"), ("t3", "t4")]


def test_late_round_fails_instead_of_inventing_rematch_priority() -> None:
    teams = _teams(6)
    for team in teams.values():
        team.wins = team.losses = 2
        team.opponents = [other for other in teams if other != team.team_id]
    with pytest.raises(PairingError, match="no Valve priority"):
        pair_round(5, teams)
