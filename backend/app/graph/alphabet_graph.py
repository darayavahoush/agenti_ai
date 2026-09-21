"""
graph/alphabet_graph.py -- LangGraph agents behind the Alphabet check.

Two small graphs, both built on the same nodes the word assessment uses:

  letter graph (once per recorded letter, POST /assessment/alphabet/analyze)
      speech_analysis -> articulation_diagnostic -> alphabet_focus
      Reuses assessment_graph's speech + articulation nodes on the letter's
      keyword, then alphabet_focus keeps only the letter's own sound.

  plan graph (once, when the letters are done, POST /assessment/alphabet/complete)
      vaakmirror_planner
      Folds every letter result into VaakMirror game parameters.

Graph construction takes the nodes as arguments so the wiring can be tested
without loading Whisper/Vosk; the module-level graphs use the real nodes,
imported lazily so importing this module stays cheap.
"""

from langgraph.graph import StateGraph, END

from app.state.alphabet_state import AlphabetState, AlphabetPlanState
from app.agents.alphabet_focus_agent import AlphabetFocusAgent
from app.agents.vaakmirror_planner_agent import VaakMirrorPlannerAgent


def build_letter_graph(speech_node, articulation_node, focus_node=None):
    focus_node = focus_node or AlphabetFocusAgent().analyze
    b = StateGraph(AlphabetState)
    b.add_node("speech_analysis", speech_node)
    b.add_node("articulation_diagnostic", articulation_node)
    b.add_node("alphabet_focus", focus_node)
    b.set_entry_point("speech_analysis")
    b.add_edge("speech_analysis", "articulation_diagnostic")
    b.add_edge("articulation_diagnostic", "alphabet_focus")
    b.add_edge("alphabet_focus", END)
    return b.compile()


def build_plan_graph(planner_node=None):
    planner_node = planner_node or VaakMirrorPlannerAgent().analyze
    b = StateGraph(AlphabetPlanState)
    b.add_node("vaakmirror_planner", planner_node)
    b.set_entry_point("vaakmirror_planner")
    b.add_edge("vaakmirror_planner", END)
    return b.compile()


_letter_graph = None
_plan_graph = None


def get_letter_graph():
    """Real graph, built on first use (loads the speech models' modules)."""
    global _letter_graph
    if _letter_graph is None:
        from app.graph.assessment_graph import speech_analysis_node, articulation_diagnostic_node
        _letter_graph = build_letter_graph(speech_analysis_node, articulation_diagnostic_node)
    return _letter_graph


def get_plan_graph():
    global _plan_graph
    if _plan_graph is None:
        _plan_graph = build_plan_graph()
    return _plan_graph
