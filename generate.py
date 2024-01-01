import json
import streamlit as st
import pandas as pd
from dialogues import Character, Dialogue
from openai import OpenAI
from jsonschema import validate
from utils import log
from sidebar import SidebarData

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

def generate_dialogue(system_prompt: str, input_prompt: str, sidebar: SidebarData) -> str:
  """Generate the dialogue using OpenAI."""
  client = OpenAI(api_key=sidebar.openai_api_key, timeout=180)  
  messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": input_prompt}
  ]
  chat_options = {
    "model": sidebar.openai_model,
    "temperature": sidebar.openai_temp,
    "max_tokens": sidebar.openai_max_tokens,
  }
  log(f"chat options: {chat_options}")
  
  response = client.chat.completions.create(
    **chat_options,
    messages=messages
  )
  # new_dialogue = '{ "characters": ["Brian"], "dialogue": [{"Speaker": "Brian", "Line": 1, "Text": "Hello, how are you?"}] }'
  new_dialogue = response.choices[0].message.content
  return new_dialogue

def load_dialogue_system_prompt() -> str:
  """Load the dialogue system prompt from the file."""
  with open("openai_dialogue_system_prompt.txt", "r") as f:
    system_prompt = f.read()
    return system_prompt
  
def load_continue_dialogue_system_prompt() -> str:
  """Load the continue dialogue system prompt from the file."""
  with open("openai_continue_system_prompt.txt", "r") as f:
    system_prompt = f.read()
    return system_prompt
    
def load_plot_system_prompt() -> str:
  """Load the plot system prompt from the file."""
  with open("openai_plot_system_prompt.txt", "r") as f:
    system_prompt = f.read()
    return system_prompt

def generate_plot_input_prompt(characters: list[Character]) -> dict:
  input_prompt = "CHARACTERS:\n"
  for i, c in enumerate(characters):
    input_prompt += f"<Name>{c.name}</Name>\n<Description>{c.description}</Description>\n\n\n"
  
  return input_prompt

def generate_dialogue_input_prompt(characters: list[Character], number_of_lines: int, plot: str) -> dict:
  input_prompt = f"NUMBER OF LINES:\n<Lines>{number_of_lines}</Lines>\n\n\n"
  input_prompt += generate_plot_input_prompt(characters)
  input_prompt += f"PLOT:\n<Plot>{plot}</Plot>\n\n\n"
  return input_prompt
  
def generate_continue_dialogue_input_prompt(characters: list[Character], number_of_lines: int, plot: str, dialogue: list[Dialogue]) -> dict:
  input_prompt = generate_dialogue_input_prompt(characters, number_of_lines, plot)
  input_prompt += f"EXISTING LINES:\n"
  for line in dialogue:
    input_prompt += f"<Dialogue><Speaker>{line.character.name}</Speaker>\n<Number>{line.line}</Number><Text>{line.text}</Text></Dialogue>\n\n\n"
  return input_prompt

def create_continue_dialogue(sidebar: SidebarData, characters: list[Character], dialogue: list[Dialogue]) -> pd.DataFrame:
  with st.spinner("Generating dialogue..."):
    input_prompt = generate_continue_dialogue_input_prompt(
      characters, 
      st.session_state["number_of_lines"], 
      st.session_state["plot"], 
      dialogue
    )
    system_prompt = load_continue_dialogue_system_prompt()
    try:
      if "audio_files" in st.session_state:
        del st.session_state["audio_files"]
      if "final_audio" in st.session_state:
        del st.session_state["final_audio"]
        
      lines = [d.to_dict(without_line=True) for d in dialogue]
      dialogue = generate_dialogue(system_prompt, input_prompt, sidebar)
      dialogue = json.loads(dialogue)
      validate(instance=dialogue, schema=openai_dialogue_schema)
      for line in dialogue["dialogue"]:
        character_found = next((c for c in characters if c.name == line["Speaker"]), None)
        if character_found:
          lines.append({ "Speaker": line["Speaker"], "Text": line["Text"] })
      log(f"lines produced: {len(lines)}")
      result = pd.DataFrame(lines, columns=["Speaker", "Text"])
      return result
    except Exception as e:
      log(e)
      st.error("An error occured while generating the dialogue. Please try again.") 
      return None

def create_dialogue_generation(sidebar: SidebarData, characters: list[Character]) -> pd.DataFrame:
  result = None
  
  if sidebar.openai_api_key:
    with st.expander("Dialogue Generation"):
      st.markdown("You can generate the dialogue using OpenAI. It will use the character descriptions and the plot to generate the dialogue. If you are not feeling creative, you can even have OpenAI generate the plot using the character descriptions. If you are not getting the number of lines, either try again or put in the plot text the number of lines you desire to provide encouragement to OpenAI.")
      generate_plot_btn = st.button("Generate Plot", use_container_width=True)
      plot_value = ""
      if generate_plot_btn:
        with st.spinner("Generating plot..."):
          input_prompt = generate_plot_input_prompt(characters)
          system_prompt = load_plot_system_prompt()
          try:
            plot_value = generate_dialogue(system_prompt, input_prompt, sidebar)
            st.session_state["plot"] = plot_value
          except Exception as e:
            log(e)
            st.error("An error occured while generating the plot. Please try again.")
      elif "plot" in st.session_state:
        plot_value = st.session_state["plot"]
      
      plot = st.text_area("Desired Plot", plot_value, placeholder="describe what you want to happen in the dialogue")
      if "plot" in st.session_state and st.session_state["plot"] != plot:
        st.session_state["plot"] = plot
        
      number_of_lines = st.slider("Approximate Number of Dialogue Lines", 5, 50, 10, 5)
      st.session_state["number_of_lines"] = number_of_lines
      generate_dialogue_btn = st.button(
        "Generate Dialogue", 
        use_container_width=True, 
        disabled=(len(plot) == 0)
      )    
      
      if generate_dialogue_btn:
        with st.spinner("Generating dialogue..."):
          input_prompt = generate_dialogue_input_prompt(characters, number_of_lines, plot)
          system_prompt = load_dialogue_system_prompt()
          try:
            if "audio_files" in st.session_state:
              del st.session_state["audio_files"]
            if "final_audio" in st.session_state:
              del st.session_state["final_audio"]
              
            dialogue = generate_dialogue(system_prompt, input_prompt, sidebar)
            dialogue = json.loads(dialogue)
            validate(instance=dialogue, schema=openai_dialogue_schema)
            lines = []
            for line in dialogue["dialogue"]:
              character_found = next((c for c in characters if c.name == line["Speaker"]), None)
              if character_found:
                lines.append({ "Speaker": line["Speaker"], "Text": line["Text"] })
            log(f"lines produced: {len(lines)}")
            result = pd.DataFrame(lines, columns=["Speaker", "Text"])
          except Exception as e:
            log(e)
            st.error("An error occured while generating the dialogue. Please try again.")
  return result