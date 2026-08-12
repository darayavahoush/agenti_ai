from langgraph.graph import StateGraph, END

from app.state.assessment_state import AssessmentState
from app.agents.speech_analysis_agent import SpeechAnalysisAgent
from app.agents.articulation_diagnostic_agent import ArticulationDiagnosticAgent
from app.agents.vocal_acoustic_agent import VocalAcousticAgent
from app.agents.diagnostic_reporter_agent import DiagnosticReporterAgent

# Instantiate assessment agents
speech_analysis_agent = SpeechAnalysisAgent()
articulation_agent = ArticulationDiagnosticAgent()
vocal_agent = VocalAcousticAgent()
reporter_agent = DiagnosticReporterAgent()


# Node wrappers
def speech_analysis_node(state: AssessmentState) -> AssessmentState:
    # SpeechAnalysisAgent expects SpeechState, but its fields are identical
    # so we can reuse it directly!
    return speech_analysis_agent.analyze(state)


def articulation_diagnostic_node(state: AssessmentState) -> AssessmentState:
    return articulation_agent.analyze(state)


def vocal_acoustic_node(state: AssessmentState) -> AssessmentState:
    return vocal_agent.analyze(state)


def diagnostic_reporter_node(state: AssessmentState) -> AssessmentState:
    return reporter_agent.analyze(state)


# Build the Graph
builder = StateGraph(AssessmentState)

# Add diagnostic nodes
builder.add_node("speech_analysis", speech_analysis_node)
builder.add_node("articulation_diagnostic", articulation_diagnostic_node)
builder.add_node("vocal_acoustic", vocal_acoustic_node)
builder.add_node("diagnostic_reporter", diagnostic_reporter_node)

# Set entry point
builder.set_entry_point("speech_analysis")

# Fork parallel diagnostic nodes after core speech analysis
builder.add_edge("speech_analysis", "articulation_diagnostic")
builder.add_edge("speech_analysis", "vocal_acoustic")

# Merge results back into the diagnostic reporter
builder.add_edge("articulation_diagnostic", "diagnostic_reporter")
builder.add_edge("vocal_acoustic", "diagnostic_reporter")

# End workflow after compiling diagnostic reports
builder.add_edge("diagnostic_reporter", END)

# Compile assessment graph
assessment_graph = builder.compile()
