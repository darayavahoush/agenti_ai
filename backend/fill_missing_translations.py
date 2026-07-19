"""
Script to add translations to existing words in the database using auto-translation.

This script:
1. Finds words that are missing translations
2. Uses googletrans to auto-translate them
3. Updates the database with translations

Usage:
    python fill_missing_translations.py              # Fill all missing translations
    python fill_missing_translations.py --show       # Show words missing translations
    python fill_missing_translations.py --force      # Force re-translate all words
"""

import sys
from pathlib import Path
from sqlalchemy.orm import Session

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models.assessment_word import AssessmentWord


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def translate_word(word: str) -> dict:
    """
    Translate a word to multiple Indian languages using deep-translator.
    
    Args:
        word: English word to translate
    
    Returns:
        Dictionary with language codes as keys and translations as values
    """
    translations = {'en': word}
    
    try:
        from deep_translator import GoogleTranslator
        
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
            except Exception as e:
                print(f"    ⚠️  {lang_names[lang_code]}: error")
                translations[lang_code] = ''
        
        return translations
        
    except ImportError:
        print("❌ deep-translator not installed")
        print("   Run: pip install deep-translator")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Translation error: {e}")
        return translations


def show_missing_translations(db: Session):
    """Show words that have missing translations"""
    words = db.query(AssessmentWord).order_by(AssessmentWord.word).all()
    
    missing = []
    for word in words:
        trans_count = sum(1 for attr in ['telugu', 'hindi', 'tamil', 'kannada', 'malayalam', 'bengali', 'marathi'] 
                         if getattr(word, attr))
        if trans_count == 0:
            missing.append(word)
    
    if not missing:
        print("✅ All words have translations!")
        return
    
    print(f"\n📋 Words missing translations ({len(missing)}):")
    print("=" * 80)
    for i, word in enumerate(missing, 1):
        print(f"{i:3}. {word.word:30} (ID: {word.id})")
    
    print(f"\n⚠️  Total: {len(missing)} words need translations")


def fill_missing_translations(force=False):
    """
    Fill missing translations for words in the database.
    
    Args:
        force: If True, re-translate all words even if they have translations
    """
    db = SessionLocal()
    try:
        words = db.query(AssessmentWord).order_by(AssessmentWord.word).all()
        
        if not words:
            print("❌ No words found in database")
            return
        
        updated = 0
        skipped = 0
        
        print("\n🔄 Filling missing translations:")
        print("=" * 80)
        
        for word in words:
            # Check if word needs translation
            trans_count = sum(1 for attr in ['telugu', 'hindi', 'tamil', 'kannada', 'malayalam', 'bengali', 'marathi'] 
                             if getattr(word, attr))
            
            if trans_count > 0 and not force:
                print(f"⏭️  SKIP  | {word.word:30} (has {trans_count} translations)")
                skipped += 1
                continue
            
            try:
                print(f"🔄 TRANS | {word.word:30}", end="", flush=True)
                
                # Get translations
                translations = translate_word(word.word)
                
                # Update word with translations
                word.english = translations.get('en', word.word)
                word.telugu = translations.get('te', '')
                word.hindi = translations.get('hi', '')
                word.tamil = translations.get('ta', '')
                word.kannada = translations.get('kn', '')
                word.malayalam = translations.get('ml', '')
                word.bengali = translations.get('bn', '')
                word.marathi = translations.get('mr', '')
                
                db.add(word)
                db.commit()
                
                trans_count = sum(1 for v in translations.values() if v and v != word.word)
                print(f" ✅ ({trans_count} translations)")
                updated += 1
                
            except Exception as e:
                db.rollback()
                print(f" ❌ ERROR: {str(e)}")
        
        print("\n" + "=" * 80)
        print(f"📊 Summary: {updated} updated, {skipped} skipped")
        
    finally:
        db.close()


def main():
    """Main function"""
    if len(sys.argv) > 1:
        if sys.argv[1] == '--show':
            db = SessionLocal()
            try:
                show_missing_translations(db)
            finally:
                db.close()
        elif sys.argv[1] == '--force':
            print("⚠️  Force mode: Re-translating ALL words...")
            fill_missing_translations(force=True)
        else:
            print(f"❌ Unknown option: {sys.argv[1]}")
            print("   Usage: python fill_missing_translations.py [--show|--force]")
    else:
        fill_missing_translations()


if __name__ == "__main__":
    main()
