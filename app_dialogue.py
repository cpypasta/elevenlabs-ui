import os, glob
import streamlit as st
import elevenlabs as el
import pandas as pd
from dotenv import load_dotenv
from pydub import AudioSegment as seg

load_dotenv()

class Character:
  def __init__(self, name: str, voice: str, voices: list[el.Voice]) -> None:
    self.name = name
    self.voice = voice
    try:
      voice_details = next(v for v in voices if v.name == voice)
      self.voice_id = voice_details.voice_id
    except Exception as e:
      print("unable to find voice", voice)
      pass
  
  def __str__(self):
    return f"{self.name} ({self.voice})"

class Dialogue:
  def __init__(self, character: Character, line: int, text: str):
    self.character = character
    self.line = line
    self.text = text
  
  def __str__(self):
    return f"[{self.line}] {self.character.name}: {self.text}"

@st.cache_data
def get_voices() -> list[el.Voice]:
  voices = list(el.voices())
  voices.sort(key=lambda x: x.name)
  return voices

@st.cache_data
def get_models() -> list[el.Model]:
  return list(el.Models.from_api())

def generate_audio(dialogue: Dialogue, model_id: str) -> bytes:
  audio = el.generate(
    text=dialogue.text,
    model=model_id,
    voice = el.Voice(
      voice_id=dialogue.character.voice_id
    )
  )  
  return audio

def show_final_audio() -> bool:
  return "final_audio" in st.session_state and st.session_state.final_audio


if __name__ == "__main__":
  st.title("🎧 ElevenLabs Dialogue")
  
  with st.sidebar:
    el_key = st.text_input("API Key", os.getenv("ELEVENLABS_API_KEY"), type="password")
    if el_key:
      el.set_api_key(el_key)          
      models = get_models()
      model_ids = [m.model_id for m in models]
      model_names = [m.name for m in models]
      model_name = st.selectbox("Model", model_names)
      if model_name:
        model_index = model_names.index(model_name)
        model_id = model_ids[model_index]
    
      el_voices = get_voices()
      el_voice_names = [voice.name for voice in el_voices]
      el_voice = st.selectbox("Voice", el_voice_names)
      if el_voice:
        el_voice_index = el_voice_names.index(el_voice)
        el_voice_details = el_voices[el_voice_index]
        el_voice_id = el_voice_details.voice_id
        
        # voice sample
        if el_voice_details.preview_url:
          st.audio(el_voice_details.preview_url, format="audio/mp3")
  
  st.header("Characters")
  st.markdown("This is where you setup and define what characters are in your story along with what voice the character should use. You can use the sidebar if you want to hear what a voice sounds like.")
  st.info("Adding or changing a name will clear the dialogue.")
  
  character_table = st.data_editor(
    pd.DataFrame([], columns=["Name", "Voice"]),
    use_container_width=True,
    hide_index=True, 
    num_rows="dynamic",
    column_config={
      "Name": st.column_config.TextColumn(
        "Name",
        required=True
      ),
      "Voice": st.column_config.SelectboxColumn(
        "Voice",
        options=el_voice_names,
        required=True
      )
    }    
  )
  
  if not character_table.empty:
    characters = [Character(row["Name"], row["Voice"], el_voices) for _, row in character_table.iterrows()]
    character_names = [character.name for character in characters]
    
    st.header("Dialogue")
    st.markdown("This is where you write the dialogue for your story. The dialog will use the model and voice settings defined in the sidebar. You can generate the audio multiple times, so feel free to generate the dialog to see the progress.")
    
    dialogue_table = st.data_editor(
      pd.DataFrame([], columns=["Speaker", "Text"]),
      use_container_width=True,
      num_rows="dynamic",
      column_config={
        "Speaker": st.column_config.SelectboxColumn(
          "Speaker",
          options=character_names,
          required=True,
          width="small"
        ),
        "Text": st.column_config.TextColumn(
          "Text",
          required=True,
          width="large"
        )
      }
    )
    
    if not dialogue_table.empty:
      dialogue = []
      for i, row in dialogue_table.iterrows():
        character_index = character_names.index(row["Speaker"])
        character = characters[character_index]
        dialogue.append(Dialogue(character, i, row["Text"]))
      
      generate_btn = st.button("Generate Dialogue")      
      if generate_btn:
        st.session_state["final_audio"] = False
        for file in glob.glob("./audio/*.mp3"):
          os.remove(file)
        audio_files = []
        for line in dialogue:
          audio = generate_audio(line, model_id)
          audio_file = f"./audio/line{line.line}.mp3"
          with open(audio_file, "wb") as f:
            f.write(audio)
          audio_files.append(audio_file) 
        st.session_state["audio_files"] = audio_files
      
      if "audio_files" in st.session_state:
        st.header("Audio Dialogue")
        for line in dialogue:
          st.markdown(f"{line.line + 1}. **{line.character.name}**: \"{line.text}\"")
          audio_file = f"./audio/line{line.line}.mp3"
          with open(audio_file, "rb") as audio:            
            st.audio(audio)        
      
      if "audio_files" in st.session_state:
        join_dialogue = st.button("Join Dialogue")
        
        if join_dialogue:          
          audio_files = st.session_state.audio_files
          segments = []
          for file in audio_files:
            segments.append(seg.from_mp3(file))
          final_audio = segments[0]
          for s in segments[1:]:
            final_audio += s
          final_audio.export("./audio/dialogue.mp3", format="mp3")
          st.session_state["final_audio"] = True
      
      if show_final_audio():
        st.header("Final Dialogue")
        st.audio("./audio/dialogue.mp3")
    