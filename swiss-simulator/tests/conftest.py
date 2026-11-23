from __future__ import annotations

import pytest

from swiss.simulator import ProbabilityMatrices


@pytest.fixture
def seeds() -> dict[str, int]:
    return {f"team-{seed}": seed for seed in range(1, 17)}


@pytest.fixture
def even_probabilities(seeds: dict[str, int]) -> ProbabilityMatrices:
    matrix = {
        team: {opponent: 0.5 for opponent in seeds if opponent != team}
        for team in seeds
    }
    return ProbabilityMatrices(bo1=matrix, bo3=matrix)

