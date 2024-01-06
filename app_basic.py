import os
import streamlit as st
import elevenlabs as el
from dotenv import load_dotenv

load_dotenv()

@st.cache_data
def get_voices() -> list[el.Voice]:
  voices = list(el.voices())
  voices.sort(key=lambda x: x.name)
  return voices

@st.cache_data
def get_models() -> list[el.Model]:
  return list(el.Models.from_api())

def voice_names_with_filter(
  voices: list[el.Voice], 
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

if __name__ == "__main__":
  st.set_page_config(page_title="ElevenLabs Speech", page_icon="🎧")
  
  st.title("🎧 ElevenLabs Speech")
  
  with st.sidebar:
    el_key = st.text_input("API Key", os.getenv("ELEVENLABS_API_KEY"), type="password")
    if el_key:
      el.set_api_key(el_key)          
      models = get_models()
      model_ids = [m.model_id for m in models]
      model_names = [m.name for m in models]
      model_name = st.selectbox("Model", model_names, model_names.index("Eleven Turbo v2"))
      if model_name:
        model_index = model_names.index(model_name)
        model_id = model_ids[model_index]
    
      el_voices = get_voices()
      
      with st.expander("Voice Selection", expanded="expand_voices" not in st.session_state):
        st.session_state["expand_voices"] = True
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
          el_voice_index = el_voice_names.index(el_voice)
          el_voice_details = el_voices[el_voice_index]
          el_voice_id = el_voice_details.voice_id
          
          # voice sample
          if el_voice_details.preview_url:
            st.audio(el_voice_details.preview_url, format="audio/mp3")
        
      with st.expander("Voice Options"):      
        # voice settings
        if el_voice_details.settings:
          voice_settings = el_voice_details.settings
        else:
          el_voice_details.fetch_settings()
          voice_settings = el_voice_details.settings
        if not voice_settings:
          print("default settings")
          voice_settings = el.Voice.default_settings()
        
        stability = st.slider(
          "Stability", 
          0.0, 
          1.0, 
          value=voice_settings.stability, 
          help="Increasing stability will make the voice more consistent between re-generations, but it can also make it sounds a bit monotone. On longer text fragments we recommend lowering this value."
        )
        simarlity_boost = st.slider(
          "Clarity + Simalarity Enhancement",
          0.0,
          1.0,
          value=voice_settings.similarity_boost,
          help="High enhancement boosts overall voice clarity and target speaker similarity. Very high values can cause artifacts, so adjusting this setting to find the optimal value is encouraged."
        )
        style = st.slider(
          "Style Exaggeration",
          0.0,
          1.0,
          value=voice_settings.style,
          help="High values are recommended if the style of the speech should be exaggerated compared to the uploaded audio. Higher values can lead to more instability in the generated speech. Setting this to 0.0 will greatly increase generation speed and is the default setting."
        )
  
  if el_key:
    st.subheader("Text")
    sample_text = "Right now we just have a runnable sequence, but the chain still doesn't have any dynamic capability. There are multiple ways to do this. First, we'll look at the hard way which demonstrates the process, but keep in mind this can be simplified."
    text_to_generate = st.text_area("Text", sample_text, label_visibility="collapsed")
    generate_bnt = st.button("Generate Speech")
  else:
    st.warning("Enter your ElevenLabs API Key to continue.")
  
  if el_key and generate_bnt and text_to_generate:
    audio = el.generate(
      text=text_to_generate,
      model=model_id,
      voice = el.Voice(
        voice_id=el_voice_id,
        settings=el.VoiceSettings(stability=stability, similarity_boost=simarlity_boost, style=style)
      )
    )
    st.audio(audio)