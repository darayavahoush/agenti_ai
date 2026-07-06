from app.state.assessment_state import AssessmentState


class ArticulationDiagnosticAgent:
    """
    Diagnostic agent that evaluates phonetic matches to classify children's speech sound disorders
    and phonological processes (such as Fronting or Final Consonant Deletion).
    """

    def analyze(self, state: AssessmentState) -> AssessmentState:
        matches = state.get("phoneme_matches") or []
        expected = state.get("expected_phonemes") or []
        accuracy = state.get("accuracy") or 0

        detected_patterns = []
        targeted_quests = []

        # Helper to map phoneme to A-Z letter
        def phoneme_to_letter(p: str) -> str:
            p = p.upper().replace("0", "").replace("1", "").replace("2", "")
            mapping = {
                "AA": "A", "AE": "A", "AH": "A", "AO": "O", "AW": "A", "AY": "A",
                "EH": "E", "ER": "R", "EY": "A", "IH": "I", "IY": "E", "OW": "O", "OY": "O",
                "UH": "U", "UW": "U", "B": "B", "CH": "C", "SH": "S", "JH": "J", "ZH": "S",
                "D": "D", "DH": "D", "F": "F", "G": "G", "HH": "H", "K": "K", "L": "L",
                "M": "M", "N": "N", "NG": "N", "P": "P", "R": "R", "S": "S", "Z": "Z",
                "T": "T", "TH": "T", "V": "V", "W": "W", "Y": "Y"
            }
            return mapping.get(p, "")

        # 1. Detect Final Consonant Deletion
        if len(matches) > 0 and len(expected) > 0:
            last_expected = expected[-1]
            # If the last expected phoneme is a consonant (doesn't contain vowel letters) and matches shows it was incorrect
            is_vowel = any(v in last_expected for v in ["A", "E", "I", "O", "U"])
            if not is_vowel:
                # Find if the last match was correct
                last_match = matches[-1]
                if not last_match.get("correct"):
                    detected_patterns.append("Final Consonant Deletion (dropping ending sounds)")
                    letter = phoneme_to_letter(last_expected)
                    if letter and letter not in targeted_quests:
                        targeted_quests.append(letter)

        # 2. Detect Velar Fronting (replacing K/G with T/D)
        for m in matches:
            exp_p = m.get("expected", "").upper()
            spk_p = m.get("spoken", "").upper()
            
            if exp_p in ["K", "G"] and spk_p in ["T", "D"]:
                detected_patterns.append(f"Velar Fronting (pronouncing back sound /{exp_p}/ as front sound /{spk_p}/)")
                letter = phoneme_to_letter(exp_p)
                if letter and letter not in targeted_quests:
                    targeted_quests.append(letter)

            # Gather other failed letters
            if not m.get("correct"):
                letter = phoneme_to_letter(exp_p)
                if letter and letter not in targeted_quests:
                    targeted_quests.append(letter)

        # 3. Classify Severity
        if accuracy >= 85:
            severity = "Normal / Mild variant"
        elif accuracy >= 65:
            severity = "Mild to Moderate Articulation Delay"
        elif accuracy >= 45:
            severity = "Moderate Phonological Disorder"
        else:
            severity = "Severe Speech Sound Disorder"

        return {
            "error_patterns": list(set(detected_patterns)),
            "severity_score": severity,
            "targeted_quests": targeted_quests
        }
