import streamlit as st
import diatribe.el_audio as el_audio
from diatribe.dialogues import Dialogue
from diatribe.utils import log

def create_edit_dialogue_line(line: Dialogue, audio_file: str) -> None:
    edit_audio_line_key = f"editing_audio_line_{line.line}"                                 

    if edit_audio_line_key not in st.session_state:
        st.session_state[edit_audio_line_key] = False
        
    edit_dialogue_line = st.button("Edit Audio", key=f"audio_edit_btn_{line.line}", use_container_width=True)
    if edit_dialogue_line:
        st.session_state[edit_audio_line_key] = not st.session_state[edit_audio_line_key] 
        
    should_show_audio_edit = st.session_state[edit_audio_line_key]
    if should_show_audio_edit:    
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
            basic = el_audio.Basic(
                speech_duration_int, 
                line_volume, 
                fade_slider, 
                trim_slider,
                (extend_in_slider, extend_out_slider)
            )
        
        with soundboard_tab:
            st.markdown("### 👂💫 Soundboard")
            compressor_tab, chorus_tab, distortion_tab, limiter_tab, noise_gate_tab, reverb_tab = st.tabs([
                "Compressor", 
                "Chorus",
                "Distortion",
                "Limiter",
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
                    0.0, 50.0, 0.0, 0.5,
                    key=f"distortion_db_{line.line}",
                    help="The amount of distortion."
                )                    
            with limiter_tab:
                st.markdown("A limiter is similar to a compressor, but it is a more extreme form of compression. It will compress the dynamic range by making the quiet parts louder and and the loud parts quieter. This will often be used in combination with the compressor.")
                limiter_threshold_db = st.slider(
                    "Threshold (dB)",
                    -10.0, 0.0, 0.0, 0.5,
                    key=f"limiter_threshold_db_{line.line}",
                    help="The threshold above which the limiter is applied."
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
                noise_gate_ratio,
                limiter_threshold_db
            )
                        
        with special_tab:
            st.markdown("### 💥 Special Effect")
            
            with st.form("upload special effect", clear_on_submit=True, border=True):
                uploaded_special_effect = st.file_uploader(
                    "Upload Special Effect",
                    type=["mp3", "wav", "aiff"],
                    key=f"upload_effect_{line.line}"
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
        
        preview_line = st.button(
            "Preview", 
            key=f"preview_{line.line}",
            use_container_width=True
        )
        if preview_line:
            effect_audio, preview_audio, pedals = el_audio.preview_audio(
                audio_file, 
                basic, 
                effect_path,
                effect_start,
                effect_volume,
                effect_repeat,
                effect_fade_out,
                soundboard
            )                          
        
            pedals = [f'`{p}`' for p in pedals]
            adjustments = pedals
            adjustments.extend(basic.adjustments())
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
                            
        apply_edits = st.button("Apply", key=f"apply_{line.line}", use_container_width=True)
        if apply_edits:
            _, new_line_audio, _ = el_audio.edit_audio(
                audio_file, 
                basic, 
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

def create_edit_diatribe() -> None:
    # ambience (select charaters and apply reverb and background and volume)
    # timing (allow for adjusting when each dialogue line starts)
    st.tabs([""])