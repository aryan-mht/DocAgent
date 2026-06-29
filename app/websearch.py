import os
from tavily import TavilyClient
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def web_search(query, max_results=4):
    """Search the web with Tavily, return concatenated result snippets."""
    results = tavily.search(query, max_results=max_results)
    snippets = []
    for result in results.get("results", []):
        snippets.append(f"Source: {result['url']}\n{result['content']}")
    return "\n\n---\n\n".join(snippets)


def answer_from_web(query):
    """Full web tool: search the web, then have the LLM summarize an answer."""
    scoped_query = f"University of Saskatchewan USask {query}"
    context = web_search(scoped_query)
    if not context.strip():
        return "I couldn't find relevant information on the web for that."

    system_msg = (
        "You are a helpful assistant. Answer the user's question using the web "
        "search results provided. Be concise and accurate. Cite information from "
        "the sources. If the results don't answer the question, say so."
    )
    user_msg = f"Web search results:\n{context}\n\nQuestion: {query}"

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
    )
    return resp.choices[0].message.content.strip()

if __name__ == "__main__":
    for q in [
        "What is the tuition for international students at the University of Saskatchewan?",
        "What are the application deadlines at USask?",
    ]:
        print("Q:", q)
        print("A:", answer_from_web(q))
        print("-" * 60)