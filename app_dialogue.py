import os, glob, json, re
import matplotlib.pyplot as plt
import streamlit as st
import elevenlabs as el
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from pydub import AudioSegment as seg
from dialogues import Character, Dialogue, load_saved_dialogues

load_dotenv()
plt.style.use('dark_background')

@st.cache_data
def get_voices() -> list[el.Voice]:
  voices = list(el.voices())
  voices.sort(key=lambda x: x.name)
  return voices

@st.cache_data
def get_models() -> list[el.Model]:
  return list(el.Models.from_api())

def extract_name(s: str) -> str:
  match = re.match(r"(.*?)( \(cloned\))?$", s)
  if match:
    return match.group(1)
  return s  

def get_voice_id(voice_name: str, voices: list[el.Voice]) -> str:
  voice_name = extract_name(voice_name)
  voice_index = next((i for i, v in enumerate(voices) if v.name == voice_name), None)
  if voice_index:
    return voices[voice_index].voice_id
  else:
    return ""

def generate_audio(
  dialogue: Dialogue, 
  model_id: str,
  stability: float, 
  simarlity_boost: float, 
  style: float  
) -> bytes:
  audio = el.generate(
    text=dialogue.text,
    model=model_id,
    voice = el.Voice(
      voice_id=dialogue.character.voice_id,
      settings=el.VoiceSettings(
        stability=stability,
        similarity_boost=simarlity_boost,
        style=style
      )
    )
  )  
  return audio

def generate_waveform() -> plt.Figure:
  audio = seg.from_mp3("./audio/dialogue.mp3")
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

def show_final_audio() -> bool:
  return "final_audio" in st.session_state and st.session_state.final_audio

def generate_and_save_audio(
  line: Dialogue, 
  model_id: str, 
  stability: float, 
  simarlity_boost: float, 
  style: float
) -> str:
  audio = generate_audio(line, model_id, stability, simarlity_boost, style)
  audio_file = f"./audio/line{line.line}.mp3"
  with open(audio_file, "wb") as f:
    f.write(audio)  
  return audio_file

def debug_df(df: pd.DataFrame) -> None:
  if df.empty:
    print("dataframe is empty")
  else:
    print(df)

def on_load_saved() -> None:
  if "audio_files" in st.session_state:
    del st.session_state["audio_files"]
  if "final_audio" in st.session_state:
    del st.session_state["final_audio"]
    
def load_dialogues_with_names() -> (list[str], dict):
  saved_dialogues = load_saved_dialogues()
  saved_names = list(saved_dialogues.keys())  
  return saved_names, saved_dialogues

def generate_dialogue_details(character_table: pd.DataFrame, dialogue_table: pd.DataFrame, voices: list[el.Voice]) -> dict:
  characters = []
  for i, c in character_table.iterrows():
    characters.append(Character(c["Name"], c["Voice"], get_voice_id(c["Voice"], voices)))
  dialogue = []
  for i, d in dialogue_table.iterrows():
    character = next((c for c in characters if c.name == d["Speaker"]), None)
    dialogue.append(Dialogue(character, i, d["Text"]).to_dict()) 
  dialogue_details = {
    "characters": [c.to_dict() for c in characters],
    "dialogue": dialogue
  }  
  return dialogue_details  

if __name__ == "__main__":
  st.set_page_config(layout="wide")
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
      el_voice_names = [f"{voice.name}{' (cloned)' if voice.category == 'cloned' else ''}" for voice in el_voices]
      el_voice = st.selectbox("Voice", el_voice_names)
      if el_voice:
        el_voice_index = el_voice_names.index(el_voice)
        el_voice_details = el_voices[el_voice_index]
        el_voice_id = el_voice_details.voice_id
        
        # voice sample        
        if el_voice_details.preview_url:
          st.audio(el_voice_details.preview_url, format="audio/mp3")
          
      with st.expander("Voice Options"):                     
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
        
      with st.expander("Debug"):
        st.markdown(f"_Model ID: {model_id}_")
        st.markdown(f"_Voice ID: {el_voice_id}_") 
  
  with st.expander("Saved Dialogues"):
    col1, col2 = st.columns([7, 4])
    with col1:
      save_filename = st.text_input("filename", label_visibility="collapsed", placeholder="Dialogue Name for Saving")
    with col2:
      col21, col22 = st.columns([1, 1])
      with col21:
        save_dialog = st.button("Save Dialogue", use_container_width=True)
      with col22:
        show_json= st.button("Show JSON", use_container_width=True)
    
    saved_names, saved_dialogues = load_dialogues_with_names()
    col1, col2 = st.columns([7, 4])
    with col1:
      saved_dialogue = st.selectbox(
        "Loads", 
        saved_names, 
        index=None, 
        on_change=on_load_saved, 
        placeholder="Select a dialogue",
        label_visibility="collapsed"
      )
    with col2:
      col21, col22 = st.columns([1, 1])
      with col21:
        refresh_dialogues = st.button("Refresh", use_container_width=True)
        if refresh_dialogues:
          pass # forces rerun
      with col22:
        delete_dialogoue = st.button("Delete", use_container_width=True)
        if delete_dialogoue and saved_dialogue:
          saved_path = f"./saves/{saved_dialogue}.json"
          if os.path.exists(saved_path):
            os.remove(saved_path)
            st.toast("Dialogue has been deleted. You will have to click refresh to see it.", icon="👍")
    
    uploaded_dialogue = st.file_uploader("Upload JSON Dialogue", type=["json"])
    if uploaded_dialogue is not None:
      bytes_data = uploaded_dialogue.getvalue()
      with open(f"./saves/{uploaded_dialogue.name}", "wb") as f:
        f.write(bytes_data)
        st.toast("Dialogue has been uploaded. You will have to click refresh to see it.", icon="👍")
  
  st.header("Characters")
  st.markdown("This is where you setup and define what characters are in your dialogue along with what voice the character should use. You can use the sidebar if you want to hear what a voice sounds like.")
  st.info("Modifying names will clear the dialogue. You can freely change the voice however.")
    
  if el_key:
    if saved_dialogue:
      character_data = [c.to_dict() for c in saved_dialogues[saved_dialogue]["characters"]]
    else:
      character_data = []    
    character_table = st.data_editor(
      pd.DataFrame(character_data, columns=["Name", "Voice"]),
      use_container_width=True,
        hide_index=True,
      num_rows="dynamic",
      key="character_table",
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
  else:
    character_table = pd.DataFrame()
    st.warning("Please enter an API key in the sidebar.")
  
  if not character_table.empty:
    characters = [Character(row["Name"], row["Voice"], get_voice_id(row["Voice"], el_voices)) for _, row in character_table.iterrows()]
    character_names = [character.name for character in characters]
    
    st.header("Dialogue")
    st.markdown("This is where you write the dialogue. The audio dialogue will use the model and voice settings defined in the sidebar. You can generate the audio multiple times, so feel free to generate whenever you want to hear your progress.")
    
    if saved_dialogue:
      characters_changes = st.session_state["character_table"]
      edited_characters = False
      if "edited_rows" in characters_changes:
        edited_rows = characters_changes["edited_rows"]
        edited_cnt = 0
        for r_key in edited_rows.keys():
          change = edited_rows[r_key]
          if "Name" in change.keys():
            edited_characters = True
            break
      removed_characters = "deleted_rows" in characters_changes and len(characters_changes["deleted_rows"]) > 0
      if edited_characters or removed_characters:
        dialogue_df = pd.DataFrame([], columns=["Speaker", "Text"])
      else:
        dialogue_data = [d.to_dict(without_line=True) for d in saved_dialogues[saved_dialogue]["dialogue"]]
        dialogue_df = pd.DataFrame(dialogue_data, columns=["Speaker", "Text"])
    else:
      dialogue_df = pd.DataFrame([], columns=["Speaker", "Text"])
    
    dialogue_table = st.data_editor(
      dialogue_df,
      use_container_width=True,
      num_rows="dynamic",
      hide_index=True,
      key="dialogue_table",
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
    
    # save dialogue to file
    if save_dialog and save_filename:
      if character_table.empty or dialogue_table.empty:
        st.toast("Please enter characters and dialogue before saving.", icon="🚨")
      else:
        dialogue_details = generate_dialogue_details(character_table, dialogue_table, el_voices)      
        with open(f"./saves/{save_filename}.json", "w") as f:
          json.dump(dialogue_details, f, indent=2)
        st.toast("Dialogue has been saved. You will have to click refresh to see it.", icon="👍")
    if show_json and not character_table.empty and not dialogue_table.empty:
      with st.expander("JSON", expanded=True):
        st.toast("The JSON is shown below. Please scroll down to see it.", icon="👍")
        with open(f"./saves/{saved_dialogue}.json", "r") as f:
          st.download_button(label="Download", data=f, file_name=f"{saved_dialogue}.json", mime="application/json")
        st.json(generate_dialogue_details(character_table, dialogue_table, el_voices))
    
    if not dialogue_table.empty:
      dialogue = []
      for i, row in dialogue_table.iterrows():
        try:
          character_index = character_names.index(row["Speaker"])
          character = characters[character_index]
          dialogue.append(Dialogue(character, i, row["Text"]))
        except:
          print(f"Error: {row['Speaker']} is not a valid character.")
          pass        
      
      # generate audio dialogue
      generate_btn = st.button("Generate Audio Dialogue")      
      if generate_btn:
        st.session_state["final_audio"] = False
        for file in glob.glob("./audio/*.mp3"):
          os.remove(file)
        if not os.path.isdir("./audio"):
          os.mkdir("./audio")
        audio_files = []
        progress_text = "Generating audio..."
        if "audio_process_error" in st.session_state:
          del st.session_state["audio_process_error"]
        generate_audio_bar = st.progress(0, text=progress_text)
        for i, line in enumerate(dialogue):
          try:
            audio_file = generate_and_save_audio(line, model_id, stability, simarlity_boost, style) 
            audio_files.append(audio_file)
          except Exception as e:
            print(e)
            st.session_state["audio_process_error"] = f"{dialogue.character.name} with the voice {dialogue.character.voice} (voice_id: {dialogue.character.voice_id})"
            break
          generate_audio_bar.progress(round((i+1) / len(dialogue), 2), text=progress_text)          
        generate_audio_bar.empty()
        
        if "audio_process_error" in st.session_state:
          st.error(f"""An error occured while generating the audio. Please check your API key.
          Error occurred while processing: {st.session_state.audio_process_error}
          """)
        else:
          st.session_state["audio_files"] = audio_files
      
      if "audio_files" in st.session_state:        
        # display generated audio
        st.header("Audio Dialogue")
        # check to see if one of the audio files needs to be updated
        redos = list(filter(lambda x: x.startswith("redo_"), list(st.session_state.keys())))
        redo_key = next((r for r in redos if st.session_state[r]), None)
        if redo_key:
          _, index = redo_key.split("_")
          line = dialogue[int(index)]
          with st.spinner("Generating audio..."):
            generate_and_save_audio(line, model_id, stability, simarlity_boost, style)
                    
        for line in dialogue:
          st.markdown(f"{line.line + 1}. **{line.character.name}**: \"{line.text}\"")
          audio_file = f"./audio/line{line.line}.mp3"
          with open(audio_file, "rb") as audio: 
            col1, col2 = st.columns([9, 1])
            with col1:           
              st.audio(audio)        
            with col2:
              redo_key = f"redo_{line.line}"
              st.button("Redo", key=redo_key)
      
      # join final audio
      if "audio_files" in st.session_state:
        join_dialogue = st.button("Join Dialogue")
        
        if join_dialogue:          
          audio_files = st.session_state.audio_files
          gap = seg.silent(join_gap)
          segments = []
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
          st.session_state["final_audio"] = True
      
      # show final audio
      if show_final_audio():
        st.header("Final Dialogue")
        st.audio("./audio/dialogue.mp3")
        fig = generate_waveform()       
        st.pyplot(fig)
    