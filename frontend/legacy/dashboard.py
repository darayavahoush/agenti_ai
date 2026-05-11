import streamlit as st
import requests
import pandas as pd

# ---------------------------------
# PAGE CONFIG
# ---------------------------------
st.set_page_config(
    page_title="VaakSiddhi AI",
    page_icon="🎤",
    layout="wide"
)

API_URL = "http://127.0.0.1:8000"

# ---------------------------------
# TITLE
# ---------------------------------
st.title("🎤 VaakSiddhi AI Speech Dashboard")
st.markdown("Upload child speech and analyze voice instantly.")

st.divider()

# ---------------------------------
# FUNCTIONS
# ---------------------------------
def get_all_patients():
    try:
        res = requests.get(f"{API_URL}/patients")
        if res.status_code == 200:
            return res.json()
        return []
    except:
        return []

def get_or_create_patient(name, age, language):
    patients = get_all_patients()

    # Search by name
    for p in patients:
        if p["name"].strip().lower() == name.strip().lower():
            return p["id"], p["name"]

    # Create if not found
    payload = {
        "name": name,
        "age": age,
        "language": language
    }

    res = requests.post(f"{API_URL}/create-patient", json=payload)

    if res.status_code == 200:
        data = res.json()
        return data["id"], data["name"]

    return None, None


# ---------------------------------
# SIDEBAR
# ---------------------------------
st.sidebar.header("👶 Child Details")

name = st.sidebar.text_input("Enter Child Name")
age = st.sidebar.number_input("Age", min_value=1, max_value=18, value=4)
language = st.sidebar.selectbox(
    "Language",
    ["English", "Hindi", "Telugu", "Tamil", "Kannada"]
)

uploaded_file = st.sidebar.file_uploader(
    "Upload Audio File",
    type=["wav", "mp3", "mpeg", "m4a"]
)

analyze_btn = st.sidebar.button("🚀 Analyze Speech")

# ---------------------------------
# MAIN
# ---------------------------------
if analyze_btn:

    if name == "":
        st.warning("Please enter child name.")
        st.stop()

    if uploaded_file is None:
        st.warning("Please upload audio file.")
        st.stop()

    # ---------------------------------
    # Create/Get Patient
    # ---------------------------------
    with st.spinner("Checking patient..."):
        patient_id, patient_name = get_or_create_patient(name, age, language)

    if patient_id is None:
        st.error("Patient creation failed.")
        st.stop()

    # ---------------------------------
    # Upload Audio
    # ---------------------------------
    with st.spinner("Uploading audio..."):

        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                uploaded_file.type
            )
        }

        upload_res = requests.post(
            f"{API_URL}/upload-audio",
            files=files
        )

    if upload_res.status_code != 200:
        st.error("Audio upload failed.")
        st.stop()

    file_path = upload_res.json()["file_path"]

    # ---------------------------------
    # Analyze Audio
    # ---------------------------------
    with st.spinner("Analyzing speech..."):

        analyze_res = requests.post(
            f"{API_URL}/analyze-audio",
            params={
                "patient_id": patient_id,
                "file_path": file_path
            }
        )

    if analyze_res.status_code != 200:
        st.error("Speech analysis failed.")
        st.stop()

    result = analyze_res.json()

    # ---------------------------------
    # SUCCESS
    # ---------------------------------
    st.success("✅ Analysis Completed")

    st.subheader(f"👶 Child: {patient_name}")

    # ---------------------------------
    # METRICS
    # ---------------------------------
    c1, c2, c3 = st.columns(3)
    c1.metric("🎵 Pitch", round(result["pitch"], 2))
    c2.metric("🔊 Loudness", round(result["loudness"], 4))
    c3.metric("🌡 Pressure", round(result["pressure"], 2))

    c4, c5, c6 = st.columns(3)
    c4.metric("⏱ Duration", round(result["duration"], 2))
    c5.metric("⭐ Score", result["score"])
    c6.metric("🆔 Session", result["session_id"][:8])

    st.divider()

    # ---------------------------------
    # REPORT TABLE
    # ---------------------------------
    st.subheader("📄 Full Report")

    df = pd.DataFrame([result])
    st.dataframe(df, use_container_width=True)

else:
    st.info("👈 Enter child name, upload audio, and click Analyze Speech.")