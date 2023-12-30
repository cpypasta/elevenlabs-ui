import os, el_audio, utils
import streamlit as st
from elevenlabs import Voice, set_api_key
from dataclasses import dataclass

@dataclass
class SidebarData:
  el_key: str
  model_id: str
  voices: list[Voice]
  voice_names: list[str]
  stability: float
  simarlity_boost: float
  style: float
  join_gap: int  

def get_voice_by_name(name: str, voices: list[Voice]) -> Voice:
  """Get a voice by the voice name."""
  name = utils.extract_name(name)
  return next((v for v in voices if v.name == name), None)

def get_cloned_voices(voices: list[Voice]) -> list[Voice]:
  """Get a list of cloned voices."""
  return [f"{v.name} (cloned)" for v in voices if v.category == "cloned"]

def voice_names_with_filter(
  voices: list[Voice], 
  gender: str, 
  age: str, 
  accent: str, 
  cloned: bool
) -> list[str]:
  """Get a list of voice names filtered by gender, age, accent, and cloned."""
  voice_names = []
  for v in voices:
    v_labels = v.labels
    v_gender = v_labels["gender"] if "gender" in v_labels else None
    v_age = v_labels["age"] if "age" in v_labels else None
    v_acccent = v_labels["accent"] if "accent" in v_labels else None
    match = True
    if gender and v_gender != gender:
      match = False
    if age and v_age != age:
      match = False
    if accent and v_acccent != accent:
      match = False
    if cloned:
      if v.category != "cloned":
        match = False
    if match:
      voice_names.append(f"{v.name} ({v.category})" if v.category == "cloned" else v.name)
  return voice_names

def create_sidebar() -> SidebarData:
  """Create the streamlit sidebar."""
  with st.sidebar:
    el_key = st.text_input("API Key", os.getenv("ELEVENLABS_API_KEY"), type="password")
    if el_key:
      set_api_key(el_key)          
    
      with st.expander("Voice Explorer"):
        el_voices = el_audio.get_voices()
        el_voice_names = [f"{voice.name}{' (cloned)' if voice.category == 'cloned' else ''}" for voice in el_voices]
        el_voice_accents = set([voice.labels["accent"] for voice in el_voices if "accent" in voice.labels])
        el_voice_ages = set([voice.labels["age"] for voice in el_voices if "age" in voice.labels])
        el_voice_genders = set([voice.labels["gender"] for voice in el_voices if "gender" in voice.labels])
        el_voice_accents = sorted(el_voice_accents, key=lambda x: x.lower())
        
        el_voice_cloned = st.toggle("Cloned Voices Only", value=False)
        el_voice_gender = st.selectbox("Gender Filter", el_voice_genders, index=None)
        el_voice_age = st.selectbox("Age Filter", el_voice_ages, index=None)
        el_voice_accent = st.selectbox("Accent Filter", el_voice_accents, index=None)
        
        speaker_voice_names = voice_names_with_filter(
          el_voices, 
          el_voice_gender, 
          el_voice_age, 
          el_voice_accent,
          el_voice_cloned
        )
        el_voice = st.selectbox("Speaker", speaker_voice_names)
        if el_voice:
          el_voice_details = get_voice_by_name(el_voice, el_voices)
          el_voice_id = el_voice_details.voice_id
          
          # voice sample        
          if el_voice_details.preview_url:
            st.audio(el_voice_details.preview_url, format="audio/mp3")
        
          st.markdown(f"_Voice ID: {el_voice_id}_") 
          
      with st.expander("Dialogue Options"):  
        models = el_audio.get_models()
        model_ids = [m.model_id for m in models]
        model_names = [m.name for m in models]
        model_name = st.selectbox("Speech Model", model_names)
        if model_name:
          model_index = model_names.index(model_name)
          model_id = model_ids[model_index]   
                                  
        stability = st.slider(
          "Stability", 
          0.0, 
          1.0, 
          value=0.35, 
          help="Increasing stability will make the voice more consistent between re-generations, but it can also make it sounds a bit monotone. On longer text fragments we recommend lowering this value."
        )
        simarlity_boost = st.slider(
          "Clarity + Simalarity Enhancement",
          0.0,
          1.0,
          value=0.80,
          help="High enhancement boosts overall voice clarity and target speaker similarity. Very high values can cause artifacts, so adjusting this setting to find the optimal value is encouraged."
        )
        style = st.slider(
          "Style Exaggeration",
          0.0,
          1.0,
          value=0.0,
          help="High values are recommended if the style of the speech should be exaggerated compared to the uploaded audio. Higher values can lead to more instability in the generated speech. Setting this to 0.0 will greatly increase generation speed and is the default setting."
        )
        join_gap = st.slider(
          "Gap Between Dialogue",
          0,
          1000,
          step=10,
          value=200,
          help="The gap between spoken lines in milliseconds."
        )
        
  return SidebarData(
    el_key=el_key,
    model_id=model_id,
    voices=el_voices,
    voice_names=el_voice_names,
    stability=stability,
    simarlity_boost=simarlity_boost,
    style=style,
    join_gap=join_gap
  )
  