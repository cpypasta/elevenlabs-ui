import os, shutil, glob
import streamlit as st
from diatribe.dialogues import convert_dialogue_import_into_data
from dataclasses import dataclass
from diatribe.el_audio import import_audio

@dataclass
class SavedDialogueData:
  prepare_project: bool

def convert_imported_dialogue(data: bytes) -> dict:
  uploaded_string = data.decode("utf-8")
  imported_data = convert_dialogue_import_into_data(uploaded_string)
  st.session_state["imported_characters"] = imported_data["characters"]
  st.session_state["imported_dialogue"] = imported_data["dialogue"]
  st.session_state["imported_plot"] = imported_data["plot"]  
  return imported_data
  
def unzip_package(data: bytes) -> str:
  # save zip
  import_path = f"./session/{st.session_state.session_id}/import/package.zip"
  os.makedirs(os.path.dirname(import_path), exist_ok=True)
  with open(import_path, "wb") as f:
    f.write(data)
  # unzip file
  unzip_path = f"./session/{st.session_state.session_id}/import/contents"
  if os.path.exists(unzip_path):
    shutil.rmtree(unzip_path)
  os.makedirs(os.path.dirname(unzip_path), exist_ok=True)
  shutil.unpack_archive(import_path, unzip_path) 
  return unzip_path 

def import_project(project_path: str) -> None:
  dialogue_path = f"{project_path}/dialogue.txt"  
  with open(dialogue_path, "rb") as f:
    dialogue = f.read()
  convert_imported_dialogue(dialogue)   
  imported_audio_files = import_audio(f"{project_path}/audio")
  st.session_state["audio_files"] = imported_audio_files
  st.toast("The project has been imported.", icon="👍") 
  dialogue_included = any(["dialogue.mp3" in f for f in imported_audio_files])
  if dialogue_included:
    st.session_state["final_audio"] = True
  elif "final_audio" in st.session_state: 
    del st.session_state["final_audio"]

@st.cache_data
def sample_project_names() -> list[str]:
  projects = glob.glob("./saves/*.zip")
  return [os.path.basename(p).replace("_", " ").replace(".zip", "") for p in projects]

def create_saved_dialogues():
  """Create the saved dialogues section."""
  with st.expander("Load & Downlaod Projects"):        
    st.markdown("Sample Projects")
    with st.form("Load Project", clear_on_submit=True, border=False):
      selected_save_name = st.selectbox(
        "Projects", 
        sample_project_names(), 
        index=None,  
        placeholder="Select a project",
        label_visibility="collapsed"
      )
      submit_sample_project = st.form_submit_button("Load", use_container_width=True)
      if submit_sample_project and selected_save_name:
        project_path = f"./saves/{selected_save_name.replace(' ', '_')}.zip"
        unzip_path = unzip_package(open(project_path, "rb").read())
        import_project(unzip_path)
    
    import_tab, export_tab = st.tabs(["Import", "Export"])
    with import_tab:
      with st.form("Import Project", clear_on_submit=True, border=False):
        imported_project = st.file_uploader("Project", type=["zip"])
        submit_upload_project = st.form_submit_button("Import", use_container_width=True)
        if imported_project and submit_upload_project:
          bytes_data = imported_project.getvalue()
          package_path = unzip_package(bytes_data)
          import_project(package_path)
            
    with export_tab:
      prepare_project=st.button("Prepare Download", use_container_width=True, help="Prepare the dialogue and audio for export")
      
      download_dialogue_path = f"./session/{st.session_state.session_id}/project/project.zip"
      if os.path.exists(download_dialogue_path):         
        with open(download_dialogue_path, "rb") as f:
          dialogue_downloaded = st.download_button(
            label="Download", 
            data=f, 
            file_name="project.zip", 
            mime="application/zip",
            use_container_width=True
          )
        if dialogue_downloaded:
          os.remove(download_dialogue_path)
        
  return SavedDialogueData(
    prepare_project
  )

