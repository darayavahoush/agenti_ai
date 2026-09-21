from typing import Optional, TypedDict

from app.state.assessment_state import AssessmentState


class AlphabetState(AssessmentState, total=False):
    """AssessmentState plus what the Alphabet check adds on top.

    Subclassing (rather than a new TypedDict) keeps every field the reused
    speech-analysis and articulation nodes read and write, and total=False
    lets the graph start from just the audio + target without listing every
    inherited field up front.
    """

    letter: str
    letter_result: Optional[dict]


class AlphabetPlanState(TypedDict, total=False):
    """State for the plan graph, which runs once after the letters are done."""

    letter_results: list[dict]
    plan: dict
