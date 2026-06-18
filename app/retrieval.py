from app.ingest import collection, embed_text, client

def vector_search(query, k=4):
    """Return top-k most relevant chunk (text + metadata) for a query."""
    q_emb = embed_text([query]) # returns a list with one embedding
    results = collection.query(
        query_embeddings=q_emb,  # query embedding
        n_results=k # number of results to return
    )

    # results is a dictionary with keys "documents", "metadatas"
    chunks = results["documents"][0] # list of text chunks
    metas = results["metadatas"][0] # list of metadata dictionaries

    return chunks, metas # return a tuple of lists


def answer_from_docs(query, k=4):
    """Full RAG: retrieve relevant chunks, then have the LLM answer from them."""
    chunks, metas = vector_search(query, k=k)

    context = "\n\n---\n\n".join(chunks)

    # prompt the LLM to answer the question based on the context
    system_prompt = (
        "You are a helpful assistant answering questions about University of "
        "Saskatchewan academic programs. Use ONLY the context provided to answer. "
        "If the answer is not in the context, say you don't have that information. "
        "Be concise and accurate."
    )

    usr_prompt = f"Context:\n{context}\n\nQuestion: {query}"

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": usr_prompt}
        ],
    )

    answer = resp.choices[0].message.content # extract the answer from the response
    return answer, metas # return the answer and the metadata

if __name__ == "__main__":
    print("USask Program Assistant (RAG). Type a question, or 'quit' to exit.\n")
    while True:
        query = input("You: ").strip()
        if query.lower() in ("quit", "exit", "q"):
            print("Goodbye.")
            break
        if not query:
            continue
        answer, sources = answer_from_docs(query)
        print("\nAssistant:", answer)
        print("\nSources:")
        for m in sources:
            print(f"  - {m['title']} ({m['college']}, {m['level']})")
        print("\n" + "-" * 60 + "\n")