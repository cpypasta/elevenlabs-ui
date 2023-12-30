import el_audio
import matplotlib.pyplot as plt
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from dialogues import Character, Dialogue, get_voice_id, generate_dialogue_details, save_dialogue
from sidebar import create_sidebar
from saved_dialogues import create_saved_dialogues, get_selected_characters, get_selected_dialogue

load_dotenv()
plt.style.use('dark_background')

def show_final_audio() -> bool:
  return "final_audio" in st.session_state and st.session_state.final_audio
    

if __name__ == "__main__":
  st.set_page_config(layout="wide")
  st.title("🎧 ElevenLabs Dialogue")
  
  sidebar = create_sidebar()
  saves = create_saved_dialogues()

  st.header("Characters")
  st.markdown("This is where you setup and define what characters are in your dialogue along with what voice the character should use. You can use the sidebar if you want to hear what a voice sounds like.")
  st.info("Modifying names will clear the dialogue. You can freely change the voice however.")
    
  if sidebar.el_key:
    if saves.selected_save_name:
      character_data = [c.to_dict() for c in get_selected_characters(saves)]
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
          options=sidebar.voice_names,
          required=True
        )
      }    
    )
  else:
    character_table = pd.DataFrame()
    st.warning("Please enter an API key in the sidebar.")
  
  if not character_table.empty:
    characters = [Character(row["Name"], row["Voice"], get_voice_id(row["Voice"], sidebar.voices)) for _, row in character_table.iterrows()]
    character_names = [character.name for character in characters]
    
    st.header("Dialogue")
    st.markdown("This is where you write the dialogue. The audio dialogue will use the model and voice settings defined in the sidebar. You can generate the audio multiple times, so feel free to generate whenever you want to hear your progress.")
    
    if saves.selected_save_name:
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
        dialogue_data = [d.to_dict(without_line=True) for d in get_selected_dialogue(saves)]
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
    if saves.selected_save_name and saves.save_dialogue_name:
      if character_table.empty or dialogue_table.empty:
        st.toast("Please enter characters and dialogue before saving.", icon="🚨")
      else:
        save_dialogue(character_table, dialogue_table, sidebar.voices, saves.save_dialogue_name)
        st.toast("Dialogue has been saved. You will have to click refresh to see it.", icon="👍")
    if saves.show_json and not character_table.empty and not dialogue_table.empty:
      with st.expander("JSON", expanded=True):
        st.toast("The JSON is shown below. Please scroll down to see it.", icon="👍")
        with open(f"./saves/{saves.selected_save_name}.json", "r") as f:
          st.download_button(label="Download", data=f, file_name=f"{saves.selected_save_name}.json", mime="application/json")
        st.json(generate_dialogue_details(character_table, dialogue_table, sidebar.voices))
    
    if not dialogue_table.empty:
      dialogue: list[Dialogue] = []
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
        el_audio.clear_audio_files()
        audio_files: list[str] = []
        progress_text = "Generating audio..."
        if "audio_process_error" in st.session_state:
          del st.session_state["audio_process_error"]
        generate_audio_bar = st.progress(0, text=progress_text)
        for i, line in enumerate(dialogue):
          try:
            audio_file = el_audio.generate_and_save(line.text, line.character.voice_id, line.line, sidebar) 
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
            el_audio.generate_and_save(line, sidebar) 
                    
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
          el_audio.join_audio(audio_files, sidebar.join_gap)
          st.session_state["final_audio"] = True
      
      # show final audio
      if show_final_audio():
        dialogue_path = "./audio/dialogue.mp3"
        st.header("Final Dialogue")
        st.audio(dialogue_path)
        fig = el_audio.generate_waveform(dialogue_path)       
        st.pyplot(fig)
    