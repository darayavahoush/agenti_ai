import json
import logging
import os

from app.services.game_predictor import rank_games, SOUND_LABEL

logger = logging.getLogger(__name__)


class GamePredictorAgent:
    """
    Runs once after the Assessment's words have been analysed (not per word,
    unlike the graph's other agents) and predicts which games would help the
    child most.

    The ranking itself is always rule-based (services/game_predictor.py), so
    it is stable and explainable. When OPENAI_API_KEY is set the LLM is only
    asked to write a warmer headline and per-game reasons *for the games the
    rules already picked*: it can't add, drop or reorder games, and any
    answer that doesn't validate against the ranked list is discarded in
    favour of the rule-based text. Same optional-OpenAI-with-fallback shape
    as DiagnosticReporterAgent.
    """

    def predict(self, word_results: list[dict], patient_name: str | None = None) -> dict:
        result = rank_games(word_results)
        name = (patient_name or "").strip() or "you"
        result["source"] = "rules"
        result["headline"] = self._rule_headline(result, name)

        if not result["plan"] or not os.getenv("OPENAI_API_KEY"):
            return result

        try:
            import openai

            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=8.0)
            evidence = {
                "child_first_name": patient_name or "the child",
                "words_analyzed": result["words_analyzed"],
                "average_accuracy_percent": result["avg_accuracy"],
                "tricky_sounds": [SOUND_LABEL.get(k, k) for k in result["weak_sounds"]],
                "games": [
                    {"id": g["id"], "name": g["name"], "rule_reason": g["reason"]}
                    for g in result["plan"]
                ],
            }
            prompt = (
                "You are a pediatric speech-language pathologist's assistant. A child just did a "
                "short pronunciation assessment. The games below were already chosen and ordered by "
                "a rules engine. Do NOT add, remove or reorder games. For each game, rewrite "
                "rule_reason as ONE warm, encouraging sentence (max 30 words) a 6-10 year old and "
                "their parent would understand, keeping every sound and word it mentions accurate. "
                "Also write a one-sentence headline (max 25 words) that never uses the words "
                "disorder, delay, deficit or severe.\n\n"
                f"{json.dumps(evidence)}\n\n"
                'Reply with JSON only: {"headline": "...", "reasons": {"<game id>": "..."}}'
            )
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You write short, kind explanations. JSON only."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content)
            reasons = data.get("reasons") or {}
            ids = {g["id"] for g in result["plan"]}
            if not isinstance(reasons, dict) or not set(reasons) <= ids:
                raise ValueError("LLM reasons referenced games outside the ranked plan")
            for g in result["plan"]:
                text = reasons.get(g["id"])
                if isinstance(text, str) and 0 < len(text) <= 240:
                    g["reason"] = text.strip()
            headline = data.get("headline")
            if isinstance(headline, str) and 0 < len(headline) <= 200:
                result["headline"] = headline.strip()
            result["source"] = "llm"
        except Exception as exc:  # any failure -> keep the rule-based text
            logger.info("Game predictor LLM phrasing skipped (%s); using rule-based text", exc)
        return result

    @staticmethod
    def _rule_headline(result: dict, name: str) -> str:
        if not result["plan"]:
            return "Great job! No sound stood out as tricky, so any game is a good choice."
        sounds = [SOUND_LABEL.get(k, k.lower()) for k in result["weak_sounds"][:3]]
        if not sounds:
            return "Here are the games most likely to help next."
        joined = ", ".join(f'"{s}"' for s in sounds[:-1]) + (" and " if len(sounds) > 1 else "") + f'"{sounds[-1]}"'
        return f"Your tricky sounds this time were {joined}. These games are the best place to start."
