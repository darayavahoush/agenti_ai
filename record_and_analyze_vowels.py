import sounddevice as sd
import numpy as np
import parselmouth

SAMPLE_RATE = 16000
DURATION = 2.5
REPS = 3

def record(label, rep):
    input(f"\nPress Enter, then say a loud, sustained '{label}' (take {rep}/{REPS}) for {DURATION}s...")
    print("Recording...")
    audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float64')
    sd.wait()
    print("Done.")
    return audio.flatten()

def analyze(audio):
    duration_s = len(audio) / SAMPLE_RATE
    sound = parselmouth.Sound(audio, sampling_frequency=SAMPLE_RATE)
    formant = sound.to_formant_burg()

    start, end = duration_s * 0.2, duration_s * 0.8
    times = np.linspace(start, end, num=10)
    f1_vals, f2_vals = [], []
    for t in times:
        f1 = formant.get_value_at_time(1, t)
        f2 = formant.get_value_at_time(2, t)
        if f1 and f2 and not np.isnan(f1) and not np.isnan(f2):
            f1_vals.append(f1)
            f2_vals.append(f2)

    if not f1_vals:
        return None
    return (float(np.mean(f1_vals)), float(np.mean(f2_vals)))

results = {}
for vowel in ["AAA (as in father)", "OOO (as in boot)", "EEE (as in beet)"]:
    reps = []
    for r in range(1, REPS + 1):
        audio = record(vowel, r)
        res = analyze(audio)
        if res:
            print(f"  take {r}: F1={res[0]:.0f}Hz  F2={res[1]:.0f}Hz")
            reps.append(res)
        else:
            print(f"  take {r}: no valid formants detected")
    results[vowel] = reps

print("\n=== Summary (per-take + average) ===")
averaged = {}
for vowel, reps in results.items():
    if not reps:
        print(f"{vowel}: FAILED TO DETECT ANY TAKES")
        continue
    f1_mean = float(np.mean([r[0] for r in reps]))
    f2_mean = float(np.mean([r[1] for r in reps]))
    f1_std = float(np.std([r[0] for r in reps]))
    f2_std = float(np.std([r[1] for r in reps]))
    averaged[vowel] = (f1_mean, f2_mean)
    print(f"{vowel}: F1={f1_mean:.0f}Hz (±{f1_std:.0f}), F2={f2_mean:.0f}Hz (±{f2_std:.0f}), n={len(reps)}")

TARGET_F1, TARGET_F2, TOLERANCE = 900.0, 1450.0, 400.0
print(f"\nCurrent app target: F1={TARGET_F1}, F2={TARGET_F2}, tolerance={TOLERANCE}")
print("\nDistance from 'aa' target for each vowel (using averages):")
for vowel, (f1, f2) in averaged.items():
    f1_dist = abs(f1 - TARGET_F1)
    f2_dist = abs(f2 - TARGET_F2)
    quality = max(0.0, 1.0 - (f1_dist + f2_dist) / (2 * TOLERANCE))
    print(f"  {vowel}: f1_dist={f1_dist:.0f}, f2_dist={f2_dist:.0f}, quality_score={quality:.2f}")
