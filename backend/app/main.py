import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine

# Auto-setup Vosk models directory
from app.tools.vosk_tool import setup_vosk_models_directory
setup_vosk_models_directory()

# Routes
from app.routes.patient import router as patient_router
from app.routes.speech import router as speech_router
from app.routes.assessment import router as assessment_router
from app.routers.audio import router as audio_router

# BreathQuest routes
from app.routers.breathquest.auth import router as breathquest_auth_router
from app.routers.breathquest.patients import router as breathquest_patients_router
from app.routers.breathquest.sessions import router as breathquest_sessions_router
from app.routers.breathquest.dashboard import router as breathquest_dashboard_router

# -----------------------------------
# APP
# -----------------------------------
app = FastAPI(
    title="VaakSuddhi AI Backend",
    version="1.0.0"
)

# -----------------------------------
# CORS
# -----------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------
# CREATE TABLES & RUN MIGRATIONS
# -----------------------------------
Base.metadata.create_all(bind=engine)

# Dynamically ensure database schema columns and seed translation entries
from app.utils.db_setup import ensure_db_schema_and_translations
ensure_db_schema_and_translations()


def sync_local_images_to_db():
    from app.database import SessionLocal
    from app.models.assessment_word import AssessmentWord
    from pathlib import Path
    
    db = SessionLocal()
    try:
        # Get all words already in database (lowercase to prevent duplicates)
        existing_words = {w.word.lower().strip() for w in db.query(AssessmentWord).all()}
        
        # Path to local downloaded images folder
        DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "images"
        
        if DATA_DIR.exists():
            imported_count = 0
            for path in DATA_DIR.iterdir():
                if path.is_file() and path.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]:
                    filename_stem = path.stem.strip()
                    word_key = filename_stem.lower().strip()
                    
                    # Skip config index files, system indicators, or CV2 text fallbacks
                    if word_key in ["index", "string", "placeholder"] or word_key.endswith("_text"):
                        continue
                    
                    if word_key not in existing_words:
                        new_word = AssessmentWord(
                            word=filename_stem, # Retain original name casing (e.g. "Zebra")
                            display_order=0,
                            is_active=True
                        )
                        db.add(new_word)
                        existing_words.add(word_key)
                        imported_count += 1
                        
            if imported_count > 0:
                db.commit()
                print(f"ðŸŽ‰ Automatically imported {imported_count} pre-downloaded words into the database!")
    except Exception as e:
        print(f"âš ï¸ Error during local image auto-sync: {e}")
    finally:
        db.close()

sync_local_images_to_db()

# -----------------------------------
# MOUNT STATIC ASSETS
# -----------------------------------
# Ensure the assets/audio directories are created
os.makedirs(os.path.join("assets", "audio"), exist_ok=True)
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# -----------------------------------
# INCLUDE ROUTES
# -----------------------------------
# Original patient routes
app.include_router(patient_router)
app.include_router(speech_router)
app.include_router(assessment_router)
app.include_router(audio_router)

# BreathQuest routes with prefix
app.include_router(breathquest_auth_router, prefix="/api/v1/breathquest")
app.include_router(breathquest_patients_router, prefix="/api/v1/breathquest")
app.include_router(breathquest_sessions_router, prefix="/api/v1/breathquest")
app.include_router(breathquest_dashboard_router, prefix="/api/v1/breathquest")

# -----------------------------------
# ROOT
# -----------------------------------
@app.get("/")
def home():
    return {
        "message": "VaakSuddhi V1 Running ðŸš€"
    }
