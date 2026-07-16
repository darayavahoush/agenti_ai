# Setup Guide

## Project Overview
This project is a speech therapy application designed to help children practice pronunciation and speech skills. The backend handles audio analysis and phoneme evaluation, while the frontend provides a playful, kid-friendly interface for therapy activities.

## 1. Clone the project
```bash
git clone <repo-url>
cd vaaksudhi
```

## 2. Create and activate a virtual environment
### PowerShell
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Command Prompt
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

## 3. Install Python dependencies
```bash
pip install -r requirement.txt
```

## 4. Install Vosk for Indian language speech recognition
**Required for native script output** (Hindi speech → Hindi text, Telugu speech → Telugu text, etc.):

```bash
cd backend
pip install vosk pyaudio
```

Then download language models (required for proper functionality):
```bash
# For Hindi
python setup_vosk_models.py hi

# For Telugu
python setup_vosk_models.py te

# For Kannada
python setup_vosk_models.py kn

# For all Indian languages (recommended)
python setup_vosk_models.py all
```

**Note:** Models are ~50MB each. This is required for native script output. The system will fall back to Whisper (English transliteration) if Vosk models are not installed, but this will not provide the intended native script experience.

## 5. Download required NLTK data
Run these inside the activated environment:
```python
import nltk
nltk.download('averaged_perceptron_tagger_eng')
nltk.download('averaged_perceptron_tagger')
nltk.download('cmudict')
nltk.download('punkt')
```

## 6. Configure environment variables
Create a `.env` file in the backend folder and add the required credentials/config values.

## 7. Run the backend
```bash
cd backend
uvicorn app.main:app --reload
```

## 8. Run the frontend
```bash
cd frontend
npm install
npm run dev
```

## Notes
- The backend uses FastAPI.
- The frontend uses React + Vite.
- If you are on Windows and PowerShell blocks script execution, run:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```     
