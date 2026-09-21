"""Game prediction from assessment words (services/game_predictor.py + agent)."""
import os
import pytest

from app.services.game_predictor import rank_games, canon
from app.agents.game_predictor_agent import GamePredictorAgent


def m(expected, spoken=None):
    spoken = expected if spoken is None else spoken
    return {"expected": expected, "spoken": spoken, "correct": expected == spoken}


def word(target, matches, accuracy, patterns=None):
    return {"targetWord": target, "phonemeMatches": matches, "accuracy": accuracy,
            "errorPatterns": patterns or []}


FIVE_WORDS = [
    word("rabbit", [m("R", "W"), m("AE1"), m("B"), m("IH0"), m("T")], 70),
    word("rocket", [m("R", "W"), m("AA1"), m("K"), m("AH0"), m("T")], 72),
    word("cat", [m("K", "T"), m("AE1"), m("T")], 60,
         ["Velar Fronting (pronouncing back sound /K/ as front sound /T/)"]),
    word("car", [m("K"), m("AA1"), m("R", "")], 66,
         ["Final Consonant Deletion (dropping ending sounds)"]),
    word("sun", [m("S"), m("AH1"), m("N")], 95),
]


def test_canon_handles_stress_and_aliases():
    assert canon("AE1") == "AE"
    assert canon("HH") == "H"
    assert canon("DH") == "TH"
    assert canon("ER0") == "R"
    assert canon("AH0") is None      # not modelled -> ignored, never guessed
    assert canon("") is None and canon(None) is None


def test_r_errors_point_to_lions_roar_first():
    out = rank_games(FIVE_WORDS)
    assert out["words_analyzed"] == 5 and out["confidence"] == "good"
    assert out["plan"][0]["id"] == "chime_r"
    assert "R" in out["weak_sounds"]
    assert "rabbit" in out["plan"][0]["reason"] or "rocket" in out["plan"][0]["reason"]


def test_patterns_add_skill_games():
    ids = {g["id"] for g in rank_games(FIVE_WORDS, limit=10)["plan"]}
    assert "vm_minimal_pairs" in ids      # k->t swap / velar fronting
    assert "chime_ma" in ids              # final consonant deletion


def test_plan_is_capped_and_varied():
    out = rank_games(FIVE_WORDS, limit=4)
    assert 1 <= len(out["plan"]) <= 4
    fams = [g["family"] for g in out["plan"]]
    assert all(fams.count(f) <= 2 for f in set(fams))
    assert [g["priority"] for g in out["plan"]] == list(range(1, len(out["plan"]) + 1))


def test_clean_words_recommend_nothing():
    clean = [word("sun", [m("S"), m("AH1"), m("N")], 98), word("map", [m("M"), m("AE1"), m("P")], 96)]
    out = rank_games(clean)
    assert out["plan"] == [] and out["confidence"] == "low"


def test_snake_case_word_results_also_work():
    snake = [{"target_word": "rabbit", "accuracy": 60, "error_patterns": [],
              "phoneme_matches": [m("R", "W"), m("AE1"), m("B"), m("IH0"), m("T")]},
             {"target_word": "run", "accuracy": 60, "error_patterns": [],
              "phoneme_matches": [m("R", "W"), m("AH1"), m("N")]}]
    assert rank_games(snake)["plan"][0]["id"] == "chime_r"


def test_bad_input_never_raises():
    assert rank_games(None)["plan"] == []
    assert rank_games([None, "x", {"phonemeMatches": "nope"}])["plan"] == []


def test_agent_falls_back_to_rules_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    out = GamePredictorAgent().predict(FIVE_WORDS, "Ani")
    assert out["source"] == "rules" and out["plan"] and "\"r\"" in out["headline"]
