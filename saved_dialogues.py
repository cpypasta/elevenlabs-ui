import os, json
import streamlit as st
import pandas as pd
from dialogues import Character, Dialogue, load_dialogues_with_names, generate_dialogue_details
from dataclasses import dataclass
from utils import log
from elevenlabs import Voice

@dataclass
class SavedDialogueData:
  saved_dialogues: dict
  selected_save_name: str
  save_dialogue_name: str
  save_dialogue: bool
  prepare_json: bool

def on_load_saved() -> None:
  """Clears the generated audio files and final audio from the session when a saved dialogue is loaded."""
  if "audio_files" in st.session_state:
    del st.session_state["audio_files"]
  if "final_audio" in st.session_state:
    del st.session_state["final_audio"]
  if "generated_dialogue" in st.session_state:
    del st.session_state["generated_dialogue"]

def get_selected_characters(save_dialogue_data: SavedDialogueData) -> list[Character]:
  """Get the characters from the selected saved dialogue."""
  if save_dialogue_data.selected_save_name:
    return save_dialogue_data.saved_dialogues[save_dialogue_data.selected_save_name]["characters"]
  return []

def get_selected_dialogue(save_dialogue_data: SavedDialogueData) -> list[Dialogue]:
  """Get the dialogue from the selected saved dialogue."""
  if save_dialogue_data.selected_save_name:
    return save_dialogue_data.saved_dialogues[save_dialogue_data.selected_save_name]["dialogue"]
  return []

def convert_dialogue_import_into_details(data: str, voices: list[Voice]) -> dict:
  """Convert the imported dialogue into a common format."""
  characters_input, plot, dialogue_input = data.split("\n\n")
  characters = []
  dialogues = []  
  
  for character in characters_input.split("\n"):
    if character.startswith("#"):
      continue
    name, description = character.split(":")
    name, voice = name.split("|")
    characters.append({ "Name": name, "Voice": voice, "Description": description })
  
  for i, line in enumerate(dialogue_input.split("\n")):
    if line.startswith("#"):
      continue
    speaker, text = line.split(":")
    character = next((c for c in characters if c["Name"] == speaker), None)
    dialogues.append({ "Speaker": speaker, "Text": text })
    
  dialogue_details = generate_dialogue_details(
    pd.DataFrame(characters, columns=["Name", "Voice", "Description"]), 
    pd.DataFrame(dialogues, columns=["Speaker", "Text"]), 
    voices
  )
  return dialogue_details
  
def create_saved_dialogues(voices: list[Voice]):
  """Create the saved dialogues section."""
  with st.expander("Load & Save Dialogues"):
    
    st.markdown("Save")
    col1, col2 = st.columns([7, 3])
    with col1:
      save_dialogue_name = st.text_input("filename", label_visibility="collapsed", placeholder="Dialogue Name (file name)")
    with col2:
      save_dialog = st.button("Save Dialogue", use_container_width=True)
    
    st.markdown("Load")
    saved_names, saved_dialogues = load_dialogues_with_names()
    col1, col2 = st.columns([7, 4])
    with col1:
      selected_save_name = st.selectbox(
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
        st.button("Refresh", use_container_width=True) # forces rerun
      with col22:
        delete_dialogoue = st.button("Delete", use_container_width=True)
        if delete_dialogoue and selected_save_name:
          saved_path = f"./session/{st.session_state.session_id}/saves/{selected_save_name}.json"
          if os.path.exists(saved_path):
            os.remove(saved_path)
            st.toast("Dialogue has been deleted. You will have to click refresh to see it.", icon="👍")
    
    tab1, tab2 = st.tabs(["Import", "Export"])
    with tab1:
      uploaded_dialogue = st.file_uploader("Import JSON", type=["json", "txt"])
      if uploaded_dialogue is not None:
        not_previous_upload = "imported_json" in st.session_state and st.session_state["imported_json"] != uploaded_dialogue.file_id
        if "imported_json" not in st.session_state or not_previous_upload:
          bytes_data = uploaded_dialogue.getvalue()
          st.session_state["imported_json"] = uploaded_dialogue.file_id
          
          import_name = uploaded_dialogue.name.replace("_", " ")
          
          uploaded_string = bytes_data.decode("utf-8")
          if uploaded_string.startswith("# CHARACTERS"):
            dialogue_details = convert_dialogue_import_into_details(uploaded_string, voices)
            bytes_data = json.dumps(dialogue_details, indent=2).encode("utf-8")
            import_name = import_name.replace(".txt", ".json")
          
          import_path = f"./session/{st.session_state.session_id}/saves/{import_name}"
          os.makedirs(os.path.dirname(import_path), exist_ok=True)                            
          with open(import_path, "wb") as f:
            f.write(bytes_data)
            st.session_state["imported_json"] = uploaded_dialogue.file_id
            st.toast("Dialogue has been uploaded. You will have to click refresh to see it.", icon="👍")
    with tab2:
      st.markdown("<p style='font-size:14px'>Export JSON</p>", unsafe_allow_html=True)
      prepare_json=st.button("Prepare", use_container_width=True)
      
      if os.path.exists(f"./session/{st.session_state.session_id}/export/dialogue.json"):
          download_dialogue_name = st.text_input(
            "download filename", 
            label_visibility="collapsed", 
            placeholder="Dialogue Name (file name)"
          )            
          with open(f"./session/{st.session_state.session_id}/export/dialogue.json", "r") as f:
            dialogue_downloaded = st.download_button(
              label="Download", 
              data=f, 
              file_name=f"{download_dialogue_name}.json", 
              mime="application/json",
              use_container_width=True,
              disabled=not download_dialogue_name
            )
          if dialogue_downloaded:
            os.remove(f"./session/{st.session_state.session_id}/export/dialogue.json")
        
  return SavedDialogueData(saved_dialogues, selected_save_name, save_dialogue_name, save_dialog, prepare_json)

