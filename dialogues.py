import json, os
import pandas as pd
import streamlit as st
from pathlib import Path
from elevenlabs import Voice
from el_audio import get_voice_id
from utils import log

class Character:
  def __init__(self, name: str, voice: str, voice_id: str, description: str = "") -> None:
    self.name = name
    self.voice = voice
    self.voice_id = voice_id
    self.description = description
  
  def to_dict(self) -> dict:
    return {
      "Name": self.name,
      "Voice": self.voice,
      "Voice_ID": self.voice_id,
      "Description": self.description
    }
  
  def __str__(self):
    return f"{self.name};{self.voice};{self.voice_id}"
  
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
  voices: list[Voice]
) -> dict:
  """Generate dialogue details in a common format suitiable for JSON."""
  characters: list[Character] = []
  for i, c in characters_df.iterrows():
    characters.append(Character(c["Name"], c["Voice"], get_voice_id(c["Voice"], voices), description=c["Description"]))
  dialogue: list[Dialogue] = []
  for i, d in dialogue_df.iterrows():
    character = next((c for c in characters if c.name == d["Speaker"]), None)
    dialogue.append(Dialogue(character, i, d["Text"]).to_dict()) 
  dialogue_details = {
    "characters": [c.to_dict() for c in characters],
    "dialogue": dialogue
  }  
  return dialogue_details 

def load_saved_dialogues() -> dict:
  """Load saved dialogues from the saves directory."""
  global_directory = Path("./saves")
  session_directory = Path(f"./session/{st.session_state.session_id}/saves")
  files = list(global_directory.glob("*.json")) + list(session_directory.glob("*.json"))
  names = {}
  for json_file in files:
    characters = []
    dialogues = []
    with open(json_file, "r") as f:
      data = json.load(f)
      for character in data["characters"]:
        characters.append(Character(
          character["Name"], 
          character["Voice"], 
          character["Voice_ID"], 
          description=character["Description"] if "Description" in character else ""
        ))
      for dialogue in data["dialogue"]:
        character = next((c for c in characters if c.name == dialogue["Speaker"]), None)
        dialogues.append(Dialogue(character, dialogue["Line"], dialogue["Text"]))
    names[json_file.stem] = { "characters": characters, "dialogue": dialogues }
  return names

def load_dialogues_with_names() -> (list[str], dict):
  """Load saved dialogues with their names from the saves directory."""
  saved_dialogues = load_saved_dialogues()
  saved_names = list(saved_dialogues.keys())  
  return saved_names, saved_dialogues

def save_dialogue(
  characters: pd.DataFrame, 
  dialogue: pd.DataFrame, 
  voices: list[Voice],
  save_filename: str
) -> None:
  """Save a dialogue to a JSON file."""""
  dialogue_details = generate_dialogue_details(characters, dialogue, voices) 
  os.makedirs(os.path.dirname(save_filename), exist_ok=True)     
  with open(save_filename, "w") as f:
    json.dump(dialogue_details, f, indent=2)  

def character_change(character_changes: dict) -> bool:
  """Check if characters where changed."""
  edited = len(character_changes["edited_rows"].keys()) > 0
  added = any(["Name" in c for c in character_changes["added_rows"]])
  deleted_rows = len(character_changes["deleted_rows"]) > 0
  is_change = edited or added or deleted_rows
  if is_change:
    log("character change")
    if added:
      log(f"\tadded characters: {character_changes['added_rows']}")
  return is_change

def added_or_removed_characters(character_changes: dict) -> bool:
  """Check if characters were added or removed from the character table."""
  edited_characters = False
  if "edited_rows" in character_changes:
    edited_rows = character_changes["edited_rows"]
    for r_key in edited_rows.keys():
      change = edited_rows[r_key]
      if "Name" in change.keys():
        edited_characters = True
        break # only need to find one          
  removed_characters = "deleted_rows" in character_changes and len(character_changes["deleted_rows"]) > 0 
  return edited_characters or removed_characters 

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