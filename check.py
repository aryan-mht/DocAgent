import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

print("OpenAI key:", "YES" if os.getenv("OPENAI_API_KEY", "").startswith("sk-") else "NO")
print("Tavily key:", "YES" if os.getenv("TAVILY_API_KEY", "").startswith("tvly-") else "NO")

client = OpenAI()
resp = client.embeddings.create(model="text-embedding-3-small", input="hello world")
print("OpenAI embedding response:", len(resp.data[0].embedding))