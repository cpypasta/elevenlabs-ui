import os, uuid, shutil
import matplotlib.pyplot as plt
import streamlit as st
import pandas as pd
import diatribe.el_audio as el_audio
import diatribe.saved_dialogues as saved_dialogues
from dotenv import load_dotenv
from streamlit_extras.stylable_container import stylable_container
from diatribe.dialogues import Character, Dialogue, get_voice_id, export_dialogue, get_lines
from diatribe.sidebar import create_sidebar
from diatribe.saved_dialogues import create_saved_dialogues
from diatribe.generate import create_dialogue_generation, create_continue_dialogue
from diatribe.utils import log
from diatribe.audio_edit import create_edit_dialogue_line, create_edit_diatribe

load_dotenv()
plt.style.use('dark_background')

button_style = """
  button {
    background-color: #50a35f;
    border-color: #50a35f;
  }
"""

def show_final_audio() -> bool:
  return "final_audio" in st.session_state and st.session_state.final_audio
    

if __name__ == "__main__":
  st.set_page_config(layout="wide", page_title="Diatribe", page_icon="🎧")
  
  if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())  
    log("session id: " + st.session_state.session_id)
  
  st.title("🎧 Diatribe")
  
  sidebar = create_sidebar()
    
  if sidebar.el_key:
    saves = create_saved_dialogues()    
    
    st.header("Characters")
    if sidebar.enable_instructions:
      st.markdown("This is where you setup and define what characters are in your dialogue along with what voice the character should use. You can use the `Voice Explorer` in the sidebar if you want to hear what a voice sounds like.")
      with st.expander("**WARNING**: changing characters can clear the dialogue"):
        st.info("Adding characters, removing characters, and modifying character names will clear or reset the dialogue. That being said, you can freely change the voices, groups, and description without affecting the dialogue.")      
    
    with st.expander("Import Characters & Dialogue"):
      uploaded_dialogue = None
      with st.form("import dialogue", clear_on_submit=True, border=False):
        dialogue_upload = st.file_uploader(
          "Dialogue", type=["txt"]
        )         
        submit_dialogue_upload = st.form_submit_button("Import", use_container_width=True)
        if submit_dialogue_upload and dialogue_upload:
          uploaded_dialogue = dialogue_upload.getvalue()
          saved_dialogues.convert_imported_dialogue(uploaded_dialogue)
          if "audio_files" in st.session_state:
            del st.session_state["audio_files"]
          if "generated_dialogue" in st.session_state:
            del st.session_state["generated_dialogue"]
          if "final_audio" in st.session_state:
            del st.session_state["final_audio"]
          st.toast("The dialogue has been imported.", icon="👍")
    
    if "imported_characters" in st.session_state:
      character_data = st.session_state["imported_characters"]     
    else:
      character_data = []    
            
    character_table = st.data_editor(
      pd.DataFrame(character_data, columns=["Name", "Voice", "Group", "Description"]),
      use_container_width=True,
        hide_index=True,
      num_rows="dynamic",
      key="character_table",
      column_config={
        "Name": st.column_config.TextColumn(
          "Name",
          required=True,
          width="small"
        ),
        "Voice": st.column_config.SelectboxColumn(
          "Voice",
          options=sidebar.voice_names,
          required=True,
          width="small"
        ),
        "Group": st.column_config.NumberColumn(
          "Group",
          required=False,
          width="small"
        ),
        "Description": st.column_config.TextColumn(
          "Description",
          required=False,
          width="large"
        )
      }    
    )
  else:
    character_table = pd.DataFrame()
    st.warning("Please enter an API key in the sidebar.")
  
  characters_available = not character_table.empty
  if characters_available:
    characters: list[Character] = []
    for _, row in character_table.iterrows():
      c = Character(
        row["Name"], 
        row["Voice"], 
        get_voice_id(row["Voice"], sidebar.voices),
        description=row["Description"],
        group=int(row["Group"]) if row["Group"] is not None else 1
      )
      characters.append(c)
    character_names = [character.name for character in characters]
    
    st.header("Dialogue")
    if sidebar.enable_instructions:
      st.markdown("This is where you write or generate the dialogue. The audio dialogue will use the model and voice settings defined in the sidebar. You can generate the audio multiple times, so click `Generate Audio Dialogue` as often as you would like.")    
      
    generated_dialogue = create_dialogue_generation(sidebar, saves, characters)
        
    if generated_dialogue is not None: 
      st.session_state["generated_dialogue"] = generated_dialogue
      dialogue_df = generated_dialogue
    elif "generated_dialogue" in st.session_state:
      dialogue_df = st.session_state["generated_dialogue"]
    elif "imported_dialogue" in st.session_state:
      dialogue_df = st.session_state["imported_dialogue"]
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
    
    # extract Dialogues from the dialogue table
    if not dialogue_table.empty:
      dialogue: list[Dialogue] = []
      for i, row in dialogue_table.iterrows():
        try:
          character_index = character_names.index(row["Speaker"])
          character = characters[character_index]
          dialogue.append(Dialogue(character, i+1, row["Text"]))
        except:
          print(f"Error: {row['Speaker']} is not a valid character.")
          pass        
      dialogue.sort(key=lambda x: x.line)
      
      with st.expander("Export Characters & Dialogue"):
        prepare_download_dialogue = st.button("Prepare Download", help="This will prepare the dialogue for download.", use_container_width=True)
        if prepare_download_dialogue:
          export_dialogue_path = export_dialogue(character_table, dialogue_table, sidebar.voices)
          with open(export_dialogue_path, "r") as f:
            st.download_button(
              "Download",
              data=f,
              file_name=os.path.basename(export_dialogue_path),
              mime="text/plain",
              use_container_width=True
            )        
      
      # continue generated dialogue
      if sidebar.openai_api_key and not dialogue_table.empty:
        continue_btn = st.button("Continue Dialogue", use_container_width=True, help="This uses options set in `Dialogue Generation` to continue the dialogue.")
        if continue_btn:
          generated_dialogue = create_continue_dialogue(sidebar, characters, dialogue)     
          if generated_dialogue is not None: 
            st.session_state["generated_dialogue"] = generated_dialogue
            st.rerun()
      
      # generate audio dialogue files
      st.markdown("---")
      existing_audio_files = el_audio.get_generated_audio()
    
      with stylable_container(
        key="generate_dialogue_button_with_existing",
        css_styles=button_style
      ):
        generate_btn = st.button("Generate Audio Dialogue", use_container_width=True, type="primary") 

      if generate_btn:
        st.session_state["final_audio"] = False
        el_audio.clear_audio_files()
        audio_files: list[str] = []
        progress_text = "Generating audio..."
        if "audio_process_error" in st.session_state:
          del st.session_state["audio_process_error"]
        generate_audio_bar = st.progress(0, text=progress_text)
        for i, line in enumerate(dialogue):
          if line.character.voice_id is None:
            st.toast(f"Error: voice ID not found for `{line.character.voice}`.", icon="👎")
            break
          try:
            audio_file = el_audio.generate_and_save(line.text, line.character.voice_id, line.line, sidebar) 
            audio_files.append(audio_file)
          except Exception as e:
            print(e)
            st.session_state["audio_process_error"] = f"{line.character.name} with the voice {line.character.voice} (voice_id: {line.character.voice_id})"
            break
          generate_audio_bar.progress(round((i+1) / len(dialogue), 2), text=progress_text)          
        generate_audio_bar.empty()
        
        if "audio_process_error" in st.session_state:
          st.error(f"""An error occured while generating the audio. Please check your API key.
          Error occurred while processing: {st.session_state.audio_process_error}
          """)
          if "audio_files" in st.session_state:
            del st.session_state["audio_files"]
        else:
          st.session_state["audio_files"] = audio_files
      
      if saves.prepare_project:
        export_dialogue(character_table, dialogue_table, sidebar.voices)
        export_path = el_audio.export_audio(get_lines(dialogue))
        project_path = f"./session/{st.session_state.session_id}/project"
        os.makedirs(project_path, exist_ok=True)
        shutil.make_archive(f"{project_path}/project", "zip", export_path)
        st.rerun()
      
      if "audio_files" in st.session_state:   
        # display generated audio
        st.header("Audio Dialogue")
        if sidebar.enable_instructions:
          st.markdown("The dialogue text has now been coverted into audio. You can listen to the audio by clicking the play button. If you want to regenerate the audio, you can click the `Generate Audio Dialogue` button above. If you are happy with the audio, you can join the audio files together by clicking the `Join Dialogue` button below. You can also click the `Redo` button to regenerate the audio for a specific line.")
          with st.expander("**WARNING**: deleting dialogue lines requires audio regeneration"):
            st.info("If you delete dialogue lines, you will have to regenerate the audio by clicking the `Generate Audio Dialogue` button above. Adding or modifying dialogue lines will not require regeneration of all lines, but you will likely need to click the `Redo` button for the affected lines.")                 
        
        for i, line in enumerate(dialogue):
          st.markdown(f"`{i + 1}.` **:green[{line.character.name}]**: \"{line.text}\"")
          
          col1, col2 = st.columns([9, 1])
          with col1:     
            audio_file = f"./session/{st.session_state.session_id}/audio/line{line.line}.wav"
            if os.path.exists(audio_file):     
              with open(audio_file, "rb") as audio:  
                st.audio(audio)
                pass
              audio_file_found = True
            else:
              st.markdown("Audio file not found. Please click the `Redo` button.")  
              audio_file_found = False
          with col2:
            redo_key = f"redo_{line.line}"
            redo_btn = st.button("Redo", key=redo_key)
          if redo_btn:
            with st.spinner("Generating audio..."):
              el_audio.generate_and_save(line.text, line.character.voice_id, line.line, sidebar)
            st.rerun()
            
          # dialogue audio editing
          if audio_file_found and sidebar.enable_audio_editing:
            create_edit_dialogue_line(line, audio_file)    
      
      # join final audio
      if "audio_files" in st.session_state:
        st.markdown("---")
        with stylable_container(
          key="join_dialogue_button",
          css_styles=button_style
        ):        
          join_dialogue = st.button("Join Dialogue", use_container_width=True, type="primary")
        line_indices = [d.line for d in dialogue]
        if join_dialogue:          
          el_audio.join_audio(
            line_indices
          )
          st.session_state["final_audio"] = True
      
      # show final audio
      if show_final_audio():
        st.header("Audio Diatribe")
        if sidebar.enable_instructions:
          st.markdown("Here is the final dialogue with all the lines joined together. If you are unhappy about specific lines, then just click the `Redo` button on the line above and click `Join Dialogue` again.")        
        
        if sidebar.enable_audio_editing:
          create_edit_diatribe(sidebar, characters, dialogue)
        
        dialogue_path = f"./session/{st.session_state.session_id}/final/audio/dialogue.mp3"
        st.audio(dialogue_path)
        _, fig = el_audio.generate_waveform_from_file(dialogue_path)       
        st.pyplot(fig)
          
        with open(dialogue_path, "rb") as mp3_audio:
          with stylable_container(
            key="download_dialogue_button",
            css_styles=button_style
          ):
            st.download_button(
              label="Download Final Dialogue",
              data=mp3_audio, 
              file_name="dialogue.mp3", 
              mime="audio/mp3",
              use_container_width=True,
              type="primary"
            )
    