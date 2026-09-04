// fa level — sustained voicing / "ya" glide-into-vowel control.
// "ya" is tonal (a glide into a voiced vowel), the opposite acoustic signature
// from the old "ffff" target (turbulent, noise-shaped frication). Detecting it
// needs periodicity, not spectral centroid: autocorrelation on the raw
// time-domain samples finds the strongest self-similarity lag within the
// expected human-voice pitch range, normalized by signal energy so it stays
// comparable across loudness. A high peak means the waveform is repeating
// itself at a steady pitch (voiced); noise or silence has no strong lag.

function computePeriodicity(timeDomainData, sampleRate, minFreqHz = 120, maxFreqHz = 500) {
  const n = timeDomainData.length;
  let energy = 0;
  for (let i = 0; i < n; i++) energy += timeDomainData[i] * timeDomainData[i];
  if (energy < 1e-6) return 0; // silence — no periodicity to find

  const minLag = Math.max(1, Math.floor(sampleRate / maxFreqHz));
  const maxLag = Math.min(n - 1, Math.floor(sampleRate / minFreqHz));
  let bestCorr = 0;
  for (let lag = minLag; lag <= maxLag; lag++) {
    let corr = 0;
    for (let i = 0; i < n - lag; i++) corr += timeDomainData[i] * timeDomainData[i + lag];
    const normCorr = corr / energy;
    if (normCorr > bestCorr) bestCorr = normCorr;
  }
  return Math.max(0, Math.min(1, bestCorr));
}

const NOISE_FLOOR_RMS_DEFAULT = 0.01;
const MIN_PERIODICITY_DEFAULT = 0.15;   // below this looks unvoiced/noisy, not "ya"-shaped
const MAX_EXPECTED_PERIODICITY_DEFAULT = 0.85;

function computeVoicingScore(rms, periodicity, noiseFloor = NOISE_FLOOR_RMS_DEFAULT,
                              minPeriodicity = MIN_PERIODICITY_DEFAULT, maxPeriodicity = MAX_EXPECTED_PERIODICITY_DEFAULT) {
  if (rms < noiseFloor) return { score: 0, isValidAttempt: false };
  if (periodicity < minPeriodicity) return { score: 0.05, isValidAttempt: true }; // present but not voiced-shaped
  const score = Math.max(0, Math.min(1, (periodicity - minPeriodicity) / (maxPeriodicity - minPeriodicity)));
  return { score, isValidAttempt: true };
}

// Averages periodicity readings taken during the calibration "say ya" phase
// into a personalized range, rather than assuming every child+mic setup
// produces the same generic 0.15-0.85 periodicity. Falls back to generic
// defaults if too few valid readings came through.
function personalizeVoicingRange(periodicityReadings, fallbackMin = MIN_PERIODICITY_DEFAULT, fallbackMax = MAX_EXPECTED_PERIODICITY_DEFAULT) {
  const valid = periodicityReadings.filter(p => p > 0);
  if (valid.length < 3) return { minPeriodicity: fallbackMin, maxPeriodicity: fallbackMax, usedFallback: true };
  const mean = valid.reduce((s, p) => s + p, 0) / valid.length;
  // center a range around what this child actually produced, floored/capped
  // to sane absolute bounds so a fluke reading can't make the level impossible
  const minPeriodicity = Math.max(0.05, mean * 0.5);
  const maxPeriodicity = Math.min(0.98, mean * 1.25);
  return { minPeriodicity, maxPeriodicity, usedFallback: false };
}

// Chime rotation state — sustained voicing spins the chime garden faster;
// each full rotation (2*PI) rings a note. Rotation decays gently, not abruptly.
function updateChimeRotation(currentAngle, currentSpeed, voicingScore, dt, config) {
  const { maxSpeed, spinUpRate, decayRate } = config;
  const targetSpeed = voicingScore * maxSpeed;
  const nextSpeed = currentSpeed < targetSpeed
    ? Math.min(targetSpeed, currentSpeed + spinUpRate * dt)
    : Math.max(targetSpeed, currentSpeed - decayRate * dt);
  const nextAngle = currentAngle + nextSpeed * dt;
  const fullRotations = Math.floor(nextAngle / (2 * Math.PI)) - Math.floor(currentAngle / (2 * Math.PI));
  return { angle: nextAngle, speed: nextSpeed, chimesRung: fullRotations };
}

if (typeof module !== 'undefined') {
  module.exports = { computePeriodicity, computeVoicingScore, updateChimeRotation, personalizeVoicingRange };
}
