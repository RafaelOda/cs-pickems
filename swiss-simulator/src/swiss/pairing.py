from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence

from .buchholz import seeded_order
from .models import TeamState


class PairingError(ValueError):
    pass


# Valve Major Supplemental Rulebook order. Positions are one-based mid-stage seeds.
LATE_ROUND_PRIORITIES: tuple[tuple[tuple[int, int], ...], ...] = (
    ((1, 6), (2, 5), (3, 4)),
    ((1, 6), (2, 4), (3, 5)),
    ((1, 5), (2, 6), (3, 4)),
    ((1, 5), (2, 4), (3, 6)),
    ((1, 4), (2, 6), (3, 5)),
    ((1, 4), (2, 5), (3, 6)),
    ((1, 6), (2, 3), (4, 5)),
    ((1, 5), (2, 3), (4, 6)),
    ((1, 3), (2, 6), (4, 5)),
    ((1, 3), (2, 5), (4, 6)),
    ((1, 4), (2, 3), (5, 6)),
    ((1, 3), (2, 4), (5, 6)),
    ((1, 2), (3, 6), (4, 5)),
    ((1, 2), (3, 5), (4, 6)),
    ((1, 2), (3, 4), (5, 6)),
)


def initial_pairings(teams: Mapping[str, TeamState]) -> list[tuple[str, str]]:
    by_seed = {team.initial_seed: team.team_id for team in teams.values()}
    if set(by_seed) != set(range(1, 17)):
        raise PairingError("initial seeds must contain every integer from 1 through 16")
    return [(by_seed[seed], by_seed[seed + 8]) for seed in range(1, 9)]


def _is_rematch(a: TeamState, b: TeamState) -> bool:
    return b.team_id in a.opponents


def _high_low_pairings(ordered: Sequence[TeamState]) -> list[tuple[str, str]]:
    """Rounds 2/3: highest seed faces lowest available non-rematch."""
    def search(
        remaining: tuple[TeamState, ...],
    ) -> tuple[int, tuple[int, ...], list[tuple[str, str]]]:
        if not remaining:
            return 0, (), []
        high, rest = remaining[0], remaining[1:]
        candidates = list(range(len(rest) - 1, -1, -1))
        best: tuple[int, tuple[int, ...], list[tuple[str, str]]] | None = None
        for priority, opponent_index in enumerate(candidates):
            opponent = rest[opponent_index]
            tail = rest[:opponent_index] + rest[opponent_index + 1 :]
            rematches, choices, pairs = search(tail)
            candidate = (
                rematches + int(_is_rematch(high, opponent)),
                (priority,) + choices,
                [(high.team_id, opponent.team_id), *pairs],
            )
            if best is None or candidate[:2] < best[:2]:
                best = candidate
        assert best is not None
        return best

    # Minimize rematches first. Among equally legal solutions, preserve Valve's
    # highest-versus-lowest priority at every successive choice.
    return search(tuple(ordered))[2]


def _priority_pairings(ordered: Sequence[TeamState]) -> list[tuple[str, str]]:
    if len(ordered) != 6:
        raise PairingError(f"late-round record groups must contain 6 teams, got {len(ordered)}")
    for layout in LATE_ROUND_PRIORITIES:
        candidate = [(ordered[a - 1], ordered[b - 1]) for a, b in layout]
        if all(not _is_rematch(a, b) for a, b in candidate):
            return [(a.team_id, b.team_id) for a, b in candidate]
    # The rulebook says to select the top row that does not rematch. A legal Swiss
    # history should always have one; failing loudly is safer than inventing a rule.
    raise PairingError("no Valve priority-table layout avoids a rematch")


def pair_round(
    round_number: int, teams: Mapping[str, TeamState]
) -> list[tuple[str, str]]:
    if round_number == 1:
        return initial_pairings(teams)
    if round_number not in range(2, 6):
        raise PairingError(f"round number must be between 1 and 5, got {round_number}")

    groups: dict[tuple[int, int], list[TeamState]] = defaultdict(list)
    for team in teams.values():
        if team.active:
            groups[team.record].append(team)

    pairings: list[tuple[str, str]] = []
    for record in sorted(groups, key=lambda item: (-item[0], item[1])):
        ordered = seeded_order(groups[record], teams)
        if len(ordered) % 2:
            raise PairingError(f"record group {record} contains an odd number of teams")
        if round_number in (2, 3):
            pairings.extend(_high_low_pairings(ordered))
        else:
            pairings.extend(_priority_pairings(ordered))
    return pairings
