import el_audio, os, uuid, shutil, time
import matplotlib.pyplot as plt
import streamlit as st
import pandas as pd
from pydub import AudioSegment
from dotenv import load_dotenv
from dialogues import Character, Dialogue, get_voice_id, save_dialogue, characters_match, export_dialogue
from sidebar import create_sidebar
from saved_dialogues import get_selected_characters, get_selected_dialogue, on_load_saved, create_saved_dialogues
from generate import create_dialogue_generation, create_continue_dialogue
from utils import log

load_dotenv()
plt.style.use('dark_background')

def show_final_audio() -> bool:
  return "final_audio" in st.session_state and st.session_state.final_audio
    

if __name__ == "__main__":
  st.set_page_config(layout="wide")
  
  if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())  
    log("session id: " + st.session_state.session_id)
  
  st.title("🎧 ElevenLabs Dialogue")
  
  sidebar = create_sidebar()
    
  if sidebar.el_key:
    saves = create_saved_dialogues(sidebar.voices)    
    
    st.header("Characters")
    st.markdown("This is where you setup and define what characters are in your dialogue along with what voice the character should use. You can use the `Voice Explorer` in the sidebar if you want to hear what a voice sounds like.")
    with st.expander("**WARNING**: changing characters can clear the dialogue"):
      st.info("Adding or removing characters and modifying names will clear or reset the dialogue. That being said, you can freely change the voices without affecting the dialogue.")
    
    if saves.selected_save_name:
      character_data = [c.to_dict() for c in get_selected_characters(saves)]
    else:
      character_data = []    
    character_table = st.data_editor(
      pd.DataFrame(character_data, columns=["Name", "Voice", "Description"]),
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
        description=row["Description"]
      )
      characters.append(c)
    character_names = [character.name for character in characters]
    
    st.header("Dialogue")
    st.markdown("This is where you write or generate the dialogue. The audio dialogue will use the model and voice settings defined in the sidebar. You can generate the audio multiple times, so click `Generate Audio Dialogue` as often as you would like.")
    
    generated_dialogue = create_dialogue_generation(sidebar, saves, characters)

    if "generated_dialogue" in st.session_state:
      characters_matched = characters_match(character_table, st.session_state["generated_dialogue"])
      if not characters_matched:
        log("characters do not match between generated dialogue and current characters")
        st.toast("It appears that the speakers in the dialogue do not match the characters you have defined.", icon="👎")
        del st.session_state["generated_dialogue"]
        
    if generated_dialogue is not None: 
      log("using created generated dialogue")     
      st.session_state["generated_dialogue"] = generated_dialogue
      dialogue_df = generated_dialogue
    elif "generated_dialogue" in st.session_state:
      dialogue_df = st.session_state["generated_dialogue"]
    elif saves.selected_save_name:
      log("using loaded dialogue") 
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
    if saves.save_dialogue and saves.save_dialogue_name:
      save_dialogue(character_table, dialogue_table, sidebar.voices, f"./session/{st.session_state.session_id}/saves/{saves.save_dialogue_name}.json")
      st.toast("Dialogue has been saved. You will have to click refresh to see it.", icon="👍")
    if saves.prepare_export:
      export_dialogue(character_table, dialogue_table, sidebar.voices, f"./session/{st.session_state.session_id}/export/dialogue.txt")
      st.rerun()
    
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
      
      # continue generated dialogue
      if sidebar.openai_api_key and not dialogue_table.empty:
        continue_btn = st.button("Cotinue Dialogue", use_container_width=True, help="This uses options set in `Dialogue Generation` to continue the dialogue.")
        if continue_btn:
          generated_dialogue = create_continue_dialogue(sidebar, characters, dialogue)     
          if generated_dialogue is not None: 
            st.session_state["generated_dialogue"] = generated_dialogue
            st.rerun()
      
      # generate audio dialogue files
      existing_audio_files = el_audio.get_generated_audio()
      show_existing_audio_files = len(existing_audio_files) > 0 and "imported_file" in st.session_state
      if show_existing_audio_files:
        col1, col2 = st.columns([1, 1])
        with col1:      
          generate_btn = st.button("Generate Audio Dialogue", use_container_width=True) 
        with col2:
          use_existing_btn = st.button(
            "Use Existing Audio", 
            use_container_width=True, 
            help="Use the existing audio files imported from a project.")
          if use_existing_btn:
            st.session_state["audio_files"] = existing_audio_files
      else:
        generate_btn = st.button("Generate Audio Dialogue", use_container_width=True)
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
        export_dialogue(character_table, dialogue_table, sidebar.voices, f"./session/{st.session_state.session_id}/export/dialogue.txt")
        el_audio.export_audio()
        project_path = f"./session/{st.session_state.session_id}/project"
        os.makedirs(project_path, exist_ok=True)
        shutil.make_archive(f"{project_path}/project", "zip", f"./session/{st.session_state.session_id}/export")
        st.rerun()
      
      if "audio_files" in st.session_state:   
        # display generated audio
        st.header("Audio Dialogue")
        st.markdown("The dialogue text has now been coverted into audio. You can listen to the audio by clicking the play button. If you want to regenerate the audio, you can click the `Generate Audio Dialogue` button above. If you are happy with the audio, you can join the audio files together by clicking the `Join Dialogue` button below. You can also click the `Redo` button to regenerate the audio for a specific line.")
        with st.expander("**WARNING**: deleting dialogue lines requires audio regeneration"):
          st.info("If you delete dialogue lines, you will have to regenerate the audio by clicking the `Generate Audio Dialogue` button above. Adding or modifying dialogue lines will not require regeneration of all lines, but you will likely need to click the `Redo` button for the affected lines.")
                    
        for i, line in enumerate(dialogue):
          st.markdown(f"{i + 1}. **{line.character.name}**: \"{line.text}\"")
          
          col1, col2 = st.columns([9, 1])
          with col1:     
            audio_file = f"./session/{st.session_state.session_id}/audio/line{line.line}.mp3"
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
            
          # AUDIO EDITING
          if audio_file_found and sidebar.enable_audio_editing:
            edit_audio_line_key = f"editing_audio_line_{line.line}"                                 
            
            if edit_audio_line_key not in st.session_state:
              st.session_state[edit_audio_line_key] = False
            edit_dialogue_line = st.button("Edit Audio", key=f"audio_edit_btn_{line.line}", use_container_width=True)
            if edit_dialogue_line:
              st.session_state[edit_audio_line_key] = not st.session_state[edit_audio_line_key] 
                
            should_show_audio_edit = st.session_state[edit_audio_line_key]
            if should_show_audio_edit:               
              basic_tab, soundboard_tab, special_tab,  = st.tabs(["Basic", "Soundboard", "Special Effect"])
              with basic_tab:
                st.markdown("### 🔊 Basic Settings")
                line_volume = st.slider(
                  "Adjust Speech Volume (dB)",
                  -25, 
                  25, 
                  0, 
                  1, 
                  key=f"volume_{line.line}"
                )
                
              with soundboard_tab:
                st.markdown("### 👂💫 Soundboard")
                compressor_tab, chorus_tab, distortion_tab, noise_gate_tab, reverb_tab = st.tabs([
                  "Compressor", 
                  "Chorus",
                  "Distortion",
                  "Noise Gate",
                  "Reverb"
                ])
                with compressor_tab:
                  st.markdown("A compressor controls the dynamic range of an audio signal. In other words, it reduces loud volumes by \"compressing\" the audio range.")
                  compressor_threshold_db = st.slider(
                    "Threshold (dB)",
                    -20.0, 0.0, 0.0, 0.5,
                    key=f"compressor_threshold_db_{line.line}",
                    help="The threshold above which compression is applied."
                  )
                  compressor_ratio = st.slider(
                    "Ratio",
                    1.0, 20.0, 2.0, 0.5,
                    key=f"compressor_ratio_{line.line}",
                    help="The amount of compression applied when the threshold is exceeded."
                  )          
                with chorus_tab:
                  st.markdown("A chorus effect makes a sound seem like it is being played by multiple sources at once which creates a \"shimmering\" sound.")
                  chorus_rate_hz = st.slider(
                    "Rate (Hz)",
                    0.0, 20.0, 0.0, 0.1,
                    key=f"chorus_rate_hz_{line.line}",
                    help="The low-frequency oscillator (LFO) in hertz (cycles per second)."
                  )                  
                  chorus_depth = st.slider(
                    "Depth",
                    0.25, 1.0, 0.25, 0.05,
                    key=f"chorus_depth_{line.line}",
                    help="Amount of modulation applied as set by the LFO."
                  )
                  chorus_centre_delay = st.slider(
                    "Delay (ms)",
                    0.0, 20.0, 7.0, 0.5,
                    key=f"chorus_delay_{line.line}",
                    help="The delay effect around the LFO."
                  )
                  chorus_feedback = st.slider(
                    "Feedback",
                    0.0, 1.0, 0.0, 0.1,
                    key=f"chorus_feedback_{line.line}",
                    help="The amount of output signal feed back into the input."
                  )                                                              
                with distortion_tab:
                  st.markdown("A distortion effect adds a \"gritty\" sound to the audio.")
                  distortion_db = st.slider(
                    "Drive (Db)",
                    0.0, 50.0, 0.0, 1.0,
                    key=f"distortion_db_{line.line}",
                    help="The amount of distortion."
                  )                    
                with noise_gate_tab:
                  st.markdown("A noise gate removes unwanted noise from the audio, often background noise. It is similar to the compressor, but a noise gate cuts off audio above a threshold instead of compressing it.")
                  noise_gate_threshold_db = st.slider(
                    "Threshold (dB)",
                    -20.0, 0.0, 0.0, 0.5,
                    key=f"noise_gate_threshold_db_{line.line}",
                    help="The threshold above which audio is cut off."
                  )                 
                  noise_gate_ratio = st.slider(
                    "Ratio",
                    0.0, 20.0, 2.0, 0.5,
                    key=f"noise_gate_ratio_{line.line}",
                    help="The amount that should be cut off when the threshold is exceeded."
                  )                        
                with reverb_tab:
                  st.markdown("A reverb effect simulates the sound of a room. It is often used to make a sound seem more natural.")
                  reverb_room_size = st.slider(
                    "Room Size",
                    0.0, 1.0, 0.0, 0.01,
                    key=f"reverb_room_size_{line.line}",
                    help="The perceived size of the room."
                  )   
                  reverb_damping = st.slider(
                    "Damping",
                    0.0, 1.0, 0.5, 0.1,
                    key=f"reverb_damping_{line.line}",
                    help="The amount of absorption of sound in the room."
                  )  
                  reverb_wet_level = st.slider(
                    "Wet Level",
                    0.0, 1.0, 0.33, 0.01,
                    key=f"reverb_wet_level_{line.line}",
                    help="The level of the reverberated signal."
                  )  
                  reverb_dry_level = st.slider(
                    "Dry Level",
                    0.0, 1.0, 0.4, 0.01,
                    key=f"reverb_dry_level_{line.line}",
                    help="The level of the original signal."
                  )                                                                        
                                
                
                soundboard = el_audio.Soundboard(
                  compressor_threshold_db, 
                  compressor_ratio,
                  chorus_rate_hz,
                  chorus_depth,
                  chorus_centre_delay,
                  chorus_feedback,
                  reverb_room_size,
                  reverb_damping,
                  reverb_wet_level,
                  reverb_dry_level,
                  distortion_db,
                  noise_gate_threshold_db,
                  noise_gate_ratio
                )
                              
              with special_tab:
                st.markdown("### 💥 Special Effect")
                effect_name = st.selectbox(
                  "Effects", 
                  el_audio.get_effect_names(), 
                  index=None, 
                  label_visibility="collapsed", 
                  placeholder="Select an effect",
                  key=f"effect_{line.line}"
                )
                if effect_name:
                  effect_path = el_audio.get_effect_path(effect_name)
                  st.audio(effect_path)                
                    
                  speech_duration = el_audio.get_audio_duration(audio_file)    
                  
                  effect_volume_tab, effect_timing_tab = st.tabs(["Volume", "Timing"])
                  with effect_volume_tab:            
                    effect_volume = st.slider(
                      "Adjust Effect Volume (dB)",
                      -25, 
                      25, 
                      0, 
                      1, 
                      key=f"effect_volume_{line.line}"
                    )    
                    effect_fade_out = st.slider(
                      "Effect Fade Out (milliseconds)",
                      0, 
                      5000, 
                      0, 
                      50, 
                      key=f"effect_fade_out_{line.line}",
                      help="Fades the effect out, which is particularly helpful if the effect is longer than the speech."
                    )                      
                  with effect_timing_tab:          
                    effect_start = st.slider(
                      "Effect Start Time (seconds)", 
                      0.0, 
                      speech_duration, 
                      0.0, 
                      0.1, 
                      key=f"effect_start_{line.line}",
                      help="When the effect should start playing. The effect will cut off if it exceeds the speech."
                    )              
                    effect_repeat = st.slider(
                      "Effect Repeat",
                      1,
                      10,
                      1,
                      1,
                      key=f"effect_repeat_{line.line}",
                      help="If you want the effect to repeat itself."
                    )
                else:
                  effect_path = None
                  effect_start = None
                  effect_volume = None
                  effect_repeat = None
                  effect_fade_out = None
                
              preview_line = st.button(
                "Preview", 
                key=f"preview_{line.line}",
                use_container_width=True
              )
              if preview_line:
                effect_audio, preview_audio = el_audio.preview_audio(
                  audio_file, 
                  line_volume, 
                  effect_path,
                  effect_start,
                  effect_volume,
                  effect_repeat,
                  effect_fade_out,
                  soundboard
                )                          
                
                if effect_name:
                  col1, col2 = st.columns([1, 1])
                  with col1:
                    st.markdown("<p style='font-size:14px'>Special Effect Preview</p>", unsafe_allow_html=True)
                    st.audio(effect_audio, format="audio/wav")
                  with col2:
                    st.markdown("<p style='font-size:14px'>Audio Preview</p>", unsafe_allow_html=True)              
                    st.audio(preview_audio, format="audio/wav")
                else:
                  st.audio(preview_audio, format="audio/wav")
                            
                org_audio_waveform, new_audio_waveform = st.columns([1, 1])
                with org_audio_waveform:
                  st.markdown("<p style='font-size:14px'>Original</p>", unsafe_allow_html=True)
                  y_max, plot = el_audio.generate_waveform_from_file(audio_file)
                  st.pyplot(plot)                  
                with new_audio_waveform:
                  st.markdown("<p style='font-size:14px'>Updated</p>", unsafe_allow_html=True)
                  _, plot = el_audio.generate_waveform_from_bytes(preview_audio, y_max)
                  st.pyplot(plot) 
                                  
              apply_edits = st.button("Apply", key=f"apply_{line.line}", use_container_width=True)
              if apply_edits:
                _, new_line_audio = el_audio.edit_audio(
                  audio_file, 
                  line_volume, 
                  effect_path,
                  effect_start,
                  effect_volume,
                  effect_repeat,
                  effect_fade_out,
                  soundboard                
                )
                new_line_audio.export(audio_file, format="mp3")
                log(f"saving audio {audio_file}")
                st.rerun()
        
          st.markdown("---")
          
      # join final audio
      if "audio_files" in st.session_state:
        join_dialogue = st.button("Join Dialogue", use_container_width=True)
        line_indices = [d.line for d in dialogue]
        if join_dialogue:          
          el_audio.join_audio(line_indices, sidebar.join_gap)
          st.session_state["final_audio"] = True
      
      # show final audio
      if show_final_audio():
        st.header("Final Dialogue")
        st.markdown("Here is the final dialogue with all the lines joined together. The gap between the lines is controlled by the `Gap Between Dialogue` setting in the sidebar under `Dialogue Options`. If you are unhappy about specific lines, then just click the `Redo` button on the line above and click `Join Dialogue` again.")        
                
        with st.expander("Background Audio"):
          background_names = el_audio.get_background_audio()
          st.markdown("You can add background audio to the final dialogue. If you want to remove the background audio, you will have to regenerate the final dialogue by clicking `Join Dialogue`.")
          background_name = st.selectbox(
            "Background Audio", 
            background_names, 
            index=None, 
            label_visibility="collapsed", 
            placeholder="Select a background audio"
          )
          if background_name:
            st.audio(el_audio.get_background_file_from_name(background_name))
          background_fade, background_volume = st.columns([1, 3])
          with background_fade:
            fade_in = st.toggle("Fade In", value=True)
            fade_out = st.toggle("Fade Out", value=True)
          with background_volume:
            lower_db = st.slider("Lower Background Volume (dB)", 0, 15, 0, 1, help="lowers the background audio by specified decibels")

          add_background_btn = st.button("Add Background", use_container_width=True)
          if add_background_btn and background_name:
            with st.spinner("Adding background audio..."):
              el_audio.apply_background_audio(background_name, fade_in, fade_out, lower_db)
              st.toast("Background audio has been added.", icon="👍")
        
        if "background_added" in st.session_state:
          log("using background audio")
          dialogue_path = f"./session/{st.session_state.session_id}/audio/dialogue_background.mp3"
        else:
          dialogue_path = f"./session/{st.session_state.session_id}/audio/dialogue.mp3"
                  
        st.audio(dialogue_path)
        _, fig = el_audio.generate_waveform_from_file(dialogue_path)       
        st.pyplot(fig)
        with open(dialogue_path, "rb") as mp3_audio:
          st.download_button(
            label="Download Final Dialogue",
            data=mp3_audio, 
            file_name="dialogue.mp3", 
            mime="audio/mp3",
            use_container_width=True
          )
    