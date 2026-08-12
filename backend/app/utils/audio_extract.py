# ===============================================
# AUDIO EXTRACTION - FINAL WORKING VERSION
# Uses imageio_ffmpeg directly (NO pydub)
# Pitch + Loudness + Pressure
# ===============================================

# Install first:
# pip install librosa pandas numpy imageio-ffmpeg

import os
import subprocess
import librosa
import numpy as np
import pandas as pd
import imageio_ffmpeg

# ===============================================
# FOLDER PATH
# ===============================================
folder_path = r"C:\Users\lavan\speak_easy\speak_easy\audio_files"

# ===============================================
# FILE TYPES
# ===============================================
extensions = (".wav", ".mp3", ".mpeg", ".m4a", ".mp4")

# ===============================================
# GET REAL FFMPEG EXE
# ===============================================
ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

# ===============================================
# RESULTS
# ===============================================
results = []

# ===============================================
# LOOP FILES
# ===============================================
for file in os.listdir(folder_path):

    if file.lower().endswith(extensions):

        file_path = os.path.join(folder_path, file)

        try:
            # ----------------------------------
            # Convert to wav using ffmpeg.exe
            # ----------------------------------
            temp_wav = "temp_audio.wav"

            cmd = [
                ffmpeg_path,
                "-y",
                "-i", file_path,
                temp_wav
            ]

            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # ----------------------------------
            # Load WAV
            # ----------------------------------
            y, sr = librosa.load(temp_wav, sr=None)

            duration = round(len(y) / sr, 2)

            # ----------------------------------
            # 1. Pitch
            # ----------------------------------
            f0, _, _ = librosa.pyin(
                y,
                fmin=80,
                fmax=500
            )

            pitch_vals = f0[~np.isnan(f0)]

            avg_pitch = round(np.mean(pitch_vals), 2) if len(pitch_vals) > 0 else 0
            min_pitch = round(np.min(pitch_vals), 2) if len(pitch_vals) > 0 else 0
            max_pitch = round(np.max(pitch_vals), 2) if len(pitch_vals) > 0 else 0

            # ----------------------------------
            # 2. Loudness
            # ----------------------------------
            rms = librosa.feature.rms(y=y)[0]

            avg_loudness = round(np.mean(rms), 4)
            max_loudness = round(np.max(rms), 4)

            # ----------------------------------
            # 3. Pressure Proxy
            # ----------------------------------
            db = librosa.amplitude_to_db(np.abs(y), ref=np.max)

            avg_pressure = round(np.mean(db), 2)
            max_pressure = round(np.max(db), 2)

            # ----------------------------------
            # Save
            # ----------------------------------
            results.append({
                "File Name": file,
                "Duration(sec)": duration,
                "Avg Pitch": avg_pitch,
                "Min Pitch": min_pitch,
                "Max Pitch": max_pitch,
                "Avg Loudness": avg_loudness,
                "Avg Pressure(dB)": avg_pressure
            })

        except Exception as e:

            results.append({
                "File Name": file,
                "Duration(sec)": "Error",
                "Avg Pitch": "Error",
                "Min Pitch": "Error",
                "Max Pitch": "Error",
                "Avg Loudness": "Error",
                "Avg Pressure(dB)": str(e)
            })

# ===============================================
# DISPLAY
# ===============================================
df = pd.DataFrame(results)

print("\n========= AUDIO ANALYSIS RESULTS =========\n")
print(df.to_string(index=False))

# ===============================================
# SAVE EXCEL
# ===============================================
df.to_excel("audio_analysis_results.xlsx", index=False)

print("\nSaved: audio_analysis_results.xlsx")