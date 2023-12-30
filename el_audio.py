import re, os, glob, utils
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from elevenlabs import Voice, VoiceSettings, Model, Models, voices as el_voices, generate
from pydub import AudioSegment as seg
from sidebar import SidebarData

@st.cache_data
def get_voices() -> list[Voice]:
  """Get a list of voices from the Eleven Labs API."""
  voices: list[Voice] = list(el_voices())
  voices.sort(key=lambda x: x.name)
  return voices

def get_voice_id(voice_name: str, voices: list[Voice]) -> str:
  """Get the voice ID from the voice name."""
  voice_name = utils.extract_name(voice_name)
  voice_index = next((i for i, v in enumerate(voices) if v.name == voice_name), None)
  if voice_index:
    return voices[voice_index].voice_id
  else:
    return ""

@st.cache_data
def get_models() -> list[Model]:
  """Get a list of speech models from the Eleven Labs API."""
  return list(Models.from_api())

def generate(
  text: str,
  voice_id: str,
  sidebar_data: SidebarData 
) -> bytes:
  """Generate audio from a dialogue."""
  audio = generate(
    text=text,
    model=sidebar_data.model_id,
    voice = Voice(
      voice_id=voice_id,
      settings=VoiceSettings(
        stability=sidebar_data.stability,
        similarity_boost=sidebar_data.simarlity_boost,
        style=sidebar_data.style
      )
    )
  )  
  return audio

def generate_and_save(
  text: str,
  voice_id: str,
  line: int,
  sidebar_data: SidebarData
) -> str:
  """Generate audio from a dialogue and save it to a file."""
  audio = generate(text, voice_id, sidebar_data)
  audio_file = f"./audio/line{line}.mp3"
  with open(audio_file, "wb") as f:
    f.write(audio)  
  return audio_file

def generate_waveform(audio_path: str) -> plt.Figure:
  """Generate a waveform plot figure from the mp3 file."""
  audio: seg = seg.from_mp3(audio_path)
  audio_array = np.frombuffer(audio.raw_data, dtype=np.int16)
  frame_rate = audio.frame_rate        
  num_samples = len(audio_array)
  length = num_samples / float(frame_rate)
  time_axis = np.linspace(0, length, num_samples) 
  fig, ax = plt.subplots()
  plt.gca().axis("off")       
  ax.plot(time_axis, audio_array)
  fig.set_figheight(2)
  return fig

def join_audio(audio_files: list[str], join_gap: int) -> None:
  """Join audio files together with a gap in between."""
  gap = seg.silent(join_gap)
  segments: list[seg] = []
  progress_text = "Joining audio..."
  joining_audio_bar = st.progress(0, text=progress_text)          
  for i, file in enumerate(audio_files):
    segments.append(seg.from_mp3(file))
    joining_audio_bar.progress(round((i+1) / len(audio_files), 2), text=progress_text)
  final_audio = segments[0]
  for i, s in enumerate(segments[1:]):
    final_audio += gap + s
    joining_audio_bar.progress(round((i+1) / len(segments[1:]), 2), text=progress_text)            
  final_audio.export("./audio/dialogue.mp3", format="mp3")  
  joining_audio_bar.empty()
  
def clear_audio_files() -> None:
  """Clear all audio files from the audio directory."""
  for file in glob.glob("./audio/*.mp3"):
    os.remove(file)
  if not os.path.isdir("./audio"):
    os.mkdir("./audio")