# CS Major Swiss Simulator

A deterministic, independently testable implementation of Valve's 16-team
Counter-Strike Major Swiss stage. It contains no VRS calculation or probability
model: initial stage seeds and matchup probabilities are inputs.

The implementation follows the current [Valve Major Supplemental Rulebook](https://github.com/ValveSoftware/counter-strike_rules_and_regs/blob/main/major-supplemental-rulebook.md):

- round 1 pairs seeds 1–9, 2–10, …, 8–16;
- rounds 2 and 3 pair the highest current seed with the lowest available
  non-rematch opponent in the same record group;
- rounds 4 and 5 select the first rematch-free layout in Valve's explicit
  15-row pairing-priority table;
- current seed within a W-L group is Buchholz descending, then initial stage
  seed ascending;
- advancement/elimination matches are Bo3; all others are Bo1.

## Setup and tests

Python 3.11 or newer and `uv` are required.

```bash
cd swiss-simulator
uv sync --dev
uv run pytest
```

## Input formats

Seeds may be a direct map:

```json
{"Spirit": 1, "Vitality": 2, "...": 16}
```

or `{ "seeds": { ... } }`, or a list of `{ "team": "Spirit", "seed": 1 }`
objects. There must be exactly 16 unique string team IDs and seeds 1–16.

Probability JSON accepts the probability engine's map-of-maps shape:

```json
{
  "bo1": {"Spirit": {"Vitality": 0.55}},
  "bo3": {"Spirit": {"Vitality": 0.58}}
}
```

The matrices may also be nested under `probabilities`. Labelled square arrays are
accepted as `teams` plus `bo1_matrix` and `bo3_matrix`. Values mean the probability
that the row team beats the column team and must be between 0 and 1. Only entries
for matchups that are actually played are required.

## CLI

```bash
uv run python -m swiss.cli simulate \
  --input probabilities.json \
  --seeds seeds.json \
  --random-seed 42 \
  --output simulation.json
```

For a historical replay:

```bash
uv run python -m swiss.cli replay \
  --results austin-2025-stage-1.json \
  --seeds austin-2025-stage-1-seeds.json \
  --output replay.json
```

Replay data is a list (or an object with a `matches` list) in generated pairing
order. Team order within one pairing is immaterial:

```json
{
  "matches": [
    {"round": 1, "team_a": "Seed 1", "team_b": "Seed 9", "winner": "Seed 1"}
  ]
}
```

Replay entries may appear in any order within or across rounds. The replay stops
with a descriptive error if a recorded round does not contain a pairing generated
by the rules. Recorded pairings are never substituted into the simulation.

The automated regression suite includes the complete Austin 2025 Stage 1 ledger
published by [HLTV](https://www.hltv.org/events/8436/blasttv-austin-major-2025-stage-1),
including the post-withdrawal field with Legacy.

## Output

Output JSON includes every team's record, Buchholz, opponents, and final status;
the 3–0, other advancing, 0–3, and eliminated groups; and all 33 matches with
round, teams, format, winner, loser, and the probability used when applicable.
