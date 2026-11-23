from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


MatchFormat = Literal["bo1", "bo3"]


@dataclass
class TeamState:
    team_id: str
    initial_seed: int
    wins: int = 0
    losses: int = 0
    opponents: list[str] = field(default_factory=list)

    @property
    def record(self) -> tuple[int, int]:
        return self.wins, self.losses

    @property
    def active(self) -> bool:
        return self.wins < 3 and self.losses < 3

    def to_dict(self, *, buchholz: int) -> dict[str, Any]:
        return {
            "team_id": self.team_id,
            "initial_seed": self.initial_seed,
            "wins": self.wins,
            "losses": self.losses,
            "record": f"{self.wins}-{self.losses}",
            "buchholz": buchholz,
            "opponents": list(self.opponents),
            "status": "advanced" if self.wins == 3 else "eliminated",
        }


@dataclass(frozen=True)
class Match:
    round_number: int
    team_a: str
    team_b: str
    format: MatchFormat
    winner: str
    loser: str
    probability_team_a: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SimulationResult:
    teams: dict[str, TeamState]
    matches: list[Match]

    @property
    def three_zero(self) -> list[str]:
        return self._teams_with_record(3, 0)

    @property
    def advanced(self) -> list[str]:
        return self._teams_matching(lambda team: team.wins == 3)

    @property
    def advanced_three_one_or_two(self) -> list[str]:
        return self._teams_matching(
            lambda team: team.wins == 3 and team.losses in (1, 2)
        )

    @property
    def zero_three(self) -> list[str]:
        return self._teams_with_record(0, 3)

    @property
    def eliminated(self) -> list[str]:
        return self._teams_matching(lambda team: team.losses == 3)

    def _teams_with_record(self, wins: int, losses: int) -> list[str]:
        return self._teams_matching(
            lambda team: team.wins == wins and team.losses == losses
        )

    def _teams_matching(self, predicate: Any) -> list[str]:
        return [
            team.team_id
            for team in sorted(self.teams.values(), key=lambda item: item.initial_seed)
            if predicate(team)
        ]

    def to_dict(self) -> dict[str, Any]:
        from .buchholz import buchholz_score

        return {
            "teams": {
                team_id: team.to_dict(buchholz=buchholz_score(team, self.teams))
                for team_id, team in sorted(
                    self.teams.items(), key=lambda item: item[1].initial_seed
                )
            },
            "three_zero": self.three_zero,
            "advanced_three_one_or_two": self.advanced_three_one_or_two,
            "advanced": self.advanced,
            "zero_three": self.zero_three,
            "eliminated": self.eliminated,
            "matches": [match.to_dict() for match in self.matches],
        }

