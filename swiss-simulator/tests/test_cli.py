import json

from swiss.cli import main


def test_cli_simulate(tmp_path, seeds: dict[str, int]) -> None:
    seed_path = tmp_path / "seeds.json"
    probabilities_path = tmp_path / "probabilities.json"
    output_path = tmp_path / "result.json"
    seed_path.write_text(json.dumps(seeds))
    matrix = {
        team: {opponent: 0.5 for opponent in seeds if opponent != team}
        for team in seeds
    }
    probabilities_path.write_text(json.dumps({"bo1": matrix, "bo3": matrix}))
    assert main(
        [
            "simulate",
            "--input",
            str(probabilities_path),
            "--seeds",
            str(seed_path),
            "--random-seed",
            "42",
            "--output",
            str(output_path),
        ]
    ) == 0
    assert len(json.loads(output_path.read_text())["matches"]) == 33

