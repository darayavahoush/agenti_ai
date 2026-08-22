import sys
sys.path.insert(0, '.')

print("Testing route imports...")

try:
    print("\n1. Importing patient router...")
    from app.routes.patient import router as patient_router
    print(f"   ✅ Patient router loaded: {patient_router.prefix}")
    print(f"   Routes: {len(patient_router.routes)}")
except Exception as e:
    print(f"   ❌ Failed: {e}")

try:
    print("\n2. Importing assessment router...")
    from app.routes.assessment import router as assessment_router
    print(f"   ✅ Assessment router loaded: {assessment_router.prefix}")
    print(f"   Routes: {len(assessment_router.routes)}")
except Exception as e:
    print(f"   ❌ Failed: {e}")

try:
    print("\n3. Importing speech router (archived, unmounted -- see backend/app/_legacy/README.md)...")
    from app._legacy.speech_pipeline.routes.speech import router as speech_router
    print(f"   ✅ Speech router loaded: {speech_router.prefix}")
    print(f"   Routes: {len(speech_router.routes)}")
except Exception as e:
    print(f"   ❌ Failed: {e}")

try:
    print("\n4. Importing audio router...")
    from app.routers.audio import router as audio_router
    print(f"   ✅ Audio router loaded: {audio_router.prefix}")
    print(f"   Routes: {len(audio_router.routes)}")
except Exception as e:
    print(f"   ❌ Failed: {e}")

try:
    print("\n5. Importing main app...")
    from app.main import app
    print(f"   ✅ App loaded")
    print(f"   Total routes: {len(app.routes)}")
    
    # Check all routes
    print("\n   All app routes:")
    for i, r in enumerate(app.routes):
        route_type = type(r).__name__
        print(f"     [{i}] {route_type}")
        
        if hasattr(r, 'path'):
            print(f"         path: {r.path}")
        elif hasattr(r, 'prefix'):
            print(f"         prefix: {r.prefix}")
            print(f"         routes: {len(r.routes)}")
            for j, sub in enumerate(r.routes):
                if hasattr(sub, 'path'):
                    print(f"           [{j}] {sub.path}")
        elif hasattr(r, 'original_router'):
            orig = r.original_router
            print(f"         original_router: {type(orig).__name__}")
            if hasattr(orig, 'prefix'):
                print(f"         prefix: {orig.prefix}")
            if hasattr(orig, 'routes'):
                print(f"         routes: {len(orig.routes)}")
                for j, sub in enumerate(orig.routes):
                    if hasattr(sub, 'path'):
                        print(f"           [{j}] {sub.path}")
        else:
            print(f"         (no path/prefix/original_router)")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    import traceback
    traceback.print_exc()
