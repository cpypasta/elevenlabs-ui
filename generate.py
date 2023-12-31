import json
import streamlit as st
import pandas as pd
from dialogues import Character
from openai import OpenAI
from jsonschema import validate

openai_dialogue_schema = {
  "type": "object",
  "properties": {
    "characters": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "dialogue": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "Speaker": {
            "type": "string"
          },
          "Line": {
            "type": "integer"
          },
          "Text": {
            "type": "string"
          }
        }
      }
    }
  }
}

def generate_dialogue(system_prompt: str, input_prompt: str, openai_api_key: str) -> str:
  """Generate the dialogue using OpenAI."""
  client = OpenAI(api_key=openai_api_key)
  messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": input_prompt}
  ]
  response = client.chat.completions.create(
    model="gpt-4",
    temperature=1.0,
    max_tokens=4095,
    messages=messages
  )
  new_dialogue = response.choices[0].message.content
  return new_dialogue

def load_dialogue_system_prompt(dialogue_lines: int) -> str:
  """Load the dialogue system prompt from the file."""
  with open("openai_dialogue_system_prompt.txt", "r") as f:
    system_prompt = f.read()
    system_prompt = system_prompt.replace("{dialogue_lines}", str(dialogue_lines))
    return system_prompt
    
def load_plot_system_prompt() -> str:
  """Load the plot system prompt from the file."""
  with open("openai_plot_system_prompt.txt", "r") as f:
    system_prompt = f.read()
    return system_prompt

def generate_plot_input_prompt(characters: list[Character]) -> dict:
  input_prompt = "CHARACTERS:\n"
  for i, c in enumerate(characters):
    input_prompt += f"[{i}]\n<Name>{c.name}</Name>\n<Description>{c.description}</Description>\n\n"
  
  return input_prompt

def generate_dialogue_input_prompt(characters: list[Character], plot: str) -> dict:
  input_prompt = generate_plot_input_prompt(characters)
  
  input_prompt += f"PLOT:\n<Plot>{plot}</Plot>\n"
  return input_prompt
  
def create_dialogue_generation(openai_api_key: str, characters: list[Character]) -> pd.DataFrame:
  result = None
  if openai_api_key:
    with st.expander("Dialogue Generation"):
      st.info("You can generate the dialogue using OpenAI. It will use the character descriptions and the plot to generate the dialogue. If you are not feeling creative, you can even have OpenAI generate the plot using the character descriptions.")
      generate_plot_btn = st.button("Generate Plot", use_container_width=True)
      plot_value = ""
      if generate_plot_btn:
        with st.spinner("Generating plot..."):
          input_prompt = generate_plot_input_prompt(characters)
          system_prompt = load_plot_system_prompt()
          try:
            plot_value = generate_dialogue(system_prompt, input_prompt, openai_api_key)
            st.session_state["plot"] = plot_value
          except Exception as e:
            print(e)
            st.error("An error occured while generating the plot. Please try again.")
      elif "plot" in st.session_state:
        plot_value = st.session_state["plot"]
      
      plot = st.text_area("Desired Plot", plot_value, placeholder="describe what you want to happen in the dialogue")
      if "plot" in st.session_state and st.session_state["plot"] != plot:
        st.session_state["plot"] = plot
        
      number_of_lines = st.slider("Approximate Number of Dialogue Lines", 5, 100, 10, 5)
      generate_dialogue_btn = st.button("Generate Dialogue", use_container_width=True, disabled=(len(plot) == 0))    
      
      if generate_dialogue_btn:
        with st.spinner("Generating dialogue..."):
          input_prompt = generate_dialogue_input_prompt(characters, plot)
          system_prompt = load_dialogue_system_prompt(number_of_lines)
          try:
            if "audio_files" in st.session_state:
              del st.session_state["audio_files"]
            dialogue = generate_dialogue(system_prompt, input_prompt, openai_api_key)
            dialogue = json.loads(dialogue)
            validate(instance=dialogue, schema=openai_dialogue_schema)
            lines = []
            for line in dialogue["dialogue"]:
              lines.append({ "Speaker": line["Speaker"], "Text": line["Text"] })
            result = pd.DataFrame(lines, columns=["Speaker", "Text"])
          except Exception as e:
            print(e)
            st.error("An error occured while generating the dialogue. Please try again.")
  return result