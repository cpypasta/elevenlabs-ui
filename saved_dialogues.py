import os
import streamlit as st
from dialogues import Character, Dialogue, load_dialogues_with_names
from dataclasses import dataclass

@dataclass
class SavedDialogueData:
  saved_dialogues: dict
  selected_save_name: str
  save_dialogue_name: str
  save_dialogue: bool
  show_json: bool

def on_load_saved() -> None:
  """Clears the generated audio files and final audio from the session when a saved dialogue is loaded."""
  if "audio_files" in st.session_state:
    del st.session_state["audio_files"]
  if "final_audio" in st.session_state:
    del st.session_state["final_audio"]

def create_saved_dialogues():
  """Create the saved dialogues section."""
  with st.expander("Saved Dialogues"):
    col1, col2 = st.columns([7, 4])
    with col1:
      save_dialogue_name = st.text_input("filename", label_visibility="collapsed", placeholder="Dialogue Name for Saving")
    with col2:
      col21, col22 = st.columns([1, 1])
      with col21:
        save_dialog = st.button("Save Dialogue", use_container_width=True)
      with col22:
        show_json= st.button("Show JSON", use_container_width=True)
    
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
          saved_path = f"./saves/{selected_save_name}.json"
          if os.path.exists(saved_path):
            os.remove(saved_path)
            st.toast("Dialogue has been deleted. You will have to click refresh to see it.", icon="👍")
    
    uploaded_dialogue = st.file_uploader("Upload JSON Dialogue", type=["json"])
    if uploaded_dialogue is not None:
      bytes_data = uploaded_dialogue.getvalue()
      with open(f"./saves/{uploaded_dialogue.name}", "wb") as f:
        f.write(bytes_data)
        st.toast("Dialogue has been uploaded. You will have to click refresh to see it.", icon="👍")
        
  return SavedDialogueData(saved_dialogues, selected_save_name, save_dialogue_name, save_dialog, show_json)

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