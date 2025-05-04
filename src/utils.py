import torch
import torchaudio
import soundfile as sf
import io
import yt_dlp
import config
import os
from uuid import uuid4
from transformers import pipeline
from urllib.parse import urlparse
from TTS.api import TTS


def convert_to_wav_16khz_mono(audio_bytes):
    waveform, sample_rate = sf.read(io.BytesIO(audio_bytes))
    waveform = torch.tensor(waveform, dtype=torch.float32)

    # Transforms a multidimensional waveform into a one-dimensional form
    if waveform.ndim > 1 and waveform.shape[1] > 1:
        waveform = waveform.mean(dim=1)

    # Convert to 16khz
    if sample_rate != 16000:
        resampler = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=16000)
        waveform = resampler(waveform.unsqueeze(0)).squeeze(0)
        sample_rate = 16000

    return waveform, sample_rate


def load_model():
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    return pipeline("automatic-speech-recognition", model="openai/whisper-small", device=device, chunk_length_s=30)


def download_youtube_audio(url):
    file_path = f"{config.FILE_PATH}/{uuid4()}"

    ydl_opts = {
        "format": "bestaudio/best",
        "no_warnings": True,
        "quiet": True,
        "outtmpl": file_path,
        "restrictfilenames": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": config.DEFAULT_FORMAT,
                "preferredquality": "192",
            }
        ],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        file_path += f".{config.DEFAULT_FORMAT}"
        ydl.extract_info(url, download=True)

    waveform, sample_rate = torchaudio.load(file_path)
    if sample_rate != 16000 or waveform.shape[0] > 1:
        resampler = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=16000, lowpass_filter_width=128)
        waveform = resampler(waveform.mean(dim=0, keepdim=True))
        torchaudio.save(file_path, waveform, 16000)

    with open(file_path, "rb") as f:
        audio_buffer = f.read()

    if os.path.exists(file_path):
        os.remove(file_path)

    return audio_buffer


def is_url(text):
    try:
        result = urlparse(text)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def synthesize_text(text, lang, speaker):
    tts = TTS(model_name="tts_models/multilingual/multi-dataset/your_tts", progress_bar=True, gpu=True)

    file_path = f"{config.FILE_PATH}/{uuid4()}.wav"
    tts.tts_to_file(text=text, file_path=file_path, language=lang, speaker=tts.speakers[config.SPEAKER_MAP[lang][speaker]])

    with open(file_path, "rb") as f:
        audio_buffer = f.read()

    if os.path.exists(file_path):
        os.remove(file_path)

    return audio_buffer
