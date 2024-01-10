import streamlit as st
  
st.set_page_config(layout="wide", page_title="Diatribe Help", page_icon="🎧")

st.title(":sparkles: Diatribe Help")

with st.sidebar:
    # table of contents for the help page
    st.markdown("""
        1. [Quickstart](#quickstart)
        1. [Saving & Loading](#saving-loading)
            * [Exporting](#exporting)
            * [Importing](#importing)
        1. [Characters](#characters)
            * [Exploring Voices](#exploring-voices)
        1. [Dialogue](#dialogue)
            * [Generation](#generation)
        1. [Audio Dialogue](#audio-dialogue)
            * [Editing Audio](#editing-audio)
        1. [Audio Diatribe](#audio-diatribe)
            * [Editing Audio](#editing-audio)
        1. [Options](#options)
            * [Dialogue Options](#dialogue-options)
            * [OpenAI Options](#openai-options)
        1. [Usage](#usage)
    """)

st.markdown("""
    Diatribe is a tool to create interesting audio dialogues. Diatribe is mostly a wrapper around ElevenLabs.
    ElevenLabs has a `projects` feature, but I found it lacking for what I wanted to do.
""")

st.markdown("""
    The motivation for creating Diatribe was to create a tool for my family. We were haing so much
    fun with the cloned voices. At first, I created everything in ElevenLabs and combined and edited
    the dialogue lines in a desktop audio editor. But as family demand for more dialogues continued to grow and
    being the lazy programmer that I am, I decided to create a tool to automate the process. The name `Diatribe`
    was given since the dialogues created tended to be silly and long-winded.
""")

st.markdown("# Quickstart")

st.markdown("# Saving & Loading")
st.markdown("## Exporting")
st.markdown("## Importing")

st.markdown("# Characters")
st.markdown("## Exploring Voices")

st.markdown("# Dialogue")
st.markdown("## Generation")

st.markdown("# Audio Dialogue")
st.markdown("## Editing Audio")

st.markdown("# Audio Diatribe")
st.markdown("## Editing Audio")

st.markdown("# Options")
st.markdown("## Dialogue Options")
st.markdown("## OpenAI Options")

st.markdown("# Usage")