import json
from pathlib import Path

class Character:
  def __init__(self, name: str, voice: str, voice_id: str) -> None:
    self.name = name
    self.voice = voice
    self.voice_id = voice_id
  
  def to_dict(self) -> dict:
    return {
      "Name": self.name,
      "Voice": self.voice,
      "Voice_ID": self.voice_id
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


def load_saved_dialogues() -> dict:
  directory = Path("./saves")
  names = {}
  for json_file in directory.glob("*.json"):
    characters = []
    dialogues = []
    with open(json_file, "r") as f:
      data = json.load(f)
      for character in data["characters"]:
        characters.append(Character(character["Name"], character["Voice"], character["Voice_ID"]))
      for dialogue in data["dialogue"]:
        character = next((c for c in characters if c.name == dialogue["Speaker"]), None)
        dialogues.append(Dialogue(character, dialogue["Line"], dialogue["Text"]))
    names[json_file.stem] = { "characters": characters, "dialogue": dialogues }
  return names