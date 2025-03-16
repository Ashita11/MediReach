import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import whisper
import av
from deep_translator import GoogleTranslator
import numpy as np

# Load Whisper model
model = whisper.load_model("tiny")

# Streamlit UI
st.title("🎤 Real-Time Speech Translation")
st.write("**Click 'Start Speaking' and then speak clearly into your microphone.**")

# Language selection
languages = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Hindi": "hi",
    "Chinese": "zh-cn",
    "Japanese": "ja",
}
target_lang = st.selectbox("Select target language:", list(languages.keys()))

# Placeholder for translated text
translated_text_placeholder = st.empty()

# Function to process audio
def process_audio(frame):
    audio_data = np.frombuffer(frame.to_ndarray(), dtype=np.int16).astype(np.float32) / 32768.0
    audio_path = "temp_audio.wav"

    # Save the audio file
    with open(audio_path, "wb") as f:
        f.write(audio_data.tobytes())

    # Transcribe using Whisper
    result = model.transcribe(audio_path)
    text = result["text"].strip()

    if text:
        # Translate using deep-translator
        translated_text = GoogleTranslator(source="auto", target=languages[target_lang]).translate(text)
        
        # Display results
        translated_text_placeholder.markdown(f"### 🎙 **You said:** {text}")
        translated_text_placeholder.markdown(f"### 🌍 **Translated:** {translated_text}")
    else:
        translated_text_placeholder.markdown("⚠️ No speech detected. Try speaking louder.")

# Button to start/stop microphone
if "mic_active" not in st.session_state:
    st.session_state.mic_active = False

if st.button("🎤 Start Speaking!!" if not st.session_state.mic_active else "⏹ Stop Speaking"):
    st.session_state.mic_active = not st.session_state.mic_active

# Start microphone only if button is clicked
if st.session_state.mic_active:
    webrtc_streamer(
        key="speech",
        mode=WebRtcMode.SENDRECV,
        audio_processor_factory=lambda: process_audio,
        media_stream_constraints={"audio": True, "video": False},
    )
