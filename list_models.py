import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)
api_key = os.getenv("GEMINI_API_KEY")
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
r = requests.get(url)

try:
    data = r.json()
    models = [m['name'] for m in data.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
    with open("models_out.txt", "w") as f:
        f.write("\n".join(models))
except Exception as e:
    with open("models_out.txt", "w") as f:
        f.write(str(e) + "\n" + r.text)
