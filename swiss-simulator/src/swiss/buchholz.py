from __future__ import annotations

from collections.abc import Mapping

from .models import TeamState


def buchholz_score(team: TeamState, teams: Mapping[str, TeamState]) -> int:
    """Return the sum of each prior opponent's current wins minus losses."""
    return sum(teams[opponent].wins - teams[opponent].losses for opponent in team.opponents)


def seeded_order(
    teams_in_group: list[TeamState], teams: Mapping[str, TeamState]
) -> list[TeamState]:
    """Order a single W-L group by Buchholz, then initial stage seed."""
    return sorted(
        teams_in_group,
        key=lambda team: (-buchholz_score(team, teams), team.initial_seed),
    )

