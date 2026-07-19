# Vosk Speech Recognition Setup

## Overview
Vosk is a lightweight offline speech recognition toolkit that provides native script output for Indian languages. This is perfect for your use case where you want Hindi speech converted to Hindi text (देवनागरी लिपि), Telugu speech to Telugu text (తెలుగు లిపి), etc.

## Benefits over Whisper
- **Lightweight**: Much smaller models (~50MB vs ~150MB for Whisper)
- **Native Script Output**: Hindi speech → Hindi text (not English transliteration)
- **Offline**: Works without internet connection
- **Fast**: Lower latency than Whisper
- **Language-Specific**: Dedicated models for each Indian language

## Installation

### 1. Install Dependencies
```bash
cd backend
pip install vosk pyaudio
```

### 2. Download Language Models
Run the setup script to download specific language models:

```bash
# For Hindi
python setup_vosk_models.py hi

# For Telugu  
python setup_vosk_models.py te

# For Kannada
python setup_vosk_models.py kn

# For all Indian languages
python setup_vosk_models.py all
```

### 3. Manual Download (Alternative)
If the script doesn't work, download models manually from:
- https://alphacephei.com/vosk/models

Extract to: `backend/vosk_models/`

Required models:
- `vosk-model-hi-0.22` (Hindi)
- `vosk-model-te-0.22` (Telugu)
- `vosk-model-kn-0.22` (Kannada)

## How It Works

The system now automatically:
1. **Detects Indian language** (hi, te, kn, ta, ml, bn, mr)
2. **Uses Vosk model** for that language (if available)
3. **Falls back to Whisper** if Vosk model is missing
4. **Returns native script text** (Hindi speech → "कुत्ता" not "kutta")

## Example Output

### Hindi
- **Input**: Spoken Hindi word for "dog"
- **Output**: "कुत्ता" (native Devanagari script)
- **Phonemes**: क, त, ता

### Telugu
- **Input**: Spoken Telugu word for "dog"  
- **Output**: "కుక్క" (native Telugu script)
- **Phonemes**: కు, క్, క

### Kannada
- **Input**: Spoken Kannada word for "dog"
- **Output**: "ನಾಯಿ" (native Kannada script)
- **Phonemes**: ನಾ, ಯಿ

## Testing

After setup, test the assessment tab:
1. Select Hindi language
2. Record audio saying a Hindi word
3. Check backend logs for "Using Vosk for hi transcription"
4. Verify the transcript shows Hindi script

## Troubleshooting

### Model not found error
```
⚠️ Vosk model not available for hi, falling back to Whisper
```
**Solution**: Run `python setup_vosk_models.py hi`

### Vosk import error
```
⚠️ Vosk not installed, falling back to Whisper  
```
**Solution**: Run `pip install vosk`

### Poor transcription quality
- Ensure clear audio recording
- Speak clearly and at normal pace
- Vosk works best with clean audio (minimal background noise)

## Model Sizes
- Hindi: ~50MB
- Telugu: ~50MB  
- Kannada: ~50MB
- English: ~1.3GB (optional)

## Performance
- **Latency**: ~1-2 seconds for short audio
- **CPU Usage**: Low (lightweight models)
- **Memory**: ~100MB per loaded model
- **Accuracy**: Good for clear speech, improves with training data
