from pathlib import Path

P = Path(__file__).parent.parent / "prompts"


def test_cluster_prompt_demands_json_array():
    t = (P / "cluster.md").read_text()
    assert "JSON" in t and "occurrence_count" in t and "≥2" in t


def test_crosscheck_prompt_is_output_only():
    t = (P / "crosscheck.md").read_text()
    assert "do not write" in t.lower() and "output only" in t.lower()
