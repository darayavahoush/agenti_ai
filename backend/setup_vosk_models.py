"""
Vosk Model Setup Script

This script helps download and set up Vosk speech recognition models
for Indian languages (Hindi, Telugu, Kannada, etc.).

Vosk models are lightweight and provide native script output for Indian languages.
"""

import os
import sys
import urllib.request
import zipfile
from pathlib import Path

# Model download URLs (based on available models from alphacephei.com/vosk/models)
VOSK_MODELS = {
    "hi": {
        "name": "vosk-model-hi-0.22",
        "url": "https://alphacephei.com/vosk/models/vosk-model-hi-0.22.zip",
        "description": "Hindi (Devanagari script)"
    },
    "te": {
        "name": "vosk-model-small-te-0.42", 
        "url": "https://alphacephei.com/vosk/models/vosk-model-small-te-0.42.zip",
        "description": "Telugu (Telugu script)"
    },
    "kn": {
        "name": "vosk-model-small-ka-0.42",
        "url": "https://alphacephei.com/vosk/models/vosk-model-small-ka-0.42.zip", 
        "description": "Kannada (Note: ka=Georgian, may not work for Kannada)"
    },
    "ta": {
        "name": "vosk-model-ta-0.22",
        "url": "https://alphacephei.com/vosk/models/vosk-model-ta-0.22.zip",
        "description": "Tamil (Tamil script) - Not available on Vosk"
    },
    "ml": {
        "name": "vosk-model-ml-0.22",
        "url": "https://alphacephei.com/vosk/models/vosk-model-ml-0.22.zip",
        "description": "Malayalam (Malayalam script) - Not available on Vosk"
    },
    "bn": {
        "name": "vosk-model-bn-0.22",
        "url": "https://alphacephei.com/vosk/models/vosk-model-bn-0.22.zip",
        "description": "Bengali (Bengali script) - Not available on Vosk"
    },
    "mr": {
        "name": "vosk-model-mr-0.22",
        "url": "https://alphacephei.com/vosk/models/vosk-model-mr-0.22.zip",
        "description": "Marathi (Devanagari script) - Not available on Vosk"
    },
    "en": {
        "name": "vosk-model-en-us-0.22",
        "url": "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip",
        "description": "English (US)"
    }
}

MODELS_DIR = Path(__file__).parent / "vosk_models"


def download_file(url: str, destination: Path) -> bool:
    """Download file with progress indicator."""
    try:
        print(f"📥 Downloading from: {url}")
        
        def progress_hook(count, block_size, total_size):
            percent = int(count * block_size * 100 / total_size)
            sys.stdout.write(f"\r⏳ Progress: {percent}%")
            sys.stdout.flush()
        
        urllib.request.urlretrieve(url, destination, progress_hook)
        print(f"\n✅ Downloaded: {destination.name}")
        return True
    except Exception as e:
        print(f"\n❌ Download failed: {e}")
        return False


def extract_zip(zip_path: Path, extract_to: Path) -> bool:
    """Extract zip file."""
    try:
        print(f"📦 Extracting: {zip_path.name}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print(f"✅ Extracted successfully")
        return True
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return False


def setup_model(lang_code: str) -> bool:
    """Download and setup a specific language model."""
    if lang_code not in VOSK_MODELS:
        print(f"❌ Unknown language code: {lang_code}")
        return False
    
    model_info = VOSK_MODELS[lang_code]
    model_name = model_info["name"]
    model_url = model_info["url"]
    
    # Create models directory
    MODELS_DIR.mkdir(exist_ok=True)
    
    model_path = MODELS_DIR / model_name
    
    # Check if model already exists
    if model_path.exists():
        print(f"✅ Model already exists: {model_name}")
        return True
    
    # Download zip file
    zip_path = MODELS_DIR / f"{model_name}.zip"
    
    if not download_file(model_url, zip_path):
        return False
    
    # Extract zip file
    if not extract_zip(zip_path, MODELS_DIR):
        return False
    
    # Clean up zip file
    zip_path.unlink()
    print(f"🗑️ Removed zip file")
    
    return True


def main():
    """Main setup function."""
    print("🎤 Vosk Model Setup for Indian Languages")
    print("=" * 50)
    
    # Create models directory
    MODELS_DIR.mkdir(exist_ok=True)
    print(f"📁 Models directory: {MODELS_DIR}")
    
    print("\n📋 Available models:")
    for code, info in VOSK_MODELS.items():
        print(f"  {code}: {info['description']}")
    
    print("\n💡 Usage:")
    print("  python setup_vosk_models.py hi      # Install Hindi model")
    print("  python setup_vosk_models.py te      # Install Telugu model")
    print("  python setup_vosk_models.py kn      # Install Kannada model")
    print("  python setup_vosk_models.py all     # Install all models")
    
    if len(sys.argv) < 2:
        print("\n❌ Please specify a language code or 'all'")
        return
    
    lang = sys.argv[1].lower()
    
    if lang == "all":
        print("\n🔄 Installing all models...")
        for code in VOSK_MODELS.keys():
            print(f"\n🎯 Installing {code} model...")
            if not setup_model(code):
                print(f"❌ Failed to install {code} model")
    else:
        print(f"\n🎯 Installing {lang} model...")
        if setup_model(lang):
            print(f"✅ Successfully installed {lang} model")
        else:
            print(f"❌ Failed to install {lang} model")
    
    print("\n✨ Setup complete!")
    print(f"📁 Models installed in: {MODELS_DIR}")


if __name__ == "__main__":
    main()
