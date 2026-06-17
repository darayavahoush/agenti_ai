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

## 4. Download required NLTK data
Run these inside the activated environment:
```python
import nltk
nltk.download('averaged_perceptron_tagger_eng')
nltk.download('averaged_perceptron_tagger')
nltk.download('cmudict')
nltk.download('punkt')
```

## 5. Configure environment variables
Create a `.env` file in the backend folder and add the required credentials/config values.

## 6. Run the backend
```bash
cd backend
uvicorn app.main:app --reload
```

## 7. Run the frontend
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
