from app.state.speech_state import SpeechState
from app.tools.audio_tool import (
    load_audio,
    normalize_audio,
    trim_audio,
    select_child_segment,
    extract_features
)
from app.tools.speech_tool import (
    transcribe,
    normalize_text,
    extract_first_sound
)
from app.tools.phoneme_tool import (
    get_basic_phonemes,
    compute_score,
    get_display_phoneme_list,
    generate_feedback
)
from app.services.phoneme.scoring import score_phonemes
from rapidfuzz import fuzz


class SpeechAnalysisAgent:
    """
    Agent responsible for core speech therapy audio analysis.
    """

    def analyze(self, state: SpeechState) -> SpeechState:
        path = state.get("audio_path")
        if not path:
            state["error"] = "No audio path provided"
            return state

        try:
            # Load audio
            y, sr = load_audio(path)
            state["sample_rate"] = sr

            # Normalize audio
            y = normalize_audio(y)

            # Trim silence
            y = trim_audio(y, top_db=10)

            # Child segment selection
            y_child = select_child_segment(y, sr)

            # Fallback safety
            if y_child is None or len(y_child) < 300:
                y_child = y

            # Transcribe
            target_word = state.get("target_word", "")
            transcript_child = transcribe(y_child, sr, prompt=target_word)
            transcript_full = transcribe(y, sr, prompt=target_word)

            target = normalize_text(target_word)

            therapy_mode = state.get("therapy_mode", "")

            def match_score(text: str) -> int:
                if therapy_mode == "First Letter Match":
                    return fuzz.ratio(
                        extract_first_sound(text),
                        extract_first_sound(target)
                    )
                return fuzz.ratio(text, target)

            score_child = match_score(transcript_child)
            score_full = match_score(transcript_full)

            analysis_notes = []
            if transcript_child == "" and transcript_full == "":
                transcript = ""
                analysis_notes.append("Audio check: No speech detected in the recording. Let's try again!")
            elif transcript_child == "":
                transcript = transcript_full
                analysis_notes.append("Audio check: Swapped to full length recording capture for maximum accuracy.")
            elif transcript_full == "":
                transcript = transcript_child
                analysis_notes.append("Audio check: Isolated child voice segment selected for transcription.")
            elif score_full > score_child + 5:
                transcript = transcript_full
                analysis_notes.append("Audio check: Full recording yielded a better phoneme match, swapping inputs.")
            else:
                transcript = transcript_child
                analysis_notes.append("Audio check: Isolated voice segment selected.")

            state["transcript"] = transcript
            state["reasoning"] = " | ".join(analysis_notes)

            # Spoken word extraction
            if therapy_mode == "First Letter Match":
                spoken = extract_first_sound(transcript)
            else:
                spoken = transcript

            spoken = normalize_text(spoken)
            state["spoken_word"] = spoken if spoken else "No speech detected"

            # Phoneme analysis
            expected_phonemes = get_basic_phonemes(target)
            spoken_phonemes = get_basic_phonemes(spoken)

            state["expected_phonemes"] = expected_phonemes
            state["spoken_phonemes"] = spoken_phonemes

            phoneme_result = score_phonemes(expected_phonemes, spoken_phonemes)
            state["phoneme_accuracy"] = phoneme_result["accuracy"]
            state["phoneme_matches"] = phoneme_result["matches"]

            # Score computation
            score = compute_score(target, spoken)
            state["accuracy"] = score

            # Feedback generation
            feedback, stars = generate_feedback(score, target, spoken)
            state["feedback"] = feedback
            state["stars"] = stars

            # Extract features
            metrics = extract_features(y_child, sr)
            state["duration"] = metrics["duration"]
            state["loudness"] = metrics["loudness"]
            state["pitch"] = metrics["pitch"]

            # Display formatting
            state["expected_phonemes_display"] = get_display_phoneme_list(
                expected_phonemes, word=target_word
            )
            state["spoken_phonemes_display"] = get_display_phoneme_list(
                spoken_phonemes, word=spoken
            )

        except Exception as e:
            state["error"] = str(e)

        return state
