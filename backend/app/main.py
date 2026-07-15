from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine, ensure_database_schema

# Routes
from app.routes.patient import router as patient_router
from app.routes.speech import router as speech_router
from app.routes.assessment import router as assessment_router
from app.routers.audio import router as audio_router
import app.models
# from app.routes.image import router as image_router

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
# CREATE TABLES
# -----------------------------------
Base.metadata.create_all(bind=engine)
ensure_database_schema()

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)


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
                print(f"🎉 Automatically imported {imported_count} pre-downloaded words into the database!")
    except Exception as e:
        print(f"⚠️ Error during local image auto-sync: {e}")
    finally:
        db.close()

sync_local_images_to_db()

# -----------------------------------
# INCLUDE ROUTES
# -----------------------------------
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

app.include_router(patient_router)
app.include_router(speech_router)
app.include_router(assessment_router)
app.include_router(audio_router, prefix="/api")
# app.include_router(image_router)

# -----------------------------------
# ROOT
# -----------------------------------
@app.get("/")
def home():
    return {
        "message": "VaakSuddhi V1 Running 🚀"
    }

