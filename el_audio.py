import os, glob, utils
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from elevenlabs import Voice, VoiceSettings, Model, Models, voices as el_voices, generate as el_generate
from pydub import AudioSegment as seg
from sidebar import SidebarData
from utils import log

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
  if voice_index is not None:
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
  audio = el_generate(
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
  audio_file = f"./session/{st.session_state.session_id}/audio/line{line}.mp3"
  os.makedirs(os.path.dirname(audio_file), exist_ok=True)
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

def join_audio(line_indices: list[int], join_gap: int) -> None:
  """Join audio files found in the audio folder together with a gap in between."""
  audio_files = [f"./session/{st.session_state.session_id}/audio/line{i}.mp3" for i in line_indices]
  log(f"joining {len(audio_files)} audio files: {line_indices}")
  
  gap = seg.silent(join_gap)
  segments: list[seg] = []
  progress_text = "Joining audio..."
  joining_audio_bar = st.progress(0, text=progress_text)          
  for i, file in enumerate(audio_files):
    if os.path.exists(file):
      segments.append(seg.from_mp3(file))
    joining_audio_bar.progress(round((i+1) / len(audio_files), 2), text=progress_text)
    
  final_audio = segments[0]
  for i, s in enumerate(segments[1:]):
    final_audio += gap + s
    joining_audio_bar.progress(round((i+1) / len(segments[1:]), 2), text=progress_text)            
  final_audio.export(f"./session/{st.session_state.session_id}/audio/dialogue.mp3", format="mp3") 
  if "background_added" in st.session_state:
    del st.session_state["background_added"]
  joining_audio_bar.empty()
  
def clear_audio_files() -> None:
  """Clear all audio files from the audio directory."""
  for file in glob.glob(f"./session/{st.session_state.session_id}/audio/*.mp3"):
    os.remove(file)
  if not os.path.isdir(f"./session/{st.session_state.session_id}/audio"):
    os.makedirs(f"./session/{st.session_state.session_id}/audio", exist_ok=True)

@st.cache_data    
def get_background_audio() -> list[str]:
  """Return the names and audio for the background audio files."""
  names = []
  for file in glob.glob("./backgrounds/*.mp3"):
    name = os.path.basename(file).replace(".mp3", "").replace("_", " ")
    names.append(name)
  return names

def get_background_file_from_name(name: str) -> str:
  """Return the background audio file from the name."""
  return f"./backgrounds/{name.replace(' ', '_')}.mp3"

def apply_background_audio(background_name: str, fade_in: bool, fade_out: bool, lower_db: int) -> None:
  background_files = glob.glob("./backgrounds/*.mp3")
  background_index = background_files.index(get_background_file_from_name(background_name))
  background_file = background_files[background_index]
  dialogue_file = f"./session/{st.session_state.session_id}/audio/dialogue.mp3"
  
  dialogue: seg = seg.from_mp3(dialogue_file)
  background: seg = seg.from_mp3(background_file)
  if background.duration_seconds > dialogue.duration_seconds:
    background = background[:dialogue.duration_seconds * 1000]
  if lower_db > 0:
    background = background - lower_db
  if fade_in:
    background = background.fade_in(1500)
  if fade_out:
    background = background.fade_out(1000)
  
  final_dialgoue = dialogue.overlay(background)
  final_dialgoue.export(f"./session/{st.session_state.session_id}/audio/dialogue_background.mp3", format="mp3")  
  st.session_state["background_added"] = True
   