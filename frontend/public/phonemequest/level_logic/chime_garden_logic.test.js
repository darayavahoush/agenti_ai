const assert = require('assert');
const { computePeriodicity, computeVoicingScore, updateChimeRotation, personalizeVoicingRange } = require('./chime_garden_logic.js');

const SR = 44100;
const WINDOW = 2048;

// A clean sine wave at a given pitch — stands in for a voiced "ya" glide,
// which is tonal/harmonic.
function makeVoicedWaveform(freqHz, amplitude = 0.3) {
  const data = new Float32Array(WINDOW);
  for (let i = 0; i < WINDOW; i++) {
    data[i] = amplitude * Math.sin((2 * Math.PI * freqHz * i) / SR);
  }
  return data;
}

// Pseudo-random noise — stands in for unvoiced/breathy sound (e.g. the old
// "ffff" target), which has no strong single periodicity.
function makeNoiseWaveform(amplitude = 0.3) {
  const data = new Float32Array(WINDOW);
  let seed = 42;
  for (let i = 0; i < WINDOW; i++) {
    seed = (seed * 1103515245 + 12345) & 0x7fffffff;
    data[i] = amplitude * ((seed / 0x7fffffff) * 2 - 1);
  }
  return data;
}

function makeSilence() {
  return new Float32Array(WINDOW);
}

// --- computePeriodicity ---
const voicedPeriodicity = computePeriodicity(makeVoicedWaveform(220), SR);
assert.ok(voicedPeriodicity > 0.7, `a clean tone should show strong periodicity, got ${voicedPeriodicity}`);

const noisePeriodicity = computePeriodicity(makeNoiseWaveform(), SR);
assert.ok(noisePeriodicity < voicedPeriodicity, 'noise should show weaker periodicity than a clean tone');

const silentPeriodicity = computePeriodicity(makeSilence(), SR);
assert.strictEqual(silentPeriodicity, 0, 'silence should have zero periodicity');

// --- computeVoicingScore ---
const quiet = computeVoicingScore(0.005, 0.8);
assert.strictEqual(quiet.isValidAttempt, false, 'below noise floor should be an invalid attempt regardless of periodicity');

const noisyNotVoiced = computeVoicingScore(0.1, 0.05);
assert.ok(noisyNotVoiced.score < 0.2, 'loud but low-periodicity sound (not voiced-shaped) should score low');
assert.strictEqual(noisyNotVoiced.isValidAttempt, true, 'but still counts as a valid attempt for engagement purposes');

const goodVoicing = computeVoicingScore(0.1, 0.8);
assert.ok(goodVoicing.score > 0.7, `high periodicity should score well, got ${goodVoicing.score}`);
assert.ok(goodVoicing.score > noisyNotVoiced.score, 'voiced-shaped sound should score higher than non-voiced sound at same volume');

// --- updateChimeRotation ---
const config = { maxSpeed: 4, spinUpRate: 8, decayRate: 3 };
let state = { angle: 0, speed: 0 };
let totalChimes = 0;
for (let i = 0; i < 100; i++) {
  state = updateChimeRotation(state.angle, state.speed, 0.9, 0.05, config);
  totalChimes += state.chimesRung;
}
assert.ok(totalChimes > 0, `sustained high voicing should eventually ring at least one chime, got ${totalChimes}`);
assert.ok(state.speed > 0, 'speed should be positive while sustaining good voicing');

// speed should decay toward zero once voicing stops
let decayState = { angle: 0, speed: 3 };
for (let i = 0; i < 50; i++) decayState = updateChimeRotation(decayState.angle, decayState.speed, 0, 0.05, config);
assert.ok(decayState.speed < 0.5, `speed should decay toward 0 once voicing stops, got ${decayState.speed}`);

console.log('All chime_garden_logic tests passed.');

// --- computeVoicingScore actually respects a passed-in calibrated noise floor ---
// (regression test carried over from the frication version: an earlier
// version ignored the calibrated value and used a hardcoded constant instead)
const highCalibratedFloor = computeVoicingScore(0.03, 0.8, 0.05); // rms below this child's calibrated floor
assert.strictEqual(highCalibratedFloor.isValidAttempt, false, 'a rms below the passed-in calibrated noise floor should be invalid, even if it would pass the old default');

const passesCalibratedFloor = computeVoicingScore(0.03, 0.8, 0.01); // same rms, lower calibrated floor
assert.strictEqual(passesCalibratedFloor.isValidAttempt, true, 'the same rms should be valid once the calibrated floor is lower than it');

// --- personalizeVoicingRange ---
const readings = [0.6, 0.65, 0, 0.55, 0.62, 0.58];
const personalized = personalizeVoicingRange(readings);
assert.strictEqual(personalized.usedFallback, false);
assert.ok(personalized.minPeriodicity < 0.58 && personalized.maxPeriodicity > 0.58, 'personalized range should bracket the child\'s actual observed periodicity');

const tooFew = personalizeVoicingRange([0.6, 0, 0]);
assert.strictEqual(tooFew.usedFallback, true, 'too few valid readings should fall back to defaults');

console.log('All chime_garden_logic calibration tests passed.');
