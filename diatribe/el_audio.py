import os, glob, shutil, io, traceback
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import diatribe.utils as utils
from elevenlabs import Voice, VoiceSettings, Model, Models, voices as el_voices, generate as el_generate
from pydub import AudioSegment as seg
from pedalboard import Pedalboard, Plugin
from pedalboard.io import AudioFile
from math import ceil
from diatribe.sidebar import SidebarData
from diatribe.utils import log
from diatribe.edits import *

class Soundboard:
  def __init__(self, edits: list[AudioEdit] = []) -> None:
    self.edits = edits
  
  def add(self, sounds: any) -> "Soundboard":
    if isinstance(sounds, list):
      self.edits.extend(sounds)
    else:
      self.edits.append(sounds)
    return self
  
  def _get(self, edit_type: type) -> AudioEdit:
    edit = EmptyEdit()
    for e in self.edits:
      if isinstance(e, edit_type):
        edit = e
    return edit
  
  def basic(self) -> BasicEdit:
    return self._get(BasicEdit)
  
  def background(self) -> BackgroundEdit:
    return self._get(BackgroundEdit)
  
  def special_effect(self) -> SpecialEffectEdit:
    return self._get(SpecialEffectEdit)
  
  def normalization(self) -> NormalizationEdit:
    return self._get(NormalizationEdit)
  
  def pedals(self) -> list[Pedal]:
    return list(filter(lambda x: isinstance(x, Pedal), self.edits))

  def is_enabled(self) -> bool:
    return any(x.is_enabled() for x in self.edits)
  
  def enabled(self) -> list[AudioEdit]:
    return list(filter(lambda x: x.is_enabled(), self.edits))

  def enabled_pedals(self) -> list[Plugin]:
    pedals = self.pedals()
    return [pedal.as_pedal() for pedal in pedals if pedal.is_enabled()]

  def pedal_adjustments(self) -> list[str]:
    adjustments = []
    pedals = [p.adjustments() for p in self.enabled() if isinstance(p, Pedal)]
    for item in pedals:
      adjustments.extend(item)
    return [f"`{a}`" for a in adjustments]

  def adjustments(self) -> list[str]:
    adjustments = []
    for item in self.enabled():
      adjustments.extend(item.adjustments())
    return [f"`{a}`" for a in adjustments]
  

@dataclass
class AudioPart:
  lines: list[int]
  edited: bool
  
  def __str__(self):
    return f"{self.lines};{self.edited}"
  

@dataclass
class AudioLine:
  line: int = None
  file: str = None


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
    return None


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
  try:
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
  except:
    traceback.print_exc()
  return audio


def generate_and_save(
  text: str,
  voice_id: str,
  line: int,
  sidebar_data: SidebarData
) -> str:
  """Generate audio from a dialogue and save it to a file."""
  audio = generate(text, voice_id, sidebar_data)
  audio_file = f"./session/{st.session_state.session_id}/audio/line{line}.wav"
  os.makedirs(os.path.dirname(audio_file), exist_ok=True)
  with open(audio_file, "wb") as f:
    f.write(audio)  
  return audio_file


def export_source_audio(
  lines_to_copy: list[int], 
  src_dir: str, 
  dst_dir: str,
  include_dialogue: bool
) -> None:
  """Export the audio files from source to destination."""
  if not os.path.exists(src_dir) or len(os.listdir(src_dir)) == 0:
    return
  if os.path.exists(dst_dir):
    shutil.rmtree(dst_dir)
  os.makedirs(dst_dir, exist_ok=True)
  
  for line in lines_to_copy:
    try:
      shutil.copy(f"{src_dir}/line{line}.wav", f"{dst_dir}/line{line}.wav")
    except:
      log(f"line{line}.wav does not exist")
      
  if include_dialogue and os.path.exists(f"{src_dir}/dialogue.mp3"):
    shutil.copy(f"{src_dir}/dialogue.mp3", f"{dst_dir}/dialogue.mp3")


def export_audio(lines_to_copy: list[int], include_dialogue: bool = True) -> str:
  """Export the audio files from the audio folder to the export folder."""
  line_src_dir = f"./session/{st.session_state.session_id}/audio"
  final_src_dir = f"./session/{st.session_state.session_id}/final/audio"
  line_dst_dir = f"./session/{st.session_state.session_id}/export/audio"
  final_dst_dir = f"./session/{st.session_state.session_id}/export/final/audio"

  export_source_audio(lines_to_copy, line_src_dir, line_dst_dir, include_dialogue)
  export_source_audio(lines_to_copy, final_src_dir, final_dst_dir, include_dialogue)
  return f"./session/{st.session_state.session_id}/export"  


def import_source_audio(src_dir: str, dst_dir: str) -> None:
  shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True) 


def import_audio(src_dir: str) -> list[str]:
  dest_audio = f"./session/{st.session_state.session_id}/audio"
  dest_final_audio = f"./session/{st.session_state.session_id}/final/audio"
  if os.path.exists(dest_audio):
    shutil.rmtree(dest_audio)
  if os.path.exists(dest_final_audio):
    shutil.rmtree(dest_final_audio)
  os.makedirs(dest_audio, exist_ok=True)
  os.makedirs(dest_final_audio, exist_ok=True)
  
  line_dir = f"{src_dir}/audio"
  if os.path.exists(line_dir):
    import_source_audio(line_dir, dest_audio)
  final_dir = f"{src_dir}/final/audio"
  if os.path.exists(final_dir) and len(glob.glob(f"{final_dir}/line*")) > 0:
    import_source_audio(final_dir, dest_final_audio)
  else:
    if os.path.exists(f"{final_dir}/dialogue.mp3"):
      shutil.copy(f"{final_dir}/dialogue.mp3", f"{dest_final_audio}/dialogue.mp3")
    import_source_audio(line_dir, dest_final_audio)
  return glob.glob(f"{dest_audio}/line*.wav")


def get_generated_audio() -> list[str]:
  """Return whether the audio files have been generated."""
  return glob.glob(f"./session/{st.session_state.session_id}/audio/line*.wav")


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


def normalize_final_audio(dialogue_path: str) -> None:
  """Normalize the final audio."""
  log("applying audiobook normalization")
  audio = seg.from_mp3(f"{dialogue_path}/dialogue.mp3")
  soundboard = Soundboard([
    CompressorEdit(threshold=-23, ratio=2, attack=150, release=150), 
    LimiterEdit(threshold=-1, release=250)
  ])
  audio = apply_soundboard(audio, soundboard)
  audio.export(f"{dialogue_path}/dialogue.mp3", format="mp3")   


def overlap_and_extend(one: seg, two: seg, overlap: int) -> seg:
  """Overlap the two audio segments and extend the second segment."""
  offset = len(one) - overlap
  return one.overlay(two, position=offset) + two[overlap:]


def join_files(
  audio_lines: list[AudioLine],
  source_path: str,
  destination_filename: str,
  join_gap: int
) -> None:
  final_audio: seg = None
  gap = seg.silent(join_gap)
  for line in audio_lines:
    audio_file = f"{source_path}/{line.file}"
    if os.path.exists(audio_file):
      if final_audio is None:
        final_audio = seg.from_file(audio_file)
      else:
        final_audio += gap + seg.from_file(audio_file).fade_out(300)
    else:
      log(f"audio file does not exist: {audio_file}")

  format = os.path.splitext(os.path.basename(destination_filename))[1].replace(".", "")
  final_audio.export(destination_filename, format=format)  


def join_lines(
  lines: list[int],
  join_gap: int,
  source_path: str = None,
  destination_filename: str = None
) -> None:
  audio_lines = []  
  for line in lines:
    audio_lines.append(AudioLine(line, f"line{line}.wav"))
  
  join_files(
    audio_lines, 
    source_path, 
    destination_filename, 
    join_gap
  )
  
  
def join_parts(
  join_gap: int,
  source_path: str = None,
  destination_filename: str = None,
) -> None:
  audio_files = [os.path.basename(f) for f in glob.glob(f"{source_path}/part*.wav")]
  audio_lines = []
  for file in audio_files:
    line = int(os.path.splitext(file)[0].replace("part", ""))
    audio_lines.append(AudioLine(line, file))
    
  join_files(
    audio_lines, 
    source_path, 
    destination_filename, 
    join_gap
  )
  

def join_audio(
  line_indices: list[int], 
  join_gap: int = 200, 
  source_path: str = None,
  destination_path: str = None,
  copy_lines: bool = True
) -> None:
  """Join audio files found in the audio folder together with a gap in between with optional normalization."""
  if source_path is None or destination_path is None:
    source_path = f"./session/{st.session_state.session_id}/audio"
    destination_path = f"./session/{st.session_state.session_id}/final/audio"
    parts_path = f"./session/{st.session_state.session_id}/final/parts"
    
  if os.path.exists(destination_path):
    shutil.rmtree(destination_path)
  os.makedirs(destination_path, exist_ok=True)
  if os.path.exists(parts_path):
    shutil.rmtree(parts_path)
  os.makedirs(parts_path, exist_ok=True)
  
  audio_files = [f"{source_path}/line{i}.wav" for i in line_indices]
  if copy_lines:
    shutil.copytree(source_path, destination_path, dirs_exist_ok=True)
  log(f"joining {len(audio_files)} audio files: {line_indices}")
  
  gap = seg.silent(join_gap)
  segments: list[seg] = []
  progress_text = "Preparing audio..."
  joining_audio_bar = st.progress(0, text=progress_text)          
  for i, file in enumerate(audio_files):
    if os.path.exists(file):
      segments.append(seg.from_mp3(file))
    joining_audio_bar.progress(round((i+1) / len(audio_files), 2), text=progress_text)
  joining_audio_bar.empty()
    
  progress_text = "Joining audio..."
  joining_audio_bar = st.progress(0, text=progress_text) 
  final_audio = segments[0]
  for i, s in enumerate(segments[1:]):
    final_audio += gap + s.fade_out(300)
    joining_audio_bar.progress(round((i+1) / len(segments[1:]), 2), text=progress_text)  
  
  final_audio.export(f"{destination_path}/dialogue.mp3", format="mp3") 
  joining_audio_bar.empty()
  
  if "background_added" in st.session_state:
    del st.session_state["background_added"]
  
  
def clear_audio_files() -> None:
  """Clear all audio files from the audio directory."""
  shutil.rmtree(f"./session/{st.session_state.session_id}/audio", ignore_errors=True)
  os.makedirs(f"./session/{st.session_state.session_id}/audio", exist_ok=True)

 
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
  
  log(f"applying soundboard {', '.join(soundboard.pedal_adjustments())}")
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


def prepare_background(dialogue_file: str, background_file: str, edit: BackgroundEdit) -> (seg, seg):
  if not edit.is_enabled():
    return None
  
  dialogue: seg = seg.from_mp3(dialogue_file)
  background: seg = seg.from_mp3(background_file)
  if len(background) > len(dialogue):
    background = background[:len(dialogue)]
  if len(dialogue) > len(background):
    difference = len(dialogue) - len(background)
    repeats = ceil(difference / len(background)) + 1
    background = background * repeats
    background = background[:len(dialogue)]
  if edit.volume > 0:
    background = background - edit.volume
  if edit.fade_in:
    background = background.fade_in(800)
  if edit.fade_out:
    background = background.fade_out(800)
  return dialogue, background


def apply_special_effect(audio: seg, soundboard: Soundboard) -> seg:
  special_effect = soundboard.special_effect()
  if special_effect.is_enabled():
    log("applying effect")
    effect_path = special_effect.path
    effect_volume = special_effect.volume
    effect_repeat = special_effect.repeat
    start_effect = special_effect.start
    effect_fade_out = special_effect.fade_out
    
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
  return audio


def apply_edits(audio_path: str, soundboard: Soundboard) -> seg:
  """Apply the soundboard edits to the audio."""
  audio: seg = seg.from_mp3(audio_path)
  audio = apply_basic(audio, soundboard)
  audio = apply_soundboard(audio, soundboard)
  audio = apply_special_effect(audio, soundboard)
  return audio


def edit_audio(
  speech_path: str, 
  soundboard: Soundboard = None
) -> seg:
  """Edit the audio file by changing the volume."""
  audio = apply_edits(speech_path, soundboard)
  return audio


def preview_audio(
  speech_path: str, 
  soundboard: Soundboard = None
) -> bytes:
  """Preview the audio file after editing."""
  audio = edit_audio(
    speech_path, 
    soundboard
  )
  return segment_to_bytes(audio)


def get_default_effects() -> list[str]:
  """Get the effects from the effects folder."""
  return glob.glob("./effects/*")


def get_session_effects() -> list[str]:
  """Get the effects from the effects folder."""
  return glob.glob(f"./session/{st.session_state.session_id}/effects/*")


def process_audio_file_name(file: str) -> str:
  """Process the effect filename."""
  name = os.path.splitext(os.path.basename(file))[0]
  name = name.replace("_", " ")
  return name


@st.cache_data
def get_default_effect_names() -> list[str]:
  """Get the effect names from the effects folder."""
  names = [process_audio_file_name(f) for f in get_default_effects()]
  return names


def get_session_effect_names() -> list[str]:
  """Get the effect names from the session effects folder."""
  names = [process_audio_file_name(f) for f in get_session_effects()]
  return names


def get_effect_names() -> list[str]:
  default_effects = get_default_effect_names()
  session_effects = get_session_effect_names()
  return sorted(default_effects + session_effects)


def save_sound_effect(audio: bytes, name: str) -> None:
  audio: seg = seg.from_file(io.BytesIO(audio))
  name = os.path.splitext(name)[0]
  output_path = f"./session/{st.session_state.session_id}/effects/{name}.wav"
  os.makedirs(os.path.dirname(output_path), exist_ok=True)
  audio.export(output_path, format="wav") 


def get_default_backgrounds() -> list[str]:
  """Get the backgrounds from the backgrounds folder."""
  return glob.glob("./backgrounds/*")


def get_session_backgrounds() -> list[str]:
  """Get the backgrounds from the backgrounds folder."""
  return glob.glob(f"./session/{st.session_state.session_id}/backgrounds/*")


def get_default_background_names() -> list[str]:
  """Get the background names from the backgrounds folder."""
  names = [process_audio_file_name(f) for f in get_default_backgrounds()]
  return names


def get_session_background_names() -> list[str]:
  """Get the background names from the session backgrounds folder."""
  names = [process_audio_file_name(f) for f in get_session_backgrounds()]
  return names


def get_background_files() -> list[str]:
  return get_default_backgrounds() + get_session_backgrounds()


def get_background_names() -> list[str]:
  default_backgrounds = get_default_background_names()
  session_backgrounds = get_session_background_names()
  return sorted(default_backgrounds + session_backgrounds)


def save_background_audio(audio: bytes, name: str) -> None:
  audio: seg = seg.from_file(io.BytesIO(audio))
  name = os.path.splitext(name)[0]
  output_path = f"./session/{st.session_state.session_id}/backgrounds/{name}.mp3"
  os.makedirs(os.path.dirname(output_path), exist_ok=True)
  audio.export(output_path, format="mp3")


def get_audio_duration(filename: str) -> float:
  """Get the duration of the speech in seconds."""
  audio: seg = seg.from_mp3(filename)
  return audio.duration_seconds


def get_line_duration(line: int) -> float:
  """Get the duration of the speech in seconds."""
  filename = f"./session/{st.session_state.session_id}/audio/line{line}.wav"
  return len(seg.from_mp3(filename))


def get_audio_max_decibels(filename: str) -> (int, int):
  """Get the max volume of the audio."""
  audio: seg = seg.from_mp3(filename)
  return audio.max_dBFS


def get_asset_path_from_name(name: str, folder: str) -> str:
  name = name.replace(' ', '_')
  files = glob.glob(f"./{folder}/{name}.*")
  if files:
    return files[0]
  else:
    files = glob.glob(f"./session/{st.session_state.session_id}/{folder}/{name}.*")
    if files:
      return files[0]
    else:
      return None


def get_effect_path(name: str) -> str:
  """Get the effect path from the effect name."""
  return get_asset_path_from_name(name, "effects")


def get_background_path(name: str) -> str:
  """Get the background path from the background name."""
  return get_asset_path_from_name(name, "backgrounds")


def apply_background_audio(background_edit: BackgroundEdit, destination_path: str) -> None:
  background_files = get_background_files()
  background_index = background_files.index(get_background_path(background_edit.name))
  background_file = background_files[background_index]  
  dialogue, background = prepare_background(destination_path, background_file, background_edit)
  final_dialogue: seg = dialogue.overlay(background)
  final_dialogue.export(destination_path, format="wav")  


def get_contiguous_lines(affected_lines: list[int], all_lines: list[int]) -> list[AudioPart]:
  """Get the contiguous lines from the list of lines."""
  parts: list[AudioPart] = []
  for i, line in enumerate(all_lines):
    if line in affected_lines:
      if i == 0 or all_lines[i-1] not in affected_lines:
        parts.append(AudioPart([line], True))
      else:
        parts[-1].lines.append(line)
    else:
      if i == 0 or all_lines[i-1] in affected_lines:
        parts.append(AudioPart([line], False))
      else:
        parts[-1].lines.append(line)
        
  return parts
  

def master_audio_parts(
  affected_lines: list[int], 
  lines: list[int], 
  soundboard: Soundboard,
  gap: int, 
  parts_audio_path: str, 
  destination_audio_path: str,
  dialogue_path: str
) -> None:
  audio_parts: list[AudioPart] = get_contiguous_lines(affected_lines, lines)
  for i, part in enumerate(audio_parts):
    part_path = f"{parts_audio_path}/part{i+1}.wav"
    if not os.path.exists(part_path):
      join_lines(
        part.lines, 
        gap, 
        destination_audio_path, 
        part_path
      )
    if part.edited:
      part_audio = apply_edits(part_path, soundboard)
      part_audio.export(part_path, format="wav")
      background_edit = soundboard.background()
      if background_edit is not None and background_edit.is_enabled():
        apply_background_audio(background_edit, part_path)      
  
  join_parts(
    gap, 
    parts_audio_path, 
    dialogue_path
  )  


def preview_mastered_audio(
  affected_lines: list[int], 
  lines: list[int], 
  soundboard: Soundboard, 
  gap: int
) -> (str, str):  
  src_audio_path = f"./session/{st.session_state.session_id}/final/audio"
  src_parts_path = f"./session/{st.session_state.session_id}/final/parts"
  destination_audio_path = f"./session/{st.session_state.session_id}/temp/audio"
  parts_audio_path = f"./session/{st.session_state.session_id}/temp/parts"
    
  dialogue_path = f"{destination_audio_path}/dialogue.mp3"
  os.makedirs(parts_audio_path, exist_ok=True)
  
  if os.path.exists(destination_audio_path):
    shutil.rmtree(destination_audio_path)
  os.makedirs(destination_audio_path, exist_ok=True)

  if os.path.exists(parts_audio_path):
    shutil.rmtree(parts_audio_path)
  os.makedirs(parts_audio_path, exist_ok=True)
  if os.path.exists(src_parts_path):
    shutil.copytree(src_parts_path, parts_audio_path, dirs_exist_ok=True)
  
  master_audio_parts(
    affected_lines,
    lines,
    soundboard,
    gap,
    parts_audio_path,
    src_audio_path,
    dialogue_path
  )
  
  if soundboard.normalization().is_enabled():
    normalize_final_audio(destination_audio_path) 
    
  original_audio = f"{src_audio_path}/dialogue.mp3"
  return original_audio, dialogue_path


def apply_mastered_audio(
  affected_lines: list[int], 
  lines: list[int], 
  soundboard: Soundboard, 
  gap: int
) -> None:
  src_audio_path = f"./session/{st.session_state.session_id}/final/audio"
  src_parts_path = f"./session/{st.session_state.session_id}/final/parts"
  destination_audio_path = f"./session/{st.session_state.session_id}/final/audio"
  parts_audio_path = src_parts_path
  dialogue_path = f"{destination_audio_path}/dialogue.mp3"
  
  os.makedirs(src_parts_path, exist_ok=True)
  
  shutil.copy(
    f"{src_audio_path}/dialogue.mp3", 
    f"{src_audio_path}/dialogue_org.mp3"
  )    
  
  master_audio_parts(
    affected_lines,
    lines,
    soundboard,
    gap,
    parts_audio_path,
    destination_audio_path,
    dialogue_path
  )
  
  if soundboard.normalization().is_enabled():
    normalize_final_audio(destination_audio_path) 