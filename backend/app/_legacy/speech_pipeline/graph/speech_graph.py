from langgraph.graph import StateGraph, END

from app.state.speech_state import SpeechState
from app.agents.speech_analysis_agent import SpeechAnalysisAgent
from app._legacy.speech_pipeline.agents.supervisor_agent import SupervisorAgent
from app._legacy.speech_pipeline.agents.therapy_recommendation_agent import TherapyRecommendationAgent
from app._legacy.speech_pipeline.agents.progress_evaluation_agent import ProgressEvaluationAgent
from app._legacy.speech_pipeline.agents.intensive_practice_agent import IntensivePracticeAgent
from app._legacy.speech_pipeline.agents.session_planning_agent import SessionPlanningAgent

# Instantiate agents
analysis_agent = SpeechAnalysisAgent()
supervisor_agent = SupervisorAgent()
recommendation_agent = TherapyRecommendationAgent()
evaluation_agent = ProgressEvaluationAgent()
intensive_agent = IntensivePracticeAgent()
planning_agent = SessionPlanningAgent()


# Node functions
def speech_analysis_node(state: SpeechState) -> SpeechState:
    return analysis_agent.analyze(state)


def progress_evaluation_node(state: SpeechState) -> SpeechState:
    return evaluation_agent.analyze(state)


def supervisor_node(state: SpeechState) -> SpeechState:
    return supervisor_agent.analyze(state)


def therapy_recommendation_node(state: SpeechState) -> SpeechState:
    return recommendation_agent.analyze(state)


def intensive_practice_node(state: SpeechState) -> SpeechState:
    return intensive_agent.analyze(state)


def session_planning_node(state: SpeechState) -> SpeechState:
    return planning_agent.analyze(state)


# Edge routing function based on Supervisor Agent's decisions
def route_next(state: SpeechState) -> str:
    return state.get("next_agent") or "session_planning"


# Build the Graph
builder = StateGraph(SpeechState)

# Add all agent nodes (including Supervisor Agent)
builder.add_node("speech_analysis", speech_analysis_node)
builder.add_node("progress_evaluation", progress_evaluation_node)
builder.add_node("supervisor", supervisor_node)
builder.add_node("therapy_recommendation", therapy_recommendation_node)
builder.add_node("intensive_practice", intensive_practice_node)
builder.add_node("session_planning", session_planning_node)

# Set entry point
builder.set_entry_point("speech_analysis")

# Define edges
# Speech Analysis flows to Progress Evaluation to load streaks
builder.add_edge("speech_analysis", "progress_evaluation")

# Progress Evaluation flows to the Supervisor Agent node to make the decision
builder.add_edge("progress_evaluation", "supervisor")

# Supervisor Agent decision node dynamically branches using conditional edge
builder.add_conditional_edges(
    "supervisor",
    route_next,
    {
        "intensive_practice": "intensive_practice",
        "therapy_recommendation": "therapy_recommendation",
        "session_planning": "session_planning"
    }
)

# Practice/Recommendation agents run, and flow to Session Planner before ending
builder.add_edge("intensive_practice", "session_planning")
builder.add_edge("therapy_recommendation", "session_planning")
builder.add_edge("session_planning", END)

# Compile speech graph
speech_graph = builder.compile()