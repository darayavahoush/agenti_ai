import sys
sys.path.insert(0, '.')

print("Testing old router imports...")

try:
    print("\n1. Importing patient router...")
    from app.routes.patient import router as patient_router
    print(f"   ✅ Patient router loaded: {patient_router.prefix}")
    print(f"   Routes: {len(patient_router.routes)}")
    for route in patient_router.routes:
        print(f"     - {route.path}")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n2. Importing assessment router...")
    from app.routes.assessment import router as assessment_router
    print(f"   ✅ Assessment router loaded: {assessment_router.prefix}")
    print(f"   Routes: {len(assessment_router.routes)}")
    for route in assessment_router.routes:
        print(f"     - {route.path}")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n3. Importing speech router...")
    from app.routes.speech import router as speech_router
    print(f"   ✅ Speech router loaded: {speech_router.prefix}")
    print(f"   Routes: {len(speech_router.routes)}")
    for route in speech_router.routes:
        print(f"     - {route.path}")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n4. Importing audio router...")
    from app.routers.audio import router as audio_router
    print(f"   ✅ Audio router loaded: {audio_router.prefix}")
    print(f"   Routes: {len(audio_router.routes)}")
    for route in audio_router.routes:
        print(f"     - {route.path}")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n5. Testing database connection with old models...")
    from app.database import SessionLocal
    from app.models.patient import Patient
    db = SessionLocal()
    patients = db.query(Patient).all()
    print(f"   ✅ Database connection works. Found {len(patients)} patients")
    db.close()
except Exception as e:
    print(f"   ❌ Failed: {e}")
    import traceback
    traceback.print_exc()
