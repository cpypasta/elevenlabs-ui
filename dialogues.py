import elevenlabs as el

class Character:
  def __init__(self, name: str, voice: str, voice_id: str) -> None:
    self.name = name
    self.voice = voice
    self.voice_id = voice_id
  
  def to_dict(self) -> dict:
    return {
      "Name": self.name,
      "Voice": self.voice
    }
  
  def __str__(self):
    return f"{self.name} ({self.voice})"


class Dialogue:
  def __init__(self, character: Character, line: int, text: str):
    self.character = character
    self.line = line
    self.text = text
  
  def to_dict(self) -> dict:
    return {
      "Speaker": self.character.name,
      "Text": self.text
    }
    
  def __str__(self):
    return f"[{self.line}] {self.character.name}: {self.text}"


tracy_emily = Character("Tracy", "Emily", "LcfcDJNUP1GQjkzn1xUU")
hulk_callum = Character("Hulk", "Callum", "N2lVS1w4EtoT3dr4eOWO")

saved = {
  "Dumb Hulk": {
    "characters": [
      tracy_emily,
      hulk_callum
    ],
    "dialogue": [
      Dialogue(tracy_emily, 0, "Hello, who are you?"),
      Dialogue(hulk_callum, 1, "Hulk smash!"),
      Dialogue(tracy_emily, 2, "Okay. Nice to meet you hulk."),
      Dialogue(hulk_callum, 3, "Hulk smash!"),
      Dialogue(tracy_emily, 4, "Okay. I get it. You smash things."),
      Dialogue(hulk_callum, 5, "Hulk smash!"),
      Dialogue(tracy_emily, 6, "Okay. I'm going to leave now.")
    ]
  }
}