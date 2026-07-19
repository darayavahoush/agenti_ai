"""
Script to add images from data/images directory to the database.

This script:
1. Scans the data/images directory for image files (PNG, JPG, JPEG, WEBP)
2. For each image found, creates an AssessmentWord entry in the database
3. Supports adding translations from CSV or manual entry
4. Skips images that already exist in the database

Usage:
    python add_images_to_db.py                 # Add all images from directory
    python add_images_to_db.py image_name      # Add specific image
    python add_images_to_db.py --list          # List all images in directory
    python add_images_to_db.py --db            # List all words in database
    python add_images_to_db.py --csv file.csv  # Add images with translations from CSV
"""

import os
import sys
import csv
from pathlib import Path
from sqlalchemy.orm import Session

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models.assessment_word import AssessmentWord


DATA_DIR = Path(__file__).parent.parent / "data" / "images"


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def load_translations_from_csv(csv_file: str) -> dict:
    """
    Load translations from CSV file.
    
    CSV format:
    word,english,telugu,hindi,tamil,kannada,malayalam,bengali,marathi
    apple,apple,ఆపిల్,सेब,ஆப்பிள్,సేబు,ആപ്പിൾ,আপেল,सेब
    
    Args:
        csv_file: Path to CSV file
    
    Returns:
        Dictionary mapping word to translations dict
    """
    translations = {}
    
    try:
        csv_path = Path(csv_file)
        if not csv_path.exists():
            print(f"❌ CSV file not found: {csv_file}")
            return translations
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                word = row.get('word', '').strip().lower()
                if not word:
                    continue
                
                translations[word] = {
                    'en': row.get('english', word),
                    'te': row.get('telugu', ''),
                    'hi': row.get('hindi', ''),
                    'ta': row.get('tamil', ''),
                    'kn': row.get('kannada', ''),
                    'ml': row.get('malayalam', ''),
                    'bn': row.get('bengali', ''),
                    'mr': row.get('marathi', '')
                }
        
        print(f"✅ Loaded {len(translations)} translations from {csv_file}")
        return translations
        
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return translations


def get_images_from_directory():
    """Get all image files from data/images directory"""
    if not DATA_DIR.exists():
        print(f"❌ Images directory not found: {DATA_DIR}")
        return []
    
    image_extensions = {'.png', '.jpg', '.jpeg', '.webp'}
    images = []
    
    for file in DATA_DIR.iterdir():
        if file.is_file() and file.suffix.lower() in image_extensions:
            images.append({
                'filename': file.name,
                'word_key': file.stem.lower().strip()
            })
    
    return sorted(images, key=lambda x: x['word_key'])


def list_images_in_directory():
    """List all images in data/images directory"""
    images = get_images_from_directory()
    
    if not images:
        print("❌ No images found in data/images directory")
        return
    
    print("\n📁 Images in data/images directory:")
    print("=" * 80)
    for i, img in enumerate(images, 1):
        print(f"{i:3}. {img['word_key']:30} -> {img['filename']}")
    
    print(f"\n✅ Total: {len(images)} images")


def list_words_in_database(db: Session):
    """List all words currently in the database"""
    words = db.query(AssessmentWord).order_by(AssessmentWord.word).all()
    
    if not words:
        print("❌ No words found in database")
        return
    
    print("\n📚 Words in database:")
    print("=" * 80)
    for i, word in enumerate(words, 1):
        status = "✓" if word.is_active else "✗"
        print(f"{i:3}. [{status}] {word.word:30} (ID: {word.id})")
    
    print(f"\n✅ Total: {len(words)} words in database")


def add_images_to_database(image_names=None, translations_dict=None):
    """
    Add images from directory to database with translations.
    
    Args:
        image_names: List of specific image names to add, or None for all
        translations_dict: Dictionary mapping words to translation dicts
    """
    if translations_dict is None:
        translations_dict = {}
    
    db = SessionLocal()
    try:
        images = get_images_from_directory()
        
        if not images:
            print("❌ No images found in data/images directory")
            return
        
        # Filter if specific images requested
        if image_names:
            requested = {name.lower().strip() for name in image_names}
            images = [img for img in images if img['word_key'] in requested]
            
            if not images:
                print(f"❌ No matching images found for: {image_names}")
                return
        
        # Get existing words
        existing_words = {
            word.word.lower().strip() 
            for word in db.query(AssessmentWord).all()
        }
        
        added = 0
        skipped = 0
        
        print("\n📥 Adding images to database:")
        print("=" * 80)
        
        for img in images:
            word = img['word_key']
            filename = img['filename']
            
            if word in existing_words:
                print(f"⏭️  SKIP  | {word:30} (already exists)")
                skipped += 1
                continue
            
            try:
                # Get translations - prefer CSV if available, otherwise try Google Translate
                if word in translations_dict:
                    translations = translations_dict[word]
                else:
                    translations = get_translations(word)
                
                # Create new assessment word
                new_word = AssessmentWord(
                    word=word,
                    word_key=word,
                    english=translations.get('en', word),
                    telugu=translations.get('te', ''),
                    hindi=translations.get('hi', ''),
                    tamil=translations.get('ta', ''),
                    kannada=translations.get('kn', ''),
                    malayalam=translations.get('ml', ''),
                    bengali=translations.get('bn', ''),
                    marathi=translations.get('mr', ''),
                    image_prompt=None,
                    display_order=0,
                    is_active=True
                )
                db.add(new_word)
                db.commit()
                db.refresh(new_word)
                
                trans_count = sum(1 for v in translations.values() if v and v != word)
                print(f"✅ ADDED  | {word:30} (ID: {new_word.id}, {trans_count} trans)")
                added += 1
                
            except Exception as e:
                db.rollback()
                print(f"❌ ERROR  | {word:30} - {str(e)}")
        
        print("\n" + "=" * 80)
        print(f"📊 Summary: {added} added, {skipped} skipped, {len(images)} total")
        
    finally:
        db.close()


def get_translations(word: str) -> dict:
    """
    Get translations for a word using Google Translate (deep-translator library).
    Free API, no authentication required.
    
    Args:
        word: English word to translate
    
    Returns:
        Dictionary with language codes as keys and translations as values
    """
    translations = {'en': word}
    
    try:
        from deep_translator import GoogleTranslator
        
        # Language codes for Indian languages
        languages = {
            'te': 'te',
            'hi': 'hi',
            'ta': 'ta',
            'kn': 'kn',
            'ml': 'ml',
            'bn': 'bn',
            'mr': 'mr'
        }
        
        lang_names = {
            'te': 'Telugu',
            'hi': 'Hindi',
            'ta': 'Tamil',
            'kn': 'Kannada',
            'ml': 'Malayalam',
            'bn': 'Bengali',
            'mr': 'Marathi'
        }
        
        for lang_code, lang in languages.items():
            try:
                translated = GoogleTranslator(source='en', target=lang).translate(word)
                translations[lang_code] = translated
                print(f"  ✓ {lang_names[lang_code]:15} ({lang_code}): {word} → {translated}")
            except Exception as e:
                print(f"  ⚠️  Translation error for {lang_names[lang_code]} ({lang_code}): {e}")
                translations[lang_code] = ''
        
        return translations
        
    except ImportError:
        print("❌ deep-translator library not installed")
        print("   Install with: pip install deep-translator")
        languages = ['te', 'hi', 'ta', 'kn', 'ml', 'bn', 'mr']
        for lang in languages:
            translations[lang] = ''
        
        return translations
    except Exception as e:
        print(f"❌ Translation failed: {e}")
        languages = ['te', 'hi', 'ta', 'kn', 'ml', 'bn', 'mr']
        for lang in languages:
            translations[lang] = ''
        
        return translations


def main():
    """Main function to handle CLI arguments"""
    if len(sys.argv) > 1:
        if sys.argv[1] == '--list':
            # List images in directory
            list_images_in_directory()
        elif sys.argv[1] == '--db':
            # List words in database
            db = SessionLocal()
            try:
                list_words_in_database(db)
            finally:
                db.close()
        elif sys.argv[1] == '--csv' and len(sys.argv) > 2:
            # Add images with translations from CSV
            csv_file = sys.argv[2]
            trans = load_translations_from_csv(csv_file)
            add_images_to_database(translations_dict=trans)
        else:
            # Add specific images
            image_names = sys.argv[1:]
            add_images_to_database(image_names)
    else:
        # Add all images
        add_images_to_database()


if __name__ == "__main__":
    main()
