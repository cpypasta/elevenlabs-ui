import os, re
import pandas as pd
import streamlit as st
from elevenlabs import Voice
from diatribe.el_audio import get_voice_id
from diatribe.utils import log

class Character:
  def __init__(self, name: str, voice: str, voice_id: str, description: str = "", group: int = 1) -> None:
    self.name = name
    self.voice = voice
    self.voice_id = voice_id
    self.description = description
    self.group = group
  
  def to_dict(self) -> dict:
    return {
      "Name": self.name,
      "Voice": self.voice,
      "Voice_ID": self.voice_id,
      "Description": self.description,
      "Group": self.group
    }
  
  def __str__(self):
    return f"{self.name};{self.voice};{self.voice_id};{self.description};{self.group}"
  
  def __repr__(self) -> str:
    return self.__str__()


class Dialogue:
  def __init__(self, character: Character, line: int, text: str):
    self.character = character
    self.line = line
    self.text = text
  
  def to_dict(self, without_line: bool = False) -> dict:
    if without_line:
      return {
        "Speaker": self.character.name,
        "Text": self.text
      }
    else:
      return {
        "Speaker": self.character.name,
        "Line": self.line,
        "Text": self.text
      }
    
  def __str__(self):
    return f"[{self.line}] {self.character.name}: {self.text}"


def generate_dialogue_details(
  characters_df: pd.DataFrame, 
  dialogue_df: pd.DataFrame, 
  voices: list[Voice],
  plot: str = None
) -> dict:
  """Generate dialogue details in a common format suitiable for JSON."""
  characters: list[Character] = []
  for i, c in characters_df.iterrows():
    characters.append(Character(c["Name"], c["Voice"], get_voice_id(c["Voice"], voices), description=c["Description"], group=c["Group"]))
  dialogue: list[Dialogue] = []
  for i, d in dialogue_df.iterrows():
    character = next((c for c in characters if c.name == d["Speaker"]), None)
    dialogue.append(Dialogue(character, i, d["Text"]).to_dict()) 
  dialogue_details = {
    "characters": [c.to_dict() for c in characters],
    "plot": plot,
    "dialogue": dialogue
  }  
  return dialogue_details 

def convert_dialogue_import_into_data(data: str) -> dict:
  """Convert the imported dialogue into a common format."""
  import_parts = re.split(r'\n\n|\r\n\r\n', data)
  if len(import_parts) == 3:
    characters_input, plot, dialogue_input = import_parts
  else:    
    return None

  plot = plot.split("\n")
  plot = plot[1] if len(plot) > 1 else "" 
  characters = []
  dialogues = []      
  
  for character in characters_input.split("\n"):
    if character.startswith("#"):
      continue
    name, description = character.split(":")
    name, voice, *group = name.split("|")
    if len(group) == 0 or group[0] == "None":
      group = 1
    else:
      group = group[0]
    characters.append({ "Name": name, "Voice": voice, "Description": description.strip(), "Group": group })
  
  for line in dialogue_input.split("\n"):
    if line.startswith("#"):
      continue
    speaker, *text = line.split(":")
    text = text[0]
    character = next((c for c in characters if c["Name"] == speaker), None)
    dialogues.append({ "Speaker": speaker, "Text": text.strip() })
  
  return {
    "characters": pd.DataFrame(characters, columns=["Name", "Voice", "Group", "Description"]), 
    "dialogue": pd.DataFrame(dialogues, columns=["Speaker", "Text"]), 
    "plot": plot
  }

def convert_dialogue_details_into_export(dialogue_details: dict) -> str:
  """Convert dialogue details into a common format for export."""
  characters = dialogue_details["characters"]
  plot = dialogue_details["plot"]
  plot = f"{plot}\n\n" if plot is not None and len(plot) > 0 else "\n"
  dialogue = dialogue_details["dialogue"]
  characters_output = "# CHARACTERS\n"
  for character in characters:
    character_description = character['Description']
    character_description = character_description if character_description is not None and len(character_description) > 0 else ""
    characters_output += f"{character['Name']}|{character['Voice']}|{character['Group']}: {character_description}\n"
  dialogue_output = "# DIALOGUE\n"
  for line in dialogue:
    dialogue_output += f"{line['Speaker']}: {line['Text']}\n"
  return f"{characters_output}\n# PLOT\n{plot}{dialogue_output.strip()}"

def export_dialogue(
  characters: pd.DataFrame, 
  dialogue: pd.DataFrame, 
  voices: list[Voice]
) -> str:
  save_filename = f"./session/{st.session_state.session_id}/export/dialogue.txt"
  plot = st.session_state["plot"] if "plot" in st.session_state else None
  dialogue_details = generate_dialogue_details(characters, dialogue, voices, plot=plot)
  dialogue_export = convert_dialogue_details_into_export(dialogue_details)
  os.makedirs(os.path.dirname(save_filename), exist_ok=True)     
  with open(save_filename, "w") as f:
    f.write(dialogue_export)  
  return save_filename

def characters_match(characters: pd.DataFrame, dialogue: pd.DataFrame) -> bool:
  """
  Check if the characters in the character table match the characters in the dialogue no matter order.
  It is okay if there are more characters in characters than dialogue.
  """
  characters_in_dialogue = list(dialogue["Speaker"])
  characters_in_character_table = list(characters["Name"])
  missing = False
  for c in characters_in_dialogue:
    if c not in characters_in_character_table:
      log(f"character {c} is missing from character table")
      missing = True
      break # only need to find one
  return not missing

def get_lines(dialogues: list[Dialogue]) -> list[int]:
  return [d.line for d in dialogues]