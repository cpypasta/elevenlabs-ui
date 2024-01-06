import os, glob, utils, shutil, io
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from elevenlabs import Voice, VoiceSettings, Model, Models, voices as el_voices, generate as el_generate
from pydub import AudioSegment as seg
from sidebar import SidebarData
from utils import log
from pedalboard import Pedalboard, Compressor, Chorus, Reverb, Distortion, NoiseGate
from pedalboard.io import AudioFile
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Soundboard:
  compressor_threshold_db: float
  compressor_ratio: float
  chorus_rate_hz: float
  chorus_depth: float
  chorus_centre_delay: float
  chorus_feedback: float
  reverb_room_size: float
  reverb_damping: float
  reverb_web_level: float
  reverb_dry_level: float
  distortion_db: float
  noise_gate_threshold_db: float
  noise_gate_ratio: float
  
  
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

def export_audio() -> None:
  """Export the audio files from the audio folder to the export folder."""
  src_dir = f"./session/{st.session_state.session_id}/audio"
  dst_dir = f"./session/{st.session_state.session_id}/export/audio"
  if os.path.exists(dst_dir):
    shutil.rmtree(dst_dir)
  shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True, ignore=shutil.ignore_patterns("dialogue.mp3"))

def import_audio() -> list[str]:
  src_dir = f"./session/{st.session_state.session_id}/import/contents/audio"
  dst_dir = f"./session/{st.session_state.session_id}/audio"
  if os.path.exists(dst_dir):
    shutil.rmtree(dst_dir)
  shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)  
  return glob.glob(f"{dst_dir}/*.mp3")

def get_generated_audio() -> list[str]:
  """Return whether the audio files have been generated."""
  return glob.glob(f"./session/{st.session_state.session_id}/audio/line*.mp3")

def generate_waveform(audio: seg, y_max: float = None) -> (int, plt.Figure):
  """Generate a waveform plot figure from the mp3 file."""  
  audio_array = np.frombuffer(audio.raw_data, dtype=np.int16)
  frame_rate = audio.frame_rate        
  num_samples = len(audio_array)
  length = num_samples / float(frame_rate)
  time_axis = np.linspace(0, length, num_samples) 
  fig, ax = plt.subplots()
  plt.gca().axis("off")       
  ax.plot(time_axis, audio_array)
  
  if y_max:
    ax.set_ylim(-y_max, y_max)
  _, max_y = ax.get_ylim()
  fig.set_figheight(2)
  
  return max_y, fig

def generate_waveform_from_file(audio_file: str) -> (int, plt.Figure):
  status = st.spinner("Generating waveform...")
  with status:
    audio: seg = seg.from_mp3(audio_file)
    result = generate_waveform(audio)
  return result

def generate_waveform_from_bytes(audio_bytes: bytes, y_max: float) -> (int, plt.Figure):
  with st.spinner("Generating waveform..."):
    audio: seg = seg.from_wav(io.BytesIO(audio_bytes))
    return generate_waveform(audio, y_max)

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
  return sorted(names)

def get_background_file_from_name(name: str) -> str:
  """Return the background audio file from the name."""
  return str(Path(f"./backgrounds/{name.replace(' ', '_')}.mp3"))
 
def segment_to_bytes(segment: seg) -> bytes:
  if segment is None:
    return None
  buffer = io.BytesIO()
  segment.export(buffer, format="wav")
  audio_bytes = buffer.getvalue()
  return audio_bytes 

def apply_soundboard(audio: seg, soundboard: Soundboard) -> seg:
  """Apply the soundboard to the audio."""
  pedals = []
  if soundboard.distortion_db != 0:
    pedals.append(Distortion(
      drive_db=soundboard.distortion_db
    ))  
  if soundboard.chorus_rate_hz != 0:
    pedals.append(Chorus(
      rate_hz=soundboard.chorus_rate_hz, 
      depth=soundboard.chorus_depth, 
      centre_delay_ms=soundboard.chorus_centre_delay, 
      feedback=soundboard.chorus_feedback
    ))
  if soundboard.reverb_room_size != 0:
    pedals.append(Reverb(
      room_size=soundboard.reverb_room_size, 
      damping=soundboard.reverb_damping,
      wet_level=soundboard.reverb_web_level,
      dry_level=soundboard.reverb_dry_level
    ))
  if soundboard.noise_gate_threshold_db != 0:
    pedals.append(NoiseGate(
      threshold_db=soundboard.noise_gate_threshold_db, 
      ratio=soundboard.noise_gate_ratio
    ))
  if soundboard.compressor_threshold_db != 0:
    pedals.append(Compressor(
      threshold_db=soundboard.compressor_threshold_db, 
      ratio=soundboard.compressor_ratio)
  )    
  if len(pedals) == 0:
    return audio
  applied_pedals = [pedal.__class__.__name__ for pedal in pedals]
  log(f"Applying pedals: {applied_pedals}")
  
  temp_input_filepath = f"./session/{st.session_state.session_id}/temp/in.wav"
  temp_output_filepath = f"./session/{st.session_state.session_id}/temp/out.wav"
  os.makedirs(os.path.dirname(temp_input_filepath), exist_ok=True)
  os.makedirs(os.path.dirname(temp_output_filepath), exist_ok=True)
  
  audio.export(temp_input_filepath, format="wav")
  samplerate = 44100.0
  with AudioFile(temp_input_filepath).resampled_to(samplerate) as f:
    temp_in = f.read(f.frames)
    
  pedalboard = Pedalboard(pedals)  
  samples = pedalboard(temp_in, samplerate)
  with AudioFile(
    temp_output_filepath, 
    "w", 
    samplerate, 
    samples.shape[0]
  ) as f:
    f.write(samples)
  new_audio = seg.from_wav(temp_output_filepath)
  os.remove(temp_input_filepath)
  os.remove(temp_output_filepath)
  return new_audio

def edit_audio(
  speech_path: str, 
  volume: int = None, 
  effect_path: str = None,
  start_effect: float = None,
  effect_volume: int = None,
  effect_repeat: int = None,
  effect_fade_out: int = None,
  soundboard: Soundboard = None
) -> (seg, seg):
  """Edit the audio file by changing the volume."""
  audio: seg = seg.from_mp3(speech_path)
  # basic settings
  if volume:
    audio = audio + volume
  
  # soundboard
  audio = apply_soundboard(audio, soundboard)
    
  # effects
  effect = None
  if effect_path:
    effect: seg = seg.from_wav(effect_path)
    if effect_volume:
      effect = effect + effect_volume
    if effect_repeat:
      effect = effect * effect_repeat
    
    audio_duration = audio.duration_seconds
    effect_duration = effect.duration_seconds
    effect_total_duration = effect_duration + start_effect
    default_effect_fade_out = effect_fade_out if effect_fade_out is not None and effect_fade_out > 0 else 1000

    if effect_total_duration > audio_duration:
      effect_excess = effect_total_duration - audio_duration
      effect = effect[:int((effect_duration - effect_excess) * 1000)]
      effect = effect.fade_out(default_effect_fade_out)
    elif effect_fade_out:
      effect = effect.fade_out(effect_fade_out)
    
    audio = audio.overlay(effect, position=start_effect * 1000)
  return effect, audio

def preview_audio(
  speech_path: str, 
  volume: int = None, 
  effect_path: str = None,
  start_effect: float = None,
  effect_volume: int = None,
  effect_repeat: int = None,
  effect_fade_out: int = None,
  soundboard: Soundboard = None
) -> (bytes, bytes):
  """Preview the audio file after editing."""
  effect, audio = edit_audio(
    speech_path, 
    volume, 
    effect_path, 
    start_effect,
    effect_volume,
    effect_repeat,
    effect_fade_out,
    soundboard
  )
  return segment_to_bytes(effect), segment_to_bytes(audio)

def get_effects() -> list[str]:
  """Get the effects from the effects folder."""
  return glob.glob("./effects/*.wav")

@st.cache_data
def get_effect_names() -> list[str]:
  """Get the effect names from the effects folder."""
  names = []
  for file in get_effects():
    name = os.path.basename(file).replace(".wav", "").replace("_", " ")
    names.append(name)
  return sorted(names)

def get_audio_duration(filename: str) -> float:
  """Get the duration of the speech in seconds."""
  audio: seg = seg.from_mp3(filename)
  return audio.duration_seconds

def get_audio_max_decibels(filename: str) -> (int, int):
  """Get the max volume of the audio."""
  audio: seg = seg.from_mp3(filename)
  return audio.max_dBFS

def get_effect_path(name: str) -> str:
  """Get the effect path from the effect name."""
  return f"./effects/{name.replace(' ', '_')}.wav"

def apply_background_audio(background_name: str, fade_in: bool, fade_out: bool, lower_db: int) -> None:
  """Apply the background audio to the dialogue audio."""
  background_files = [str(x) for x in list(Path(".").glob("backgrounds/*.mp3"))]
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
   