# frontend/app.py

import streamlit as st
import requests
import pandas as pd
import tempfile
from streamlit_mic_recorder import mic_recorder

API = "http://127.0.0.1:8000"

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="VaakSiddhi V1",
    page_icon="🎤",
    layout="wide"
)

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.title("🎤 VaakSiddhi")
page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Dashboard",
        "🎤 Live Therapy",
        "👶 Patients",
        "📈 Progress"
    ]
)

# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------
if page == "🏠 Dashboard":

    st.title("🏠 VaakSiddhi Dashboard")
    st.markdown("AI Speech Therapy Platform")

    try:
        res = requests.get(f"{API}/patients/")
        patients = res.json()
        total_patients = len(patients)
    except:
        total_patients = 0

    c1, c2, c3 = st.columns(3)

    c1.metric("👶 Total Patients", total_patients)
    c2.metric("🎤 Sessions Today", "--")
    c3.metric("📈 Avg Accuracy", "--")

    st.divider()

    st.subheader("Welcome")
    st.info("Use sidebar to navigate modules.")


# --------------------------------------------------
# LIVE THERAPY
# --------------------------------------------------
elif page == "🎤 Live Therapy":

    st.title("🎤 Live AI Therapy")

    if "child_name" not in st.session_state:
        st.session_state.child_name = ""

    name = st.text_input(
        "👶 Child Name",
        key="child_name"
    )
    if "therapy_target" not in st.session_state:
        st.session_state.therapy_target = ""

    target_word = st.text_input(
        "🎯 Target Word",
        key="therapy_target"
    )
    therapy_mode = st.selectbox(
    "🧠 Therapy Mode",
    [
        "Full Word Match",
        "First Letter Match"
    ]
    )
    st.subheader(
    f"Say this word: {st.session_state.therapy_target}"
)
    audio = mic_recorder(
        start_prompt="🎤 Start Recording",
        stop_prompt="⏹ Stop Recording",
        just_once=True,
        key="therapy"
    )

    if audio:

        st.success("Recording Captured ✅")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio["bytes"])
            temp_path = f.name

        with open(temp_path, "rb") as file:

            files = {
                "file": ("recording.wav", file, "audio/wav")
            }

            data = {
            "patient_name": st.session_state.child_name,
            "target_word": st.session_state.therapy_target,
            "therapy_mode": therapy_mode
        }

            res = requests.post(
                f"{API}/speech/therapy",
                files=files,
                data=data
            )

        result = res.json()

        if res.status_code != 200:
            st.error(f"API Error: {res.text}")
            st.stop()

        result = res.json()

        if "error" in result:
            st.error(result["error"])
            st.json(result)
            st.stop()

        else:
            st.success("AI Analysis Completed 🧠")
            st.write(f"### 🧠 Mode: {therapy_mode}")
            
            c1, c2, c3 = st.columns(3)

            c1.metric("🎯 Target", result["target_word"])
            c2.metric("🗣 Spoken", result["spoken_word"])
            c3.metric("📈 Accuracy", f'{result["accuracy"]}%')

            c4, c5, c6 = st.columns(3)

            c4.metric("🎵 Pitch", result["pitch"])
            c5.metric("🔊 Loudness", result["loudness"])
            c6.metric("⏱ Duration", result["duration"])

            st.divider()

            st.subheader("🧠 Feedback")
            st.info(result["feedback"])

            st.subheader("⭐ Reward")
            st.write("⭐" * result["stars"])

            # --------------------------------------------------
            # PHONEME ANALYSIS
            # --------------------------------------------------
            st.write("## 🧩 Phoneme Analysis")

            col1, col2 = st.columns(2)

            with col1:
                st.write("### Expected")
                st.write(
                    " → ".join(
                        result.get(
                            "expected_phonemes",
                            []
                        )
                    )
                )

            with col2:
                st.write("### Detected")
                st.write(
                    " → ".join(
                        result.get(
                            "spoken_phonemes",
                            []
                        )
                    )
                )

            # --------------------------------------------------
            # PHONEME ACCURACY
            # --------------------------------------------------
            st.metric(
                "🧩 Phoneme Accuracy",
                f"{result.get('phoneme_accuracy', 0)}%"
            )

            # --------------------------------------------------
            # PHONEME MATCHING
            # --------------------------------------------------
            st.write("### 🎯 Phoneme Matching")

            matches = result.get(
                "phoneme_matches",
                []
            )

            for match in matches:

                expected = match.get("expected", "")
                detected = match.get("detected", "")
                correct = match.get("correct", False)

                if correct:

                    st.success(
                        f"✅ {expected}"
                    )

                else:

                    st.error(
                        f"❌ Expected: {expected} | Got: {detected}"
                    )    


# --------------------------------------------------
# PATIENTS
# --------------------------------------------------
elif page == "👶 Patients":

    st.title("👶 Patients")

    tab1, tab2 = st.tabs(["Create Patient", "View Patients"])

    with tab1:

        st.subheader("Create New Child")

        name = st.text_input("Name")
        age = st.number_input("Age", 1, 18, 4)
        language = st.selectbox(
            "Language",
            ["English", "Hindi", "Telugu", "Tamil"]
        )

        if st.button("Create Patient"):

            payload = {
                "name": name,
                "age": age,
                "language": language
            }

            res = requests.post(
                f"{API}/patients/",
                json=payload
            )

            if res.status_code == 200:
                st.success("Patient Created ✅")
            else:
                st.error("Failed")

    with tab2:

        st.subheader("All Patients")

        try:
            res = requests.get(f"{API}/patients/")
            data = res.json()

            if len(data) > 0:
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No patients found")

        except:
            st.error("API not reachable")


# --------------------------------------------------
# PROGRESS
# --------------------------------------------------
elif page == "📈 Progress":

    st.title("📈 Progress Dashboard")

    st.info("Coming in V2: charts, trends, reports")
