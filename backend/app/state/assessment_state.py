from typing import TypedDict, Optional


class AssessmentState(TypedDict):
    """
    State definition for the Assessment Diagnostic Graph.
    Tracks core speech details, identified error patterns, severity classification,
    vocal acoustic stability, and targeted keyboard practice quests.
    """

    # -------------------------
    # Request Info
    # -------------------------
    patient_name: str
    age: Optional[int]
    target_word: str
    language: Optional[str]

    # -------------------------
    # Audio & Speech
    # -------------------------
    audio_path: Optional[str]
    sample_rate: Optional[int]
    audio: Optional[object]
    child_audio: Optional[object]
    transcript: Optional[str]
    spoken_word: Optional[str]

    # -------------------------
    # Phonemes & Features
    # -------------------------
    expected_phonemes: list[str]
    spoken_phonemes: list[str]
    phoneme_accuracy: Optional[int]
    phoneme_matches: list[dict]
    expected_phonemes_display: list[str]
    spoken_phonemes_display: list[str]

    duration: Optional[float]
    pitch: Optional[float]
    loudness: Optional[float]

    # -------------------------
    # Diagnostics & Reports
    # -------------------------
    accuracy: Optional[int]
    feedback: Optional[str]
    stars: Optional[int]
    reasoning: Optional[str]
    vocal_reasoning: Optional[str]
    recommendations: list[str]

    error_patterns: list[str]
    severity_score: Optional[str]
    diagnostic_report: Optional[str]
    targeted_quests: list[str]

    # -------------------------
    # Errors
    # -------------------------
    error: Optional[str]
