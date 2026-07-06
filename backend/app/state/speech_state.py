from typing import TypedDict, Optional


class SpeechState(TypedDict):
    """
    Shared state passed between all LangGraph nodes.
    """

    # -------------------------
    # Request Information
    # -------------------------
    patient_name: str
    target_word: str
    therapy_mode: str

    # -------------------------
    # Audio
    # -------------------------
    audio_path: Optional[str]
    sample_rate: Optional[int]
    audio: Optional[object]
    child_audio: Optional[object]

    # -------------------------
    # Speech
    # -------------------------
    transcript: Optional[str]
    spoken_word: Optional[str]

    # -------------------------
    # Phonemes
    # -------------------------
    expected_phonemes: list[str]
    spoken_phonemes: list[str]

    phoneme_accuracy: Optional[int]
    phoneme_matches: list[dict]

    # -------------------------
    # Audio Features
    # -------------------------
    duration: Optional[float]
    pitch: Optional[float]
    loudness: Optional[float]

    # -------------------------
    # Results
    # -------------------------
    accuracy: Optional[int]
    feedback: Optional[str]
    stars: Optional[int]

    # -------------------------
    # Display Values
    # -------------------------
    expected_phonemes_display: list[str]
    spoken_phonemes_display: list[str]

    # -------------------------
    # LLM Reasoning (Future)
    # -------------------------
    reasoning: Optional[str]
    recommendations: list[str]

    # -------------------------
    # Multi-Agent Orchestration
    # -------------------------
    next_agent: Optional[str]
    therapist_observations: Optional[str]
    suggested_exercises: list[str]
    repeat_word: Optional[bool]
    progress_report: Optional[str]
    difficulty_adjustment: Optional[str]
    next_word: Optional[str]
    next_exercise: Optional[str]
    session_difficulty: Optional[str]
    intensive_practice_triggered: Optional[bool]
    intensive_practice_message: Optional[str]

    # -------------------------
    # Errors
    # -------------------------
    error: Optional[str]