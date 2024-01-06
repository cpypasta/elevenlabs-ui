import os, json, shutil
import streamlit as st
from dialogues import Character, Dialogue, load_dialogues_with_names, convert_dialogue_import_into_details
from dataclasses import dataclass
from utils import log
from elevenlabs import Voice
from el_audio import import_audio

@dataclass
class SavedDialogueData:
  saved_dialogues: dict
  selected_save_name: str
  save_dialogue_name: str
  save_dialogue: bool
  prepare_export: bool
  prepare_project: bool

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

def get_selected_plot(save_dialogue_data: SavedDialogueData) -> str:
  """Get the plot from the selected saved dialogue."""
  if save_dialogue_data.selected_save_name:
    return save_dialogue_data.saved_dialogues[save_dialogue_data.selected_save_name]["plot"]
  return None

def save_imported_dialogue(data: bytes, voices: list[Voice], file_id: str, import_name: str) -> None:
  uploaded_string = data.decode("utf-8")
  dialogue_details = convert_dialogue_import_into_details(uploaded_string, voices)
  if dialogue_details:
    data = json.dumps(dialogue_details, indent=2)
    import_name = import_name.replace(".txt", ".json")
    
    import_path = f"./session/{st.session_state.session_id}/saves/{import_name}"
    os.makedirs(os.path.dirname(import_path), exist_ok=True)                            
    with open(import_path, "w") as f:
      f.write(data)
      st.session_state["imported_file"] = file_id
      st.toast("Dialogue has been uploaded. You will have to click refresh to see it.", icon="👍")  
  else:
    st.toast("Invalid dialogue import. Please check your file for the correct format.", icon="👎")
  
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
    
    import_tab, export_tab = st.tabs(["Import", "Export"])
    with import_tab:
      uploaded_dialogue = st.file_uploader("Import JSON", type=["json", "txt", "zip"])
      if uploaded_dialogue is not None:
        not_previous_upload = "imported_file" in st.session_state and st.session_state["imported_file"] != uploaded_dialogue.file_id
        if "imported_file" not in st.session_state or not_previous_upload:
          bytes_data = uploaded_dialogue.getvalue()
          st.session_state["imported_file"] = uploaded_dialogue.file_id
          import_name = uploaded_dialogue.name.replace("_", " ")
          
          if uploaded_dialogue.type in ["text/plain", "application/json"]:    
            if uploaded_dialogue.type == "text/plain":
              save_imported_dialogue(bytes_data, voices, uploaded_dialogue.file_id, import_name)
            else:      
              import_path = f"./session/{st.session_state.session_id}/saves/{import_name}"
              os.makedirs(os.path.dirname(import_path), exist_ok=True)                            
              with open(import_path, "wb") as f:
                f.write(bytes_data)
                st.session_state["imported_file"] = uploaded_dialogue.file_id
                st.toast("Dialogue has been uploaded. You will have to click refresh to see it.", icon="👍")
          else:
            zip_name = import_name
            # save zip
            import_path = f"./session/{st.session_state.session_id}/import/{zip_name}"
            os.makedirs(os.path.dirname(import_path), exist_ok=True)
            with open(import_path, "wb") as f:
              f.write(bytes_data)
            # unzip file
            unzip_path = f"./session/{st.session_state.session_id}/import/contents"
            if os.path.exists(unzip_path):
              shutil.rmtree(unzip_path)
            os.makedirs(os.path.dirname(unzip_path), exist_ok=True)
            shutil.unpack_archive(import_path, unzip_path)
            # save dialogue
            with open(f"{unzip_path}/dialogue.txt", "rb") as f:
              bytes_data = f.read()
              save_imported_dialogue(bytes_data, voices, uploaded_dialogue.file_id, zip_name.replace(".zip", ".json"))
            # save audio files
            imported_files = import_audio()
            st.session_state["audio_files"] = imported_files
            st.toast("Audio files have been imported.", icon="👍")
            
    with export_tab:
      st.markdown("<p style='font-size:14px'>Export JSON</p>", unsafe_allow_html=True)
      col1, col2 = st.columns([1, 1])
      with col1:
        prepare_export=st.button("Prepare Dialogue", use_container_width=True, help="Prepare the dialogue for export")
        if prepare_export:
          st.session_state["export_type"] = "export"
      with col2:
        prepare_project=st.button("Prepare Project", use_container_width=True, help="Prepare the dialogue and audio for export")
        if prepare_project:
          st.session_state["export_type"] = "project"
      
      if "export_type" in st.session_state:
        if st.session_state["export_type"] == "export":
          download_dialogue_path = f"./session/{st.session_state.session_id}/export/dialogue.txt"
        else:
          download_dialogue_path = f"./session/{st.session_state.session_id}/project/project.zip"
        if os.path.exists(download_dialogue_path):
          download_dialogue_name = st.text_input(
            "download filename", 
            label_visibility="collapsed", 
            placeholder="Dialogue Name (file name)"
          )           
          if st.session_state["export_type"] == "export":
            file_name = f"{download_dialogue_name}.txt"
            mime = "plain/txt"
            read_type = "r"
          else:
            file_name = f"{download_dialogue_name}.zip" 
            mime = "application/zip"
            read_type = "rb"
          with open(download_dialogue_path, read_type) as f:
            dialogue_downloaded = st.download_button(
              label="Download", 
              data=f, 
              file_name=file_name, 
              mime=mime,
              use_container_width=True,
              disabled=not download_dialogue_name
            )
          if dialogue_downloaded:
            os.remove(download_dialogue_path)
            st.rerun()
        
  return SavedDialogueData(
    saved_dialogues, 
    selected_save_name, 
    save_dialogue_name, 
    save_dialog, 
    prepare_export, 
    prepare_project
  )

