# Database Setup (Before running the project)

## Install PostgreSQL

### Windows
1. Download PostgreSQL installer from https://www.postgresql.org/download/windows/
2. Run the installer and follow the setup wizard
3. Remember the password you set for the 'postgres' user during installation
4. Default port: 5432 (or 5433 if you changed it)

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Mac
```bash
brew install postgresql
brew services start postgresql
```

## Create Database

### Option 1: Using pgAdmin (GUI - Windows)
1. Open pgAdmin (installed with PostgreSQL)
2. Connect to your PostgreSQL server
3. Right-click on "Databases" → Create → Database
4. Name: `vaaksudhi`
5. Click Save

### Option 2: Using Command Line
```bash
# Windows
psql -U postgres -c "CREATE DATABASE vaaksudhi;"

# Linux/Mac
sudo -u postgres psql -c "CREATE DATABASE vaaksudhi;"
```

## Update Environment File

After creating the database, edit `backend/.env` and update the DATABASE_URL:

```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5433/vaaksudhi
```

Replace:
- `YOUR_PASSWORD` with your PostgreSQL password
- `5433` with your PostgreSQL port (default is 5432, but installer may use 5433)

## Verify Database Connection

Test the connection before running the backend:

```bash
cd backend
python -c "from app.database import engine; print('Database connected successfully!' if engine else 'Connection failed')"
```

---

# Project Setup Steps

# 1. Clone the project
git clone https://github.com/lavanya2kowmar/agenti_ai.git

# 2. Navigate to project
cd agenti_ai/vaaksudhi

# 3. Install uv
pip install uv

# 4. Create and activate virtual environment
uv venv
.venv\Scripts\Activate.ps1

# 5. Navigate to backend
cd backend

# 6. Install Python dependencies
uv pip install -r requirements.txt

# 7. Setup environment file (Windows uses 'copy', not 'cp')
copy .env.example .env
# Edit .env with your database credentials

# 8. Download NLTK data (stay in same terminal)
python -c "import nltk; nltk.download('averaged_perceptron_tagger_eng'); nltk.download('averaged_perceptron_tagger'); nltk.download('cmudict'); nltk.download('punkt')"

# 9. Download Vosk models (optional)
python setup_vosk_models.py all
# OR for specific languages:
# python setup_vosk_models.py hi  # Hindi
# python setup_vosk_models.py te  # Telugu
# python setup_vosk_models.py kn  # Kannada

# 10. Add images to database
python add_images_to_db.py

# 11. Fill missing translations
python fill_missing_translations.py

# 12. Run backend (keep this terminal open)
uvicorn app.main:app --reload

# 13. Open NEW terminal for frontend
cd agenti_ai/vaaksudhi\frontend
npm install
npm run dev