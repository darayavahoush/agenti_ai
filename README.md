# Vaaksudhi - Speech Therapy Application

A speech therapy application designed to help children practice pronunciation and speech skills. The backend handles audio analysis and phoneme evaluation, while the frontend provides a playful, kid-friendly interface for therapy activities.

## Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher
- PostgreSQL database (default: localhost:5433)
- Git

## Quick Setup Guide

### 1. Clone the repository
```bash
git clone <repo-url>
cd vaaksudhi
```

### 2. Backend Setup

#### 2.1 Create and activate Python virtual environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

#### 2.2 Install Python dependencies
```bash
cd backend
pip install -r requirements.txt
```

#### 2.3 Configure environment variables
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env file with your database credentials
# Default: DATABASE_URL=postgresql://postgres:password@localhost:5433/vaaksudhi
```

#### 2.4 Download required NLTK data
```python
python -c "import nltk; nltk.download('averaged_perceptron_tagger_eng'); nltk.download('averaged_perceptron_tagger'); nltk.download('cmudict'); nltk.download('punkt')"
```

#### 2.5 (Optional) Install Vosk for Indian language speech recognition
This enables native script output (Hindi speech → Hindi text, Telugu speech → Telugu text, etc.):

```bash
# Download language models
python setup_vosk_models.py all  # Downloads all Indian language models (~50MB each)
# OR for specific languages:
python setup_vosk_models.py hi  # Hindi
python setup_vosk_models.py te  # Telugu
python setup_vosk_models.py kn  # Kannada
```

**Note:** Without Vosk models, the system will fall back to Whisper (English transliteration), which won't provide native script output.

#### 2.6 Run the backend
```bash
uvicorn app.main:app --reload
```

The backend will start on `http://localhost:8000`

### 3. Frontend Setup

#### 3.1 Install Node.js dependencies
```bash
cd frontend
npm install
```

#### 3.2 Run the frontend
```bash
npm run dev
```

The frontend will start on `http://localhost:5173`

### 4. Database Setup

#### 4.1 Create PostgreSQL database
```sql
CREATE DATABASE vaaksudhi;
```

#### 4.2 Run database migrations (if applicable)
The database tables will be created automatically on first run.

#### 4.3 Add images to database
```bash
cd backend
python add_images_to_db.py              # Add all images from data/images
python add_images_to_db.py --list        # List all images
python add_images_to_db.py --db          # List words in database
```

#### 4.4 Fill missing translations
```bash
python fill_missing_translations.py     # Fill missing translations
python fill_missing_translations.py --show  # Show words missing translations
```

## Troubleshooting

### PowerShell script execution error
If you see an error about script execution on Windows:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### PyAudio installation on Windows
If PyAudio fails to install, try:
```bash
pip install pipwin
pipwin install pyaudio
```

### Database connection issues
- Ensure PostgreSQL is running
- Check the DATABASE_URL in backend/.env
- Verify the database exists: `psql -U postgres -l`

### Port already in use
If port 8000 or 5173 is already in use, you can change them:
```bash
# Backend
uvicorn app.main:app --port 8001

# Frontend (edit vite.config.js)
```

## Project Structure

```
vaaksudhi/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI application entry point
│   │   ├── config.py         # Configuration settings
│   │   ├── database.py       # Database connection
│   │   ├── models/           # SQLAlchemy models
│   │   ├── crud/             # Database operations
│   │   ├── services/         # Business logic
│   │   ├── agents/           # LangGraph agents
│   │   └── tools/            # Various tools (speech, phoneme, etc.)
│   ├── requirements.txt      # Python dependencies
│   ├── .env.example          # Environment variables template
│   └── setup_vosk_models.py  # Vosk model downloader
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # React main component
│   │   └── ...
│   ├── package.json          # Node.js dependencies
│   └── vite.config.js        # Vite configuration
└── data/
    └── images/               # Image assets for therapy words
```

## Technologies Used

### Backend
- **FastAPI** - Web framework
- **SQLAlchemy** - ORM
- **PostgreSQL** - Database
- **PyTorch** - Machine learning
- **Whisper** - Speech recognition
- **Vosk** - Offline speech recognition
- **Librosa** - Audio analysis
- **LangGraph** - Agent orchestration

### Frontend
- **React** - UI framework
- **Vite** - Build tool
- **TailwindCSS** - Styling
- **Lucide React** - Icons
- **Recharts** - Charts

## License

[Your License Here]     
