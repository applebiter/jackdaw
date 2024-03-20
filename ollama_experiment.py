import httpx
from ollama import generate

raw = httpx.get('https://indigo/images/04.jpg', verify=False)
raw.raise_for_status()

prompt = """Describe the included image:"""

for response in generate('llava', prompt, images=[raw.content], stream=True):
    print(response['response'], end='', flush=True)

print()
