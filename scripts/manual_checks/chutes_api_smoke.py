
import os
import sys
from openai import OpenAI

api_key = os.getenv("CHUTES_API_KEY")
if not api_key:
    print("Error: CHUTES_API_KEY not found in environment")
    sys.exit(1)

print(f"Testing Chutes API with key ending in ...{api_key[-4:]}")

client = OpenAI(
    base_url="https://llm.chutes.ai/v1",
    api_key=api_key
)

try:
    print("Sending request to MiniMaxAI/MiniMax-M2.1-TEE...")
    response = client.chat.completions.create(
        model="MiniMaxAI/MiniMax-M2.1-TEE",
        messages=[
            {"role": "system", "content": "You are a JSON generator. Output {'result': 'YES'}."},
            {"role": "user", "content": "Are you online?"}
        ],
        temperature=0.1,
        max_tokens=1000,
        response_format={"type": "json_object"}
    )
    print("Response received:")
    # print(response.choices[0].message.content)
    try:
        print(response.model_dump())
    except:
        print(response)
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
