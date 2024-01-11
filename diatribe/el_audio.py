import os, glob, shutil, io
from typing import Any
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import diatribe.utils as utils
from elevenlabs import Voice, VoiceSettings, Model, Models, voices as el_voices, generate as el_generate
from pydub import AudioSegment as seg
from pedalboard import Pedalboard, Plugin
from pedalboard.io import AudioFile
from pathlib import Path
from diatribe.sidebar import SidebarData
from diatribe.utils import log
from diatribe.edits import AudioEdit, Pedal, BasicEdit, BackgroundEdit, CompressorEdit, LimiterEdit

class Soundboard:
  def __init__(self, edits: list[AudioEdit] = []) -> None:
    self.edits = edits
  
  def add(self, sounds: any) -> "Soundboard":
    if isinstance(sounds, list):
      self.edits.extend(sounds)
    else:
      self.edits.append(sounds)
    return self
  
  
  def basic(self) -> BasicEdit:
    base = None
    for edit in self.edits:
      if isinstance(edit, BasicEdit):
        base = edit
    return base
  
  def background(self) -> BackgroundEdit:
    background = None
    for edit in self.edits:
      if isinstance(edit, BackgroundEdit):
        background = edit
    return background
  
  def pedals(self) -> list[Pedal]:
    return list(filter(lambda x: isinstance(x, Pedal), self.edits))

  def is_enabled(self) -> bool:
    return any(x.is_enabled() for x in self.edits)
  
  def enabled(self) -> list[AudioEdit]:
    return list(filter(lambda x: x.is_enabled(), self.edits))

  def enabled_pedals(self) -> list[Plugin]:
    pedals = self.pedals()
    return [pedal.as_pedal() for pedal in pedals if pedal.is_enabled()]

  def adjustments(self) -> list[str]:
    adjustments = []
    for item in self.enabled():
      adjustments.extend(item.adjustments())
    return [f"`{a}`" for a in adjustments]
  

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

def export_audio(lines_to_copy: list[int], include_dialogue: bool = True) -> str:
  """Export the audio files from the audio folder to the export folder."""
  src_dir = f"./session/{st.session_state.session_id}/audio"
  dst_dir = f"./session/{st.session_state.session_id}/export/audio"

  if not os.path.exists(src_dir) or len(os.listdir(src_dir)) == 0:
    return None
  if os.path.exists(dst_dir):
    shutil.rmtree(dst_dir)
  os.makedirs(dst_dir, exist_ok=True)
  for line in lines_to_copy:
    try:
      shutil.copy(f"{src_dir}/line{line}.mp3", f"{dst_dir}/line{line}.mp3")
    except:
      log(f"line{line}.mp3 does not exist")
  if include_dialogue and os.path.exists(f"{src_dir}/dialogue.mp3"):
    shutil.copy(f"{src_dir}/dialogue.mp3", f"{dst_dir}/dialogue.mp3")
  return dst_dir

def export_dialogue_audio(lines_to_copy: list[int]) -> str:
  audio_dir = export_audio(lines_to_copy, include_dialogue=False)
  if audio_dir is None:
    return None
  export_path = f"./session/{st.session_state.session_id}/export/dialogue_audio/audio"
  os.makedirs(export_path, exist_ok=True)
  shutil.make_archive(export_path, "zip", audio_dir)
  return f"{export_path}.zip"   

def import_audio(src_dir: str) -> list[str]:
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

def generate_waveform_from_file(audio_file: str, y_max: float = None) -> (int, plt.Figure):
  status = st.spinner("Generating waveform...")
  with status:
    audio: seg = seg.from_mp3(audio_file)
    result = generate_waveform(audio, y_max)
  return result

def generate_waveform_from_bytes(audio_bytes: bytes, y_max: float) -> (int, plt.Figure):
  with st.spinner("Generating waveform..."):
    audio: seg = seg.from_wav(io.BytesIO(audio_bytes))
    return generate_waveform(audio, y_max)

def normalize_final_audio(audio: seg) -> seg:
  """Normalize the final audio."""
  log("applying audiobook normalization")
  soundboard = Soundboard([CompressorEdit(threshold=-18, ratio=3), LimiterEdit(threshold=-3)])
  final_audio = apply_soundboard(audio, soundboard)
  return final_audio

def join_audio(
  line_indices: list[int], 
  join_gap: int, 
  source_path: str = None,
  destination_path: str = None,
  normalize: bool = False
) -> None:
  """Join audio files found in the audio folder together with a gap in between with optional normalization."""
  if source_path is None or destination_path is None:
    source_path = f"./session/{st.session_state.session_id}/audio"
    destination_path = source_path
  
  audio_files = [f"{source_path}/line{i}.mp3" for i in line_indices]
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
  
  if normalize:
    final_audio = normalize_final_audio(final_audio)
  
  final_audio.export(f"{destination_path}/dialogue.mp3", format="mp3") 
  log(f"joined audio: {f'{destination_path}/dialogue.mp3'}")
  
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
  pedals = soundboard.enabled_pedals()

  if len(pedals) == 0:
    return audio
  
  log("applying soundboard")
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

def apply_basic(audio: seg, soundboard: Soundboard) -> seg:
  basic = soundboard.basic()
  
  if basic is None or not basic.is_enabled():
    return audio
  
  log("applying basic auido edits")

  if basic.volume != 0:
    audio = audio + basic.volume
  if basic.trim_in != 0:
    audio = audio[basic.trim_in:]
  if basic.trim_out != 0:
    new_end = int(audio.duration_seconds * 1000) - basic.trim_out
    audio = audio[:new_end]
  if basic.extend_in != 0:
    audio = seg.silent(basic.extend_in) + audio
  if basic.extend_out != 0:
    audio = audio + seg.silent(basic.extend_out)
  if basic.fade_in != 0:
    audio = audio.fade_in(basic.fade_in)
  if basic.fade_out != 0:
    audio = audio.fade_out(basic.fade_out)
  return audio  

def apply_background(dialogue_file: str, background_file: str, edit: BackgroundEdit) -> (seg, seg):
  if not edit.is_enabled():
    return None
  
  dialogue: seg = seg.from_mp3(dialogue_file)
  background: seg = seg.from_mp3(background_file)
  if background.duration_seconds > dialogue.duration_seconds:
    background = background[:dialogue.duration_seconds * 1000]
  if edit.volume > 0:
    background = background - edit.volume
  if edit.fade_in:
    background = background.fade_in(1500)
  if edit.fade_out:
    background = background.fade_out(1000)
  return dialogue, background

def apply_edits(audio_path: str, soundboard: Soundboard) -> seg:
  """Apply the soundboard edits to the audio."""
  audio: seg = seg.from_mp3(audio_path)
  audio = apply_basic(audio, soundboard)
  audio = apply_soundboard(audio, soundboard)
  return audio

def edit_audio(
  speech_path: str, 
  effect_path: str = None,
  start_effect: float = None,
  effect_volume: int = None,
  effect_repeat: int = None,
  effect_fade_out: int = None,
  soundboard: Soundboard = None
) -> (seg, seg):
  """Edit the audio file by changing the volume."""
  audio = apply_edits(speech_path, soundboard)
    
  # effects
  effect = None
  if effect_path:
    log("applying effect")
    effect: seg = seg.from_file(effect_path)
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
    effect_path, 
    start_effect,
    effect_volume,
    effect_repeat,
    effect_fade_out,
    soundboard
  )
  return segment_to_bytes(effect), segment_to_bytes(audio)

def get_default_effects() -> list[str]:
  """Get the effects from the effects folder."""
  return glob.glob("./effects/*")

def get_session_effects() -> list[str]:
  """Get the effects from the effects folder."""
  return glob.glob(f"./session/{st.session_state.session_id}/effects/*")

def process_effect_file(file: str) -> str:
  """Process the effect filename."""
  name = os.path.splitext(os.path.basename(file))[0]
  name = name.replace("_", " ")
  return name

@st.cache_data
def get_default_effect_names() -> list[str]:
  """Get the effect names from the effects folder."""
  names = [process_effect_file(f) for f in get_default_effects()]
  return names

def get_session_effect_names() -> list[str]:
  """Get the effect names from the session effects folder."""
  names = [process_effect_file(f) for f in get_session_effects()]
  return names

def get_effect_names() -> list[str]:
  default_effects = get_default_effect_names()
  session_effects = get_session_effect_names()
  return sorted(default_effects + session_effects)

def save_sound_effect(audio: bytes, name: str) -> None:
  audio: seg = seg.from_wav(io.BytesIO(audio))
  name = os.path.splitext(name)[0]
  output_path = f"./session/{st.session_state.session_id}/effects/{name}.mp3"
  os.makedirs(os.path.dirname(output_path), exist_ok=True)
  audio.export(output_path, format="mp3") 

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
  name = name.replace(' ', '_')
  files = glob.glob(f"./effects/{name}.*")
  if files:
    return files[0]
  else:
    files = glob.glob(f"./session/{st.session_state.session_id}/effects/{name}.*")
    if files:
      return files[0]
    else:
      return None

def apply_background_audio(
  lines_affected: list[int], 
  lines: list[int], 
  soundboard: Soundboard, 
  gap: int,
  normalize: bool
) -> None:
  """Apply the background audio to the dialogue audio."""
  # apply soundbar to each audio file matching to the line
  temp_audio_path = f"./session/{st.session_state.session_id}/temp/background"
  if os.path.exists(temp_audio_path):
    shutil.rmtree(temp_audio_path)
  os.makedirs(f"{temp_audio_path}/joined", exist_ok=True)
  shutil.copytree(f"./session/{st.session_state.session_id}/audio", f"{temp_audio_path}/lines", dirs_exist_ok=True)
  audio_files = [f"./session/{st.session_state.session_id}/audio/line{i}.mp3" for i in lines_affected] 
  for file in audio_files:
    audio = apply_edits(file, soundboard)
    audio.export(f"{temp_audio_path}/lines/{os.path.basename(file)}", format="mp3")
  
  # backup old dialogue audio
  shutil.copy(
    f"./session/{st.session_state.session_id}/audio/dialogue.mp3", 
    f"./session/{st.session_state.session_id}/audio/dialogue_org.mp3"
  )
  
  # join audio files together
  dialogue_path = f"{temp_audio_path}/joined"
  join_audio(
    lines, 
    gap, 
    normalize=normalize, 
    source_path=f"{temp_audio_path}/lines", 
    destination_path=dialogue_path
  )
  
  # add background over joined audio
  background_edit = soundboard.background()
  if background_edit is not None and background_edit.is_enabled():
    background_files = [str(x) for x in list(Path(".").glob("backgrounds/*.mp3"))]
    background_index = background_files.index(get_background_file_from_name(background_edit.name))
    background_file = background_files[background_index]  
    dialogue, background = apply_background(f"{dialogue_path}/dialogue.mp3", background_file, background_edit)
    final_dialgoue = dialogue.overlay(background)
  else:
    final_dialgoue = seg.from_mp3(f"{dialogue_path}/dialogue.mp3")
    
  final_dialgoue.export(f"./session/{st.session_state.session_id}/audio/dialogue.mp3", format="mp3")  
  st.session_state["background_added"] = ' '.join(soundboard.adjustments())
   