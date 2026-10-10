import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://your-resource-name.services.ai.azure.com/openai/v1/")
model_name = os.getenv("AZURE_OPENAI_MODEL_NAME", "gpt-oss-120b")
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "Neo-Hackathon")
api_key = os.getenv("AZURE_OPENAI_API_KEY", "")

client = OpenAI(
    base_url=endpoint,
    api_key=api_key
)

completion = client.chat.completions.create(
    model=deployment_name,
    messages=[
        {
            "role": "user",
            "content": "What is the capital of France?",
        }
    ],
)

print(completion.choices[0].message)