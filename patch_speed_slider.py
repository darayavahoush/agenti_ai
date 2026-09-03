import pathlib

path = pathlib.Path("frontend/src/pages/kid/Flashcards.jsx")
src = path.read_text()

old_state = '''  const [phase, setPhase] = useState("listen");
  const [playingChar, setPlayingChar] = useState(false);
  const [playingChild, setPlayingChild] = useState(false);'''

new_state = '''  const [phase, setPhase] = useState("listen");
  const [playingChar, setPlayingChar] = useState(false);
  const [playingChild, setPlayingChild] = useState(false);
  const [speed, setSpeed] = useState(1.0);  // slidable playback speed, 0.5-1.5x (matches backend atempo range)'''

assert old_state in src, "phase/playing state block not found verbatim -- aborting"
assert src.count(old_state) == 1
src = src.replace(old_state, new_state)

old_buttons = '''                  <div style={{ display: "flex", gap: "10px" }}>
                    <button onClick={() => playWord(1.0)} disabled={playingChar} style={{ flex: 1, background: getSurface(false, 0.7), border: `1.5px solid ${th.accent}44`, borderRadius: "14px", padding: "14px", cursor: "pointer", color: th.accent, fontWeight: 700, fontSize: "0.85rem", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px", fontFamily: "Nunito, sans-serif" }}>
                      🔊 Normal
                    </button>
                    <button onClick={() => playWord(0.65)} disabled={playingChar} style={{ flex: 1, background: getSurface(false, 0.7), border: `1.5px solid ${th.accent}44`, borderRadius: "14px", padding: "14px", cursor: "pointer", color: th.accent, fontWeight: 700, fontSize: "0.85rem", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px", fontFamily: "Nunito, sans-serif" }}>
                      🐢 Slow
                    </button>
                  </div>
                  {playingChar && <p style={{ color: th.sub, fontSize: "0.75rem", textAlign: "center", margin: "-8px 0 0 0" }}>Playing...</p>}'''

new_buttons = '''                  <div style={{ background: getSurface(false, 0.7), border: `1.5px solid ${th.accent}44`, borderRadius: "14px", padding: "14px 16px", display: "flex", flexDirection: "column", gap: "8px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ color: th.sub, fontSize: "0.7rem", letterSpacing: "0.08em", fontWeight: 700, textTransform: "uppercase", fontFamily: "Nunito, sans-serif" }}>🐢 Slow &nbsp;·&nbsp; Fast 🐇</span>
                      <span style={{ color: th.accent, fontSize: "0.8rem", fontFamily: "Nunito, sans-serif", fontWeight: 900 }}>{speed.toFixed(2)}x</span>
                    </div>
                    <input
                      type="range" min="0.5" max="1.5" step="0.05" value={speed}
                      onChange={(e) => setSpeed(parseFloat(e.target.value))}
                      onMouseUp={() => playWord(speed)}
                      onTouchEnd={() => playWord(speed)}
                      style={{ width: "100%", accentColor: th.accent, cursor: "pointer" }}
                    />
                    <button onClick={() => playWord(speed)} disabled={playingChar} style={{ background: th.accent, border: "none", borderRadius: "10px", padding: "10px", cursor: "pointer", color: "#fff", fontWeight: 700, fontSize: "0.85rem", fontFamily: "Nunito, sans-serif" }}>
                      {playingChar ? "Playing..." : `🔊 Play at ${speed.toFixed(2)}x`}
                    </button>
                  </div>'''

assert old_buttons in src, "Normal/Slow button block not found verbatim -- aborting"
assert src.count(old_buttons) == 1, f"expected exactly 1 match, found {src.count(old_buttons)}"
src = src.replace(old_buttons, new_buttons)

path.write_text(src)
print("Patched successfully.")
