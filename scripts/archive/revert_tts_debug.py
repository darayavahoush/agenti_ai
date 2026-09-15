import pathlib

path = pathlib.Path("backend/app/routers/flashcards/router.py")
src = path.read_text()

old = '''    try:
        audio_bytes = tts_speak(text, character, speed=speed)
    except Exception as e:
        logger.error(f"speak_endpoint: TTS failed for text={text!r} character={character!r}: {e}")
        # TEMP DEBUG: exposing real exception text in the response body so it
        # shows up in DevTools -> Network -> Response without depending on
        # Azure log streaming. Revert detail= back to the generic message
        # once the root cause is confirmed -- don't ship raw exception text
        # to the frontend long-term.
        raise HTTPException(status_code=502, detail=f"TTS failed: {type(e).__name__}: {e}")'''

new = '''    try:
        audio_bytes = tts_speak(text, character, speed=speed)
    except Exception as e:
        logger.error(f"speak_endpoint: TTS failed for text={text!r} character={character!r}: {e}")
        raise HTTPException(status_code=502, detail="Text-to-speech is temporarily unavailable")'''

assert old in src, "debug block not found verbatim -- file may have drifted, aborting"
assert src.count(old) == 1, f"expected exactly 1 match, found {src.count(old)}"

path.write_text(src.replace(old, new))
print("Reverted successfully.")
