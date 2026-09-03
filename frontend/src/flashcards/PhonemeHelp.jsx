import { useState, useEffect } from "react";
import { getPhonemeCard } from "./lib/api";
import { friendlyPhoneme } from "./utils/phonemeMap";
import { getSurface } from "./utils/themes";

// "How to fix these sounds" -- one mouth-shape diagram + tip per phoneme
// the kid got wrong on this attempt. Bonus feedback only: doesn't touch
// scoring or the pass/fail flow in Flashcards.jsx, purely additive below
// the existing phoneme pill row.
export default function PhonemeHelp({ matches, th, darkMode = false }) {
  const [cards, setCards] = useState({});
  const wrongPhonemes = [...new Set(matches.filter(m => !m.correct).map(m => m.expected))];

  useEffect(() => {
    wrongPhonemes.forEach(async (ph) => {
      if (cards[ph] !== undefined) return;
      try {
        const card = await getPhonemeCard(ph);
        setCards(prev => ({ ...prev, [ph]: card }));
      } catch {
        setCards(prev => ({ ...prev, [ph]: null }));
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [matches]);

  if (wrongPhonemes.length === 0) return null;

  return (
    <div style={{ background: getSurface(darkMode, 0.8), border: `1.5px solid ${th.accent}33`, borderRadius: "16px", padding: "16px", display: "flex", flexDirection: "column", gap: "14px" }}>
      <p style={{ color: th.sub, fontSize: "0.65rem", letterSpacing: "0.12em", margin: 0, fontWeight: 700, textTransform: "uppercase" }}>How to fix these sounds</p>
      {wrongPhonemes.map((ph, i) => {
        const card = cards[ph];
        return (
          <div key={ph} style={{ display: "flex", flexDirection: "column", gap: "10px", paddingBottom: "14px", borderBottom: i < wrongPhonemes.length - 1 ? `1px solid ${th.accent}22` : "none" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "1.3rem", color: th.accent, fontWeight: 700 }}>{friendlyPhoneme(ph)}</span>
              <span style={{ color: th.sub, fontFamily: "JetBrains Mono, monospace", fontSize: "0.7rem", opacity: 0.7 }}>/{ph}/</span>
              {card && <span style={{ color: th.text, fontSize: "0.85rem", fontFamily: "Nunito, sans-serif", fontWeight: 700 }}>{card.name}</span>}
            </div>
            {card === undefined && <p style={{ color: th.sub, fontSize: "0.8rem", margin: 0 }}>Loading...</p>}
            {card === null && <p style={{ color: th.sub, fontSize: "0.8rem", margin: 0 }}>No tip available for this sound yet.</p>}
            {card?.mouth_svg && (
              <div style={{ width: "190px", height: "120px", alignSelf: "center" }} dangerouslySetInnerHTML={{ __html: card.mouth_svg }} />
            )}
            {card?.tip && (
              <p style={{ color: th.text, fontSize: "0.85rem", margin: 0, lineHeight: 1.6, paddingLeft: "12px", borderLeft: `3px solid ${th.accent}` }}>
                {card.tip}
              </p>
            )}
            {card?.example_word && (
              <p style={{ color: th.sub, fontSize: "0.75rem", margin: 0 }}>
                Example: <span style={{ color: th.text, fontFamily: "Nunito, sans-serif", fontWeight: 700 }}>{card.example_word}</span>
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}
