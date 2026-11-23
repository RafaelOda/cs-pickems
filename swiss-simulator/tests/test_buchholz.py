from swiss.buchholz import buchholz_score, seeded_order
from swiss.models import TeamState


def test_buchholz_sums_current_opponent_records() -> None:
    teams = {
        "a": TeamState("a", 1, opponents=["b", "c"]),
        "b": TeamState("b", 2, wins=2, losses=0),
        "c": TeamState("c", 3, wins=1, losses=1),
    }
    assert buchholz_score(teams["a"], teams) == 2


def test_seed_breaks_equal_buchholz_tie() -> None:
    teams = {"a": TeamState("a", 2), "b": TeamState("b", 1)}
    assert [team.team_id for team in seeded_order(list(teams.values()), teams)] == [
        "b",
        "a",
    ]

