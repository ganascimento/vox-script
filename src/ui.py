import streamlit as st
import utils
import config
from origin_enum import OriginEnum


class UI:
    def __init__(self):
        if "pipe" not in st.session_state:
            st.session_state.pipe = utils.load_model()

        if "origin" not in st.session_state:
            st.session_state.origin = OriginEnum.FILE

        if "language" not in st.session_state:
            st.session_state.language = config.LANGUAGE_OPTIONS[0]

        if st.session_state.origin is None:
            st.session_state.origin = OriginEnum.FILE

    def build(self):
        st.set_page_config(page_title="Vox Script", layout="centered", page_icon="🗣️")
        st.title("🗣️ Vox Script")

        if st.session_state.pipe is None:
            return

        self.__build_sidebar()

        if st.session_state.origin in {OriginEnum.FILE, OriginEnum.YOUTUBE, OriginEnum.CONVERT}:
            st.session_state.language = st.selectbox("Select source language:", config.LANGUAGE_OPTIONS)

        audio_bytes = self.__build_by_origin()

        if not audio_bytes:
            return

        st.audio(audio_bytes, format="audio/wav")

        if st.session_state.origin in {OriginEnum.FILE, OriginEnum.YOUTUBE}:
            self.__convert_audio_to_text(audio_bytes)

    def __build_sidebar(self):
        st.sidebar.markdown("#### 🎧 Upload audio file to be transcribed")
        if st.sidebar.button("Upload", key="upload"):
            st.session_state.origin = OriginEnum.FILE

        st.sidebar.markdown("---")

        st.sidebar.markdown("#### ▶️ Submit a Youtube URL to be transcribed")
        if st.sidebar.button("Download", key="url-download"):
            st.session_state.origin = OriginEnum.YOUTUBE

        st.sidebar.markdown("---")

        st.sidebar.markdown("#### 📜 Convert text to audio (TTS)")
        if st.sidebar.button("Convert", key="convert"):
            st.session_state.origin = OriginEnum.CONVERT

    def __build_by_origin(self):
        if st.session_state.origin == OriginEnum.FILE:
            audio_file = st.file_uploader("Upload an audio file", type=config.AUDIO_EXT)
            if audio_file is not None:
                return audio_file.read()

        if st.session_state.origin == OriginEnum.YOUTUBE:
            url = st.text_input("Video URL:")
            if st.button("Get", disabled=url is None or url == "" or not utils.is_url(url)):
                with st.spinner("🔄 Download..."):
                    return utils.download_youtube_audio(url)

        if st.session_state.origin == OriginEnum.CONVERT:
            speaker = st.selectbox("Select speaker:", config.SPEAKER_OPTIONS)
            text = st.text_input("Text to convert:")

            if st.button("Convert", disabled=text is None or text == "" or speaker is None):
                with st.spinner("🔄 Converting..."):
                    return utils.synthesize_text(text, config.MAP_LANGUAGE_CODE_SPEAKER[st.session_state.language], speaker)

        return None

    def __convert_audio_to_text(self, audio_bytes: bytes):
        with st.spinner("🔄 Processing audio..."):
            try:
                waveform, sample_rate = utils.convert_to_wav_16khz_mono(audio_bytes)

                result = st.session_state.pipe(
                    {"raw": waveform.numpy(), "sampling_rate": sample_rate},
                    return_timestamps=True,
                    generate_kwargs={
                        "forced_decoder_ids": st.session_state.pipe.tokenizer.get_decoder_prompt_ids(
                            language=config.MAP_LANGUAGE_CODE[st.session_state.language], task="transcribe"
                        )
                    },
                )
                transcription = result["text"]

                st.success("✅ Transcription completed!")
                st.text_area("📝 Transcribed text:", transcription, height=300)

                if "chunks" in result:
                    st.subheader("Transcript Details:")
                    text_data = ""
                    for chunk in result["chunks"]:
                        text_data += f"- {chunk['text']}\n"

                    st.markdown(f"```{text_data}```")
            except Exception as e:
                st.error(f"❌ Error processing audio file: {e}")
