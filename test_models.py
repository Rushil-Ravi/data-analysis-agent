import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])

SKIP = ("whisper", "tts", "guard", "safeguard", "orpheus", "playai", "embed")
tool = {
    "type": "function",
    "function": {
        "name": "get_number",
        "description": "Returns a number",
        "parameters": {
            "type": "object",
            "properties": {"n": {"type": "integer"}},
            "required": ["n"],
        },
    },
}

for m in client.models.list().data:
    if any(s in m.id.lower() for s in SKIP):
        continue
    try:
        r = client.chat.completions.create(
            model=m.id,
            messages=[{"role": "user", "content": "Call get_number with n=5."}],
            tools=[tool],
            max_tokens=100,
        )
        called = bool(r.choices[0].message.tool_calls)
        print(f"{m.id}: tool calling works = {called}")
    except Exception as e:
        print(f"{m.id}: FAILED - {str(e)[:90]}")