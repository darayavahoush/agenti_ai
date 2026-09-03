import pathlib

path = pathlib.Path("frontend/src/pages/kid/Flashcards.jsx")
src = path.read_text()

old_state = '''  const [showSwitcher, setShowSwitcher] = useState(false);      // character switcher (existing)
  const [showTopicSwitcher, setShowTopicSwitcher] = useState(false); // NEW: topic switcher'''

new_state = '''  const [showSwitcher, setShowSwitcher] = useState(false);      // character switcher (existing)
  const [showTopicSwitcher, setShowTopicSwitcher] = useState(false); // NEW: topic switcher
  const [exploredPhoneme, setExploredPhoneme] = useState(null);  // phoneme badge tapped for learn-before-attempt
  const [exploredCard, setExploredCard] = useState(undefined);   // undefined=loading, null=no card, object=loaded'''

assert old_state in src, "state block not found verbatim -- aborting"
assert src.count(old_state) == 1
src = src.replace(old_state, new_state)

old_import = 'import { evaluateAttempt, speakWord, getRandomWord, getThemes } from "../../flashcards/lib/api";'
new_import = 'import { evaluateAttempt, speakWord, getRandomWord, getThemes, getPhonemeCard } from "../../flashcards/lib/api";'
assert old_import in src, "api import line not found verbatim -- aborting"
assert src.count(old_import) == 1
src = src.replace(old_import, new_import)

old_badges = '''                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", justifyContent: "center" }}>
                  {(wordData?.phonemes || []).map((p, i) => (
                    <div key={i} title={phonemeExample(p)} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "2px", background: th.card, border: `1px solid ${th.accent}55`, borderRadius: "10px", padding: "6px 10px", cursor: "default" }}>
                      <span style={{ color: th.accent, fontFamily: "Nunito, sans-serif", fontSize: "0.95rem", fontWeight: 900, lineHeight: 1 }}>
                        {friendlyPhoneme(p)}
                      </span>
                      <span style={{ color: th.sub, fontFamily: "JetBrains Mono, monospace", fontSize: "0.55rem", opacity: 0.6 }}>{p}</span>
                    </div>
                  ))}
                </div>
              </div>'''

new_badges = '''                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", justifyContent: "center" }}>
                  {(wordData?.phonemes || []).map((p, i) => (
                    <div key={i} title={phonemeExample(p)}
                      onClick={async () => {
                        if (exploredPhoneme === p) { setExploredPhoneme(null); return; }
                        setExploredPhoneme(p);
                        setExploredCard(undefined);
                        try {
                          const card = await getPhonemeCard(p);
                          setExploredCard(card);
                        } catch {
                          setExploredCard(null);
                        }
                      }}
                      style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "2px", background: exploredPhoneme === p ? `${th.accent}22` : th.card, border: `1px solid ${th.accent}${exploredPhoneme === p ? "" : "55"}`, borderRadius: "10px", padding: "6px 10px", cursor: "pointer" }}>
                      <span style={{ color: th.accent, fontFamily: "Nunito, sans-serif", fontSize: "0.95rem", fontWeight: 900, lineHeight: 1 }}>
                        {friendlyPhoneme(p)}
                      </span>
                      <span style={{ color: th.sub, fontFamily: "JetBrains Mono, monospace", fontSize: "0.55rem", opacity: 0.6 }}>{p}</span>
                    </div>
                  ))}
                </div>

                {exploredPhoneme && (
                  <div style={{ width: "100%", background: getSurface(false, 0.8), border: `1.5px solid ${th.accent}33`, borderRadius: "14px", padding: "14px", display: "flex", flexDirection: "column", gap: "8px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "1.1rem", color: th.accent, fontWeight: 700 }}>{friendlyPhoneme(exploredPhoneme)}</span>
                      <span style={{ color: th.sub, fontFamily: "JetBrains Mono, monospace", fontSize: "0.65rem", opacity: 0.7 }}>/{exploredPhoneme}/</span>
                      {exploredCard && <span style={{ color: th.text, fontSize: "0.8rem", fontFamily: "Nunito, sans-serif", fontWeight: 700 }}>{exploredCard.name}</span>}
                    </div>
                    {exploredCard === undefined && <p style={{ color: th.sub, fontSize: "0.75rem", margin: 0 }}>Loading...</p>}
                    {exploredCard === null && <p style={{ color: th.sub, fontSize: "0.75rem", margin: 0 }}>No tip available for this sound yet.</p>}
                    {exploredCard?.mouth_svg && (
                      <div style={{ width: "170px", height: "110px", alignSelf: "center" }} dangerouslySetInnerHTML={{ __html: exploredCard.mouth_svg }} />
                    )}
                    {exploredCard?.tip && (
                      <p style={{ color: th.text, fontSize: "0.8rem", margin: 0, lineHeight: 1.5, paddingLeft: "10px", borderLeft: `3px solid ${th.accent}` }}>
                        {exploredCard.tip}
                      </p>
                    )}
                    {exploredCard?.example_word && (
                      <p style={{ color: th.sub, fontSize: "0.7rem", margin: 0 }}>
                        Example: <span style={{ color: th.text, fontFamily: "Nunito, sans-serif", fontWeight: 700 }}>{exploredCard.example_word}</span>
                      </p>
                    )}
                  </div>
                )}
              </div>'''

assert old_badges in src, "badge block not found verbatim -- aborting"
assert src.count(old_badges) == 1, f"expected exactly 1 match, found {src.count(old_badges)}"
src = src.replace(old_badges, new_badges)

path.write_text(src)
print("Patched successfully.")
