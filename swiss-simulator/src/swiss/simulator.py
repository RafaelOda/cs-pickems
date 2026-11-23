from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from .models import Match, MatchFormat, SimulationResult, TeamState
from .pairing import pair_round


class SimulationError(ValueError):
    pass


class RandomSource(Protocol):
    def random(self) -> float: ...


@dataclass(frozen=True)
class ReplayOutcome:
    round_number: int
    team_a: str
    team_b: str
    winner: str


@dataclass(frozen=True)
class ProbabilityMatrices:
    bo1: Mapping[str, Mapping[str, float]]
    bo3: Mapping[str, Mapping[str, float]]

    def probability(self, team_a: str, team_b: str, match_format: MatchFormat) -> float:
        matrix = self.bo1 if match_format == "bo1" else self.bo3
        try:
            value = float(matrix[team_a][team_b])
        except (KeyError, TypeError, ValueError) as error:
            raise SimulationError(
                f"missing {match_format} probability for {team_a!r} vs {team_b!r}"
            ) from error
        if not 0.0 <= value <= 1.0:
            raise SimulationError(
                f"probability for {team_a!r} vs {team_b!r} must be in [0, 1]"
            )
        return value

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> ProbabilityMatrices:
        """Parse map-of-maps or labelled square-matrix probability-engine output."""
        if not isinstance(payload, Mapping):
            raise SimulationError("probability input must be a JSON object")
        container = payload.get("probabilities", payload)
        if not isinstance(container, Mapping):
            raise SimulationError("probabilities must be a JSON object")
        bo1 = _extract_matrix(container, payload, "bo1")
        bo3 = _extract_matrix(container, payload, "bo3")
        return cls(bo1=bo1, bo3=bo3)


def _extract_matrix(
    container: Mapping[str, Any], root: Mapping[str, Any], name: str
) -> dict[str, dict[str, float]]:
    aliases = (name, name.upper(), f"{name}_matrix", f"{name}Matrix")
    raw = next((container[key] for key in aliases if key in container), None)
    if raw is None:
        raise SimulationError(f"probability input is missing a {name} matrix")
    if isinstance(raw, Mapping):
        try:
            return {
                str(team): {str(opponent): float(value) for opponent, value in row.items()}
                for team, row in raw.items()
            }
        except (AttributeError, TypeError, ValueError) as error:
            raise SimulationError(f"invalid map-based {name} matrix") from error
    if isinstance(raw, list):
        team_ids = root.get("teams") or container.get("teams") or root.get("team_ids")
        if not isinstance(team_ids, list) or not all(isinstance(team, str) for team in team_ids):
            raise SimulationError(f"labelled team list is required for array-based {name} matrix")
        if len(raw) != len(team_ids) or any(
            not isinstance(row, list) or len(row) != len(team_ids) for row in raw
        ):
            raise SimulationError(f"{name} matrix must be square and match the team list")
        try:
            return {
                team: {opponent: float(raw[i][j]) for j, opponent in enumerate(team_ids)}
                for i, team in enumerate(team_ids)
            }
        except (TypeError, ValueError) as error:
            raise SimulationError(f"invalid value in {name} matrix") from error
    raise SimulationError(f"unsupported {name} matrix representation")


class SwissSimulator:
    def __init__(
        self,
        seeds: Mapping[str, int],
        probabilities: ProbabilityMatrices | None = None,
        *,
        random_seed: int | None = None,
        rng: RandomSource | None = None,
    ) -> None:
        self._validate_seeds(seeds)
        self.teams = {
            str(team_id): TeamState(str(team_id), int(seed))
            for team_id, seed in seeds.items()
        }
        self.probabilities = probabilities
        if random_seed is not None and rng is not None:
            raise SimulationError("provide random_seed or rng, not both")
        self.rng = rng if rng is not None else random.Random(random_seed)

    @staticmethod
    def _validate_seeds(seeds: Mapping[str, int]) -> None:
        if len(seeds) != 16 or len({str(team) for team in seeds}) != 16:
            raise SimulationError("exactly 16 unique string team identifiers are required")
        if any(not isinstance(team, str) or not team for team in seeds):
            raise SimulationError("team identifiers must be non-empty strings")
        if set(seeds.values()) != set(range(1, 17)):
            raise SimulationError("initial seeds must be the unique integers 1 through 16")

    def simulate(self) -> SimulationResult:
        if self.probabilities is None:
            raise SimulationError("probability matrices are required for probabilistic simulation")
        return self._run(None)

    def replay(self, outcomes: Sequence[ReplayOutcome]) -> SimulationResult:
        return self._run(list(outcomes))

    def _run(self, replay: list[ReplayOutcome] | None) -> SimulationResult:
        if any(team.wins or team.losses or team.opponents for team in self.teams.values()):
            raise SimulationError("a SwissSimulator instance can only be run once")
        matches: list[Match] = []
        replay_remaining = list(replay) if replay is not None else None
        for round_number in range(1, 6):
            generated = pair_round(round_number, self.teams)
            for team_a, team_b in generated:
                match_format = self._match_format(team_a, team_b)
                probability: float | None = None
                if replay_remaining is not None:
                    if not replay_remaining:
                        raise SimulationError(
                            f"replay ended before round {round_number} pairing {team_a} vs {team_b}"
                        )
                    actual_pair = frozenset((team_a, team_b))
                    outcome_index = next(
                        (
                            index
                            for index, outcome in enumerate(replay_remaining)
                            if outcome.round_number == round_number
                            and frozenset((outcome.team_a, outcome.team_b)) == actual_pair
                        ),
                        None,
                    )
                    if outcome_index is None:
                        expected = next(
                            (
                                outcome
                                for outcome in replay_remaining
                                if outcome.round_number == round_number
                            ),
                            replay_remaining[0],
                        )
                        raise SimulationError(
                            "historical pairing mismatch: generated round "
                            f"{round_number} "
                            f"{team_a} vs {team_b}, got round {expected.round_number} "
                            f"{expected.team_a} vs {expected.team_b}"
                        )
                    expected = replay_remaining.pop(outcome_index)
                    if expected.winner not in actual_pair:
                        raise SimulationError("replay winner must be one of the paired teams")
                    winner = expected.winner
                else:
                    assert self.probabilities is not None
                    probability = self.probabilities.probability(
                        team_a, team_b, match_format
                    )
                    winner = team_a if self.rng.random() < probability else team_b
                loser = team_b if winner == team_a else team_a
                self._record_result(winner, loser)
                matches.append(
                    Match(
                        round_number,
                        team_a,
                        team_b,
                        match_format,
                        winner,
                        loser,
                        probability,
                    )
                )
        if replay_remaining:
            raise SimulationError(
                f"replay contains {len(replay_remaining)} unused match outcome(s)"
            )
        if any(team.active for team in self.teams.values()):
            raise SimulationError("stage did not terminate after five rounds")
        return SimulationResult(self.teams, matches)

    def _match_format(self, team_a: str, team_b: str) -> MatchFormat:
        a = self.teams[team_a]
        b = self.teams[team_b]
        if a.wins == 2 or a.losses == 2 or b.wins == 2 or b.losses == 2:
            return "bo3"
        return "bo1"

    def _record_result(self, winner_id: str, loser_id: str) -> None:
        winner = self.teams[winner_id]
        loser = self.teams[loser_id]
        if not winner.active or not loser.active:
            raise SimulationError("inactive team was scheduled for a match")
        winner.wins += 1
        loser.losses += 1
        winner.opponents.append(loser_id)
        loser.opponents.append(winner_id)
