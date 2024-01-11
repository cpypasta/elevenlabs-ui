import streamlit as st
import diatribe.el_audio as el_audio
from diatribe.dialogues import Dialogue, Character
from diatribe.sidebar import SidebarData
from diatribe.utils import log
from diatribe.edits import *

def create_compressor(key: str) -> CompressorEdit:
    st.markdown("A compressor controls the dynamic range of an audio signal. In other words, it reduces loud volumes by \"compressing\" the audio range.")
    compressor_threshold_db = st.slider(
        "Threshold (dB)",
        -20.0, 0.0, 0.0, 0.5,
        key=f"compressor_threshold_db_{key}",
        help="The threshold above which compression is applied."
    )
    compressor_ratio = st.slider(
        "Ratio",
        1.0, 20.0, 2.0, 0.5,
        key=f"compressor_ratio_{key}",
        help="The amount of compression applied when the threshold is exceeded."
    )         
    return CompressorEdit(
        compressor_threshold_db,
        compressor_ratio
    )

def create_chorus(key: str) -> ChorusEdit:
    st.markdown("A chorus effect makes a sound seem like it is being played by multiple sources at once which creates a \"shimmering\" sound.")
    chorus_rate_hz = st.slider(
        "Rate (Hz)",
        0.0, 20.0, 0.0, 0.1,
        key=f"chorus_rate_hz_{key}",
        help="The low-frequency oscillator (LFO) in hertz (cycles per second)."
    )                  
    chorus_depth = st.slider(
        "Depth",
        0.25, 1.0, 0.25, 0.05,
        key=f"chorus_depth_{key}",
        help="Amount of modulation applied as set by the LFO."
    )
    chorus_centre_delay = st.slider(
        "Delay (ms)",
        0.0, 20.0, 7.0, 0.5,
        key=f"chorus_delay_{key}",
        help="The delay effect around the LFO."
    )
    chorus_feedback = st.slider(
        "Feedback",
        0.0, 1.0, 0.0, 0.1,
        key=f"chorus_feedback_{key}",
        help="The amount of output signal feed back into the input."
    )     
    return ChorusEdit(
        chorus_rate_hz,
        chorus_depth,
        chorus_centre_delay,
        chorus_feedback
    )

def create_distortion(key: str) -> DistortionEdit:
    st.markdown("A distortion effect adds a \"gritty\" sound to the audio.")
    distortion_db = st.slider(
        "Drive (Db)",
        0.0, 50.0, 0.0, 0.5,
        key=f"distortion_db_{key}",
        help="The amount of distortion."
    )         
    return DistortionEdit(distortion_db)

def create_limiter(key: str) -> LimiterEdit:
    st.markdown("A limiter is similar to a compressor, but it is a more extreme form of compression. It will compress the dynamic range by making the quiet parts louder and and the loud parts quieter. This will often be used in combination with the compressor.")
    limiter_threshold_db = st.slider(
        "Threshold (dB)",
        -10.0, 0.0, 0.0, 0.5,
        key=f"limiter_threshold_db_{key}",
        help="The threshold above which the limiter is applied."
    )    
    return LimiterEdit(limiter_threshold_db)

def create_noise_gate(key: str) -> NoiseGateEdit:
    st.markdown("A noise gate removes unwanted noise from the audio, often background noise. It is similar to the compressor, but a noise gate cuts off audio above a threshold instead of compressing it.")
    noise_gate_threshold_db = st.slider(
        "Threshold (dB)",
        -20.0, 0.0, 0.0, 0.5,
        key=f"noise_gate_threshold_db_{key}",
        help="The threshold above which audio is cut off."
    )                 
    noise_gate_ratio = st.slider(
        "Ratio",
        0.0, 20.0, 2.0, 0.5,
        key=f"noise_gate_ratio_{key}",
        help="The amount that should be cut off when the threshold is exceeded."
    )         
    return NoiseGateEdit(
        noise_gate_threshold_db,
        noise_gate_ratio
    )

def create_reverb(key: str) -> ReverbEdit:
    st.markdown("A reverb effect simulates the sound of a room. It is often used to make a sound seem more natural.")
    reverb_room_size = st.slider(
        "Room Size",
        0.0, 1.0, 0.0, 0.01,
        key=f"reverb_room_size_{key}",
        help="The perceived size of the room."
    )   
    reverb_damping = st.slider(
        "Damping",
        0.0, 1.0, 0.5, 0.1,
        key=f"reverb_damping_{key}",
        help="The amount of absorption of sound in the room."
    )  
    reverb_wet_level = st.slider(
        "Wet Level",
        0.0, 1.0, 0.33, 0.01,
        key=f"reverb_wet_level_{key}",
        help="The level of the reverberated signal."
    )  
    reverb_dry_level = st.slider(
        "Dry Level",
        0.0, 1.0, 0.4, 0.01,
        key=f"reverb_dry_level_{key}",
        help="The level of the original signal."
    )    
    return ReverbEdit(
        reverb_room_size, 
        reverb_damping, 
        reverb_wet_level, 
        reverb_dry_level
    )

def create_soundboard(key: str, edits: list[str]) -> el_audio.Soundboard:
    edit_tabs = st.tabs(edits)
    created_edits = []
    for i, tab in enumerate(edit_tabs):
        with tab:
            if edits[i] == "Reverb":
                reverb = create_reverb(key) 
                created_edits.append(reverb) 
            elif edits[i] == "Chorus":
                chorus = create_chorus(key)
                created_edits.append(chorus)
            elif edits[i] == "Distortion":
                distortion = create_distortion(key)
                created_edits.append(distortion)
            elif edits[i] == "Limiter":
                limiter = create_limiter(key)
                created_edits.append(limiter)
            elif edits[i] == "Noise Gate":
                noise_gate = create_noise_gate(key)
                created_edits.append(noise_gate)
            elif edits[i] == "Compressor":
                compressor = create_compressor(key)
                created_edits.append(compressor) 
                
    return el_audio.Soundboard(created_edits)

def find_lines(group: int, characters: list[Character], dialogue: list[Dialogue]) -> list[int]:
    # if no group selected return all indices
    if group is None:
        return list(map(lambda d: d.line, dialogue))
    
    # character names whose lines we care about
    matching_characters = list(filter(lambda c: c.group == group, characters))
    character_names = list(map(lambda c: c.name, matching_characters))
    
    # get lines that match character names
    matching_dialogue = list(filter(lambda d: d.character.name in character_names, dialogue))
    matching_lines = list(map(lambda d: d.line, matching_dialogue))
    return matching_lines

def create_edit_dialogue_line(line: Dialogue, audio_file: str) -> None:
    edit_audio_line_key = f"editing_audio_line_{line.line}"                                 

    if edit_audio_line_key not in st.session_state:
        st.session_state[edit_audio_line_key] = False
     
    edit_dialogue_line = st.button("Edit Audio", key=f"audio_edit_btn_{line.line}", use_container_width=True)
    if edit_dialogue_line:
        st.session_state[edit_audio_line_key] = not st.session_state[edit_audio_line_key] 
        
    should_show_audio_edit = st.session_state[edit_audio_line_key]
    if should_show_audio_edit:    
        with st.container(border=True):
            speech_duration = el_audio.get_audio_duration(audio_file)  
            speech_duration_int = int(speech_duration * 1000)        
            basic_tab, soundboard_tab, special_tab,  = st.tabs(["Basic", "Soundboard", "Special Effect"])
            
            with basic_tab:
                st.markdown("### 🔊 Basic Settings")
                extend_tab, fade_tab, trim_tab, volume_tab = st.tabs(["Extend", "Fade", "Trim", "Volume"])
                with extend_tab:
                    extend_in_slider = st.slider(
                        "Extend In (ms)",
                        0,
                        5000,
                        0,
                        key=f"extend_in_{line.line}",
                        help="Allows you to extend the beginning of audio up to 5 seconds."
                    )
                    extend_out_slider = st.slider(
                        "Extend Out (ms)",
                        0,
                        5000,
                        0,
                        key=f"extend_out_{line.line}",
                        help="Allows you to extend the end of audio up to 5 seconds."
                    )                   
                with fade_tab:
                    fade_slider = st.slider(
                        "Fade (ms)",
                        0,
                        speech_duration_int,
                        (0, speech_duration_int),
                        key=f"fade_{line.line}",
                        help="Allows you to provide a fade in and a fade out."
                    )
                with volume_tab:
                    line_volume = st.slider(
                        "Volume (dB)",
                        -25, 
                        25, 
                        0, 
                        1, 
                        key=f"volume_{line.line}",
                        help="A positive value will increase the volume and a negative value will decrease the volume."
                    )
                with trim_tab:
                    trim_slider = st.slider(
                        "Trim (ms)",
                        0,
                        speech_duration_int,
                        (0, speech_duration_int),
                        key=f"trim_{line.line}",
                        help="Allows you to trim the audio from either the beginning or the end."
                    )
                basic = BasicEdit(
                    speech_duration_int, 
                    line_volume, 
                    fade_slider[0], 
                    speech_duration_int - fade_slider[1], 
                    trim_slider[0], 
                    speech_duration_int - trim_slider[1], 
                    extend_in_slider, 
                    extend_out_slider
                )
            
            with soundboard_tab:
                st.markdown("### 👂💫 Soundboard")                                
                soundboard = create_soundboard(line.line, [
                    "Compressor", 
                    "Chorus", 
                    "Distortion", 
                    "Limiter", 
                    "Noise Gate", 
                    "Reverb"
                ])
                soundboard.add(basic)
                            
            with special_tab:
                st.markdown("### 💥 Special Effect")
                    
                with st.expander("Upload Special Effect"):
                    with st.form("Audio File", clear_on_submit=True, border=False):
                        uploaded_special_effect = st.file_uploader(
                            "Upload Special Effect",
                            type=["mp3", "wav", "aiff"],
                            key=f"upload_effect_{line.line}",
                            label_visibility="collapsed"
                        )
                        submit_uploaded_special_effect = st.form_submit_button("Upload", use_container_width=True)
                        if uploaded_special_effect and submit_uploaded_special_effect:
                            if uploaded_special_effect:
                                audio_file = uploaded_special_effect.getvalue()
                                el_audio.save_sound_effect(audio_file, uploaded_special_effect.name)
                                st.toast("Special effect has been uploaded. Please click refresh to see it.", icon="👍")                      
                    
                col1, col2 = st.columns([8, 1])
                with col1:
                    effect_name = st.selectbox(
                        "Effects", 
                        el_audio.get_effect_names(), 
                        index=None, 
                        label_visibility="collapsed", 
                        placeholder="Select an effect",
                        key=f"effect_{line.line}"
                    )
                with col2:
                    st.button("Refresh", use_container_width=True, key=f"refresh_effect_{line.line}")
                    
                if effect_name:
                    effect_path = el_audio.get_effect_path(effect_name)
                    st.audio(effect_path)                   
                    
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
            
            with st.form(f"preview_edit_{line.line}", clear_on_submit=False, border=False):
                preview_line = st.form_submit_button(
                    "Preview", 
                    use_container_width=True
                )
                if preview_line:
                    effect_audio, preview_audio = el_audio.preview_audio(
                        audio_file, 
                        effect_path,
                        effect_start,
                        effect_volume,
                        effect_repeat,
                        effect_fade_out,
                        soundboard
                    )                          
                
                    adjustments = soundboard.adjustments()
                    if effect_name:
                        adjustments.append(f"`{effect_name.capitalize()}`")
                    if len(adjustments) > 0:
                        st.markdown(f"Adjustments: {' '.join(sorted(adjustments))}")  
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
                    else:
                        st.toast("There are no audio edits selected.", icon="ℹ️")
                                    
            with st.form(f"apply_edit_{line.line}", clear_on_submit=False, border=False):                                        
                apply_edits = st.form_submit_button(
                    "Apply", 
                    use_container_width=True
                )
                if apply_edits:
                    _, new_line_audio = el_audio.edit_audio(
                        audio_file, 
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

def create_edit_diatribe(sidebar: SidebarData, characters: list[Character], dialogue: list[Dialogue]) -> None:
    line_indices = [d.line for d in dialogue]
    
    background_tab, timing_tab = st.tabs(["Mastering", "Timing"])
    with background_tab:
        if sidebar.enable_instructions:
            st.markdown("You can adjust the background audio for all lines by a group of characters or all characters if no groups have been provided.")
        
        with st.container(border=True):
            st.markdown("### Character Group")
            character_groups = set([c.group for c in characters])
            background_group = st.selectbox(
                "Character Group _(optional)_)",
                character_groups,
                index=None,
                placeholder="Select a character group (optional)",
                help="Allows you to select a character group to apply the background audio to.",
                label_visibility="collapsed"
            )
            lines_affected = find_lines(background_group, characters, dialogue)
            log(f"all lines: {line_indices}")
            log(f"lines affected: {lines_affected}")
                        
        with st.container(border=True):
            st.markdown("### Soundboard")
            soundboard = create_soundboard("background", [
                "Compressor", 
                "Limiter", 
                "Reverb"
            ])
            
        with st.container(border=True):
            st.markdown("### Soundtrack")
            background_names = el_audio.get_background_audio()
            background_audio = st.selectbox(
                "Background Audio", 
                background_names, 
                index=None, 
                placeholder="Select a soundtrack (optional)",
                label_visibility="collapsed"
            )
            if background_audio:
                st.audio(el_audio.get_background_file_from_name(background_audio))
                background_fade, background_volume = st.columns([1, 3])
                with background_fade:
                    fade_in = st.toggle("Fade In", value=True)
                    fade_out = st.toggle("Fade Out", value=True)
                with background_volume:
                    lower_db = st.slider("Lower Background Volume (dB)", 0, 25, 0, 1, help="lowers the background audio by specified decibels")
                soundboard.add(BackgroundEdit(background_audio, fade_in, fade_out, lower_db))
                
        with st.container(border=False):
            add_background_btn = st.button("Apply", use_container_width=True)
            if add_background_btn and soundboard.is_enabled():
                with st.spinner("Adding background audio..."):
                    el_audio.apply_background_audio(
                        lines_affected, 
                        line_indices, 
                        soundboard, 
                        sidebar.join_gap,
                        sidebar.enable_normalization
                    )
                    st.toast("Background audio has been added.", icon="👍")