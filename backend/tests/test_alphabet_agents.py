"""Alphabet check agents: focus, VaakMirror planner, and the LangGraph wiring."""
import re
from pathlib import Path

import pytest

from app.services.alphabet_sounds import LETTERS, CORE_LETTERS, strip_stress
from app.agents.alphabet_focus_agent import AlphabetFocusAgent
from app.agents.vaakmirror_planner_agent import VaakMirrorPlannerAgent
from app.graph.alphabet_graph import build_letter_graph, build_plan_graph

TAXONOMY = Path(__file__).resolve().parents[2] / "frontend/src/vaakmirror/data/soundTaxonomy.js"


def m(expected, spoken=None):
    spoken = expected if spoken is None else spoken
    return {"expected": expected, "spoken": spoken, "correct": strip_stress(expected) == strip_stress(spoken)}


def res(letter, correct, heard=None):
    spec = LETTERS[letter]
    return {"letter": letter, "word": spec["word"], "sound_id": spec["vm"], "group": spec["group"],
            "status": "ok" if correct else "missed", "correct": correct, "heard_as": heard}


# -- catalog ---------------------------------------------------------------

@pytest.mark.skipif(not TAXONOMY.exists(), reason="frontend not checked out")
def test_every_letter_maps_to_a_real_vaakmirror_sound():
    ids = set(re.findall(r"id: '([a-z-]+)'", TAXONOMY.read_text()))
    bad = {k: v["vm"] for k, v in LETTERS.items() if v["vm"] not in ids}
    assert not bad, f"letters mapped to sound ids missing from soundTaxonomy.js: {bad}"


def test_catalog_is_consistent():
    assert set(CORE_LETTERS) <= set(LETTERS)
    for k, v in LETTERS.items():
        assert v["word"] and v["arpa"].isalpha()
        assert all(n in LETTERS for n in v["next"]), k


# -- focus agent -----------------------------------------------------------

def test_focus_picks_the_letters_own_sound_not_the_whole_word():
    state = {"letter": "B", "spoken_word": "ball", "accuracy": 60, "error_patterns": [],
             "phoneme_matches": [m("B"), m("AO1", "AA1"), m("L", "W")]}     # ball -> "baw"
    r = AlphabetFocusAgent().analyze(state)["letter_result"]
    assert r["status"] == "ok" and r["correct"] is True and r["score"] == 1.0
    assert r["word_accuracy"] == 60          # reported, but doesn't fail the letter


def test_focus_reports_what_was_heard_instead():
    state = {"letter": "K", "spoken_word": "tite", "accuracy": 70, "error_patterns": ["Velar Fronting"],
             "phoneme_matches": [m("K", "T"), m("AY1"), m("T")]}
    r = AlphabetFocusAgent().analyze(state)["letter_result"]
    assert r["status"] == "missed" and r["correct"] is False and r["heard_as"] == "T"


def test_focus_handles_silence_unknown_letters_and_dictionary_gaps():
    a = AlphabetFocusAgent()
    assert a.analyze({"letter": "B", "spoken_word": "No speech detected"})["letter_result"]["status"] == "no_speech"
    assert a.analyze({"letter": "Q", "spoken_word": "x"})["letter_result"] is None
    gap = a.analyze({"letter": "B", "spoken_word": "ball", "phoneme_matches": [m("L")]})["letter_result"]
    assert gap["status"] == "unscored" and gap["correct"] is None


# -- planner ---------------------------------------------------------------

def plan_for(results):
    return VaakMirrorPlannerAgent().analyze({"letter_results": results})["plan"]


def test_planner_focuses_on_missed_sounds_and_shortens_rounds_when_hard():
    p = plan_for([res("B", True), res("T", False, "D"), res("K", False, "T"), res("S", False, "TH")])
    v = p["vaakmirror_params"]
    assert p["ready"] and set(v["focus_sounds"][:3]) == {"t", "k", "s"}
    assert v["round_size"] == 6 and v["start_complexity"] == "single"
    assert v["primary_game"] == "tongue_tamer"          # 3 tongue misses, no lip misses


def test_planner_lip_misses_pick_lip_sync_hero():
    p = plan_for([res("B", False, "P"), res("M", False, "B"), res("T", True), res("S", True)])
    assert p["vaakmirror_params"]["primary_game"] == "lip_sync_hero"


def test_planner_all_clear_stretches_and_moves_to_blends():
    p = plan_for([res(l, True) for l in "BTKS"])
    v = p["vaakmirror_params"]
    assert v["focus_sounds"] == [] and v["round_size"] == 12 and v["start_complexity"] == "blend"


def test_planner_too_few_letters_is_not_ready_and_stays_conservative():
    p = plan_for([res("B", True)])
    assert p["ready"] is False and p["vaakmirror_params"]["start_complexity"] == "single"


def test_planner_suggests_untried_neighbours_first_and_never_repeats():
    p = plan_for([res("K", False, "T"), res("B", True)])
    assert p["suggested_next"][0] == "G"                # k's look-alike
    assert not ({"K", "B"} & set(p["suggested_next"]))


def test_planner_round_size_stays_in_vaakmirror_bounds():
    for results in ([], [res("B", True)], [res(l, False) for l in "BTKS"], [res(l, True) for l in "BTKS"]):
        assert 4 <= plan_for(results)["vaakmirror_params"]["round_size"] <= 20


def test_planner_ignores_junk_input():
    assert VaakMirrorPlannerAgent().analyze({"letter_results": [None, "x", {}]})["plan"]["letters_checked"] == 0


# -- graph wiring (stub speech nodes: no Whisper/Vosk needed) ---------------

def test_letter_graph_runs_all_three_stages_in_order():
    order = []

    def speech(state):
        order.append("speech")
        return {"spoken_word": "ball", "accuracy": 90,
                "phoneme_matches": [m("B"), m("AO1"), m("L")]}

    def artic(state):
        order.append("articulation")
        return {"error_patterns": [], "severity_score": "Normal", "targeted_quests": []}

    out = build_letter_graph(speech, artic).invoke({"letter": "B", "target_word": "ball"})
    assert order == ["speech", "articulation"]
    assert out["letter_result"]["correct"] is True and out["letter_result"]["sound_id"] == "b"


def test_plan_graph_returns_a_plan():
    out = build_plan_graph().invoke({"letter_results": [res("B", False, "P"), res("T", True)]})
    assert out["plan"]["vaakmirror_params"]["focus_sounds"] == ["b"]


# -- frontend/backend catalog drift ------------------------------------------

FRONTEND_DATA = Path(__file__).resolve().parents[2] / "frontend/src/assessment/alphabetData.js"


@pytest.mark.skipif(not FRONTEND_DATA.exists(), reason="frontend not checked out")
def test_frontend_letter_probes_match_backend_catalog():
    """alphabetData.js's LETTER_PROBES drives the UI; the backend catalog scores
    it. If they drift, the child is asked for one word and scored on another."""
    from app.services.alphabet_sounds import MIN_LETTERS_FOR_PLAN
    src = FRONTEND_DATA.read_text()
    block = src[src.index("export const LETTER_PROBES"):src.index("export const CORE_LETTERS")]
    front = {m.group(1): (m.group(2), m.group(3))
             for m in re.finditer(r'(\w): \{ word: "(\w+)",\s+emoji: "[^"]+", group: "([\w-]+)" \}', block)}
    assert set(front) == set(LETTERS), set(front) ^ set(LETTERS)
    for letter, (word, group) in front.items():
        assert LETTERS[letter]["word"] == word, letter
        assert LETTERS[letter]["group"] == group, letter
    core = re.search(r'CORE_LETTERS = \[([^\]]+)\]', src).group(1)
    assert re.findall(r'"(\w)"', core) == CORE_LETTERS
    assert int(re.search(r'MIN_LETTERS_FOR_PLAN = (\d+)', src).group(1)) == MIN_LETTERS_FOR_PLAN
