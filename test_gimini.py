import google.generativeai as genai
import os

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

response = genai.generate_text(
    model="gemini-2.5-flash",
    prompt="Hello world",
    max_output_tokens=50
)
print(response.text)