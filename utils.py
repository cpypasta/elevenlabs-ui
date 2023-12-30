import re

def extract_name(s: str) -> str:
  """Extract the voice name from the voice name with (cloned) suffix."""
  match = re.match(r"(.*?)( \(cloned\))?$", s)
  if match:
    return match.group(1)
  return s  