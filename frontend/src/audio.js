/* Audio: PCM capture → normalise → WAV encoding */

export function normalizeAudio(samples) {
  let sumSq = 0, peak = 0;
  for (let i = 0; i < samples.length; i++) {
    const abs = Math.abs(samples[i]);
    sumSq += samples[i] * samples[i];
    if (abs > peak) peak = abs;
  }
  const rms = Math.sqrt(sumSq / samples.length);
  if (rms < 0.0001) return samples;
  const gainRms = 0.18 / rms;
  const gainPeak = peak > 0 ? 0.95 / peak : 1;
  const gain = Math.min(gainRms, gainPeak, 8);
  const out = new Float32Array(samples.length);
  for (let i = 0; i < samples.length; i++) out[i] = Math.max(-1, Math.min(1, samples[i] * gain));
  return out;
}

export function encodeWav(samples, sr = 16000) {
  const buf = new ArrayBuffer(44 + samples.length * 2);
  const v = new DataView(buf);
  const w = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  w(0,"RIFF"); v.setUint32(4,36+samples.length*2,true); w(8,"WAVE"); w(12,"fmt ");
  v.setUint32(16,16,true); v.setUint16(20,1,true); v.setUint16(22,1,true);
  v.setUint32(24,sr,true); v.setUint32(28,sr*2,true); v.setUint16(32,2,true); v.setUint16(34,16,true);
  w(36,"data"); v.setUint32(40,samples.length*2,true);
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1,Math.min(1,samples[i]));
    v.setInt16(44+i*2, s < 0 ? s*0x8000 : s*0x7FFF, true);
  }
  return new Blob([buf],{type:"audio/wav"});
}

let pendingPhonemeAudioTimer = null;

export function playPhonemeAudio(exampleWord) {
  if (!window.speechSynthesis) return;
  if (pendingPhonemeAudioTimer) clearTimeout(pendingPhonemeAudioTimer);
  window.speechSynthesis.cancel();
  // Same cancel-then-speak race as lib/speech.js -- Chrome/Firefox will
  // silently drop a speak() called in the same tick right after cancel().
  // Short delay lets the queue actually clear first.
  pendingPhonemeAudioTimer = setTimeout(() => {
    pendingPhonemeAudioTimer = null;
    const utt = new SpeechSynthesisUtterance(exampleWord);
    utt.rate = 0.7; utt.pitch = 1.0; utt.lang = "en-IN";

    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v => {
      const name = v.name.toLowerCase();
      return name.includes("nova") || v.lang.toLowerCase().startsWith("en-in") || name.includes("veena") || name.includes("heera");
    });
    if (preferred) utt.voice = preferred;

    window.speechSynthesis.speak(utt);
  }, 80);
}
