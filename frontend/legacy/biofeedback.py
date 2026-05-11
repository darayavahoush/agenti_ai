import streamlit as st
import requests
import tempfile
from streamlit_mic_recorder import mic_recorder

API = "http://127.0.0.1:8000"

# ---------------------------------
# PAGE CONFIG
# ---------------------------------
st.set_page_config(
    page_title="VaakSiddhi Real AI Speech Therapy",
    page_icon="🎤",
    layout="wide"
)

# ---------------------------------
# HEADER
# ---------------------------------
st.title("🎤 VaakSiddhi Real AI Speech Therapy")
st.markdown("Child speaks live. AI detects spoken word and gives therapy feedback.")

st.divider()

# ---------------------------------
# INPUTS
# ---------------------------------
name = st.text_input("👶 Child Name")
target_word = st.text_input("🎯 Target Word", value="Ball")

st.subheader(f"Say this word: {target_word}")

# ---------------------------------
# MIC RECORDER
# ---------------------------------
audio = mic_recorder(
    start_prompt="🎤 Start Recording",
    stop_prompt="⏹ Stop Recording",
    just_once=True,
    key="recorder"
)

# ---------------------------------
# PROCESS AUDIO
# ---------------------------------
if audio:

    st.success("Recording captured ✅")

    # Save temp wav
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        f.write(audio["bytes"])
        temp_path = f.name

    # Send directly to AI speech endpoint
    with open(temp_path, "rb") as file:

        files = {
            "file": ("recording.wav", file, "audio/wav")
        }

        data = {
            "target_word": target_word
        }

        res = requests.post(
            f"{API}/speech-therapy",
            files=files,
            data=data
        )

    result = res.json()

    # ---------------------------------
    # ERROR
    # ---------------------------------
    if "error" in result:
        st.error(result["error"])

    else:

        st.success("🧠 AI Analysis Completed")

        # ---------------------------------
        # MAIN RESULT
        # ---------------------------------
        c1, c2, c3 = st.columns(3)

        c1.metric("🎯 Target Word", result["target_word"])
        c2.metric("🗣 Spoken Word", result["spoken_word"])
        c3.metric("📈 Accuracy %", result["accuracy"])

        st.divider()

        # ---------------------------------
        # FEEDBACK
        # ---------------------------------
        st.subheader("🧠 Therapy Feedback")
        st.info(result["feedback"])

        # ---------------------------------
        # STARS
        # ---------------------------------
        stars = 1

        if result["accuracy"] >= 90:
            stars = 5
        elif result["accuracy"] >= 75:
            stars = 4
        elif result["accuracy"] >= 60:
            stars = 3
        elif result["accuracy"] >= 40:
            stars = 2
        else:
            stars = 1

        st.subheader("⭐ Reward Stars")
        st.write("⭐" * stars)

        # ---------------------------------
        # MOTIVATION
        # ---------------------------------
        if result["accuracy"] >= 90:
            st.balloons()
            st.success("Excellent pronunciation!")
        elif result["accuracy"] >= 70:
            st.success("Great job! Almost perfect.")
        else:
            st.warning("Good try! Let's repeat once more.")

else:
    st.info("🎤 Press Start Recording and say the target word.")