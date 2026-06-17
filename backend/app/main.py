from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine

# Routes
from app.routes.patient import router as patient_router
from app.routes.speech import router as speech_router

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
# Base.metadata.create_all(bind=engine)
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

# -----------------------------------
# INCLUDE ROUTES
# -----------------------------------
app.include_router(patient_router)
app.include_router(speech_router)

# -----------------------------------
# ROOT
# -----------------------------------
@app.get("/")
def home():
    return {
        "message": "VaakSuddhi V1 Running 🚀"
    }