import os, csv
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

DATA_DIR = "data"
METADATA_CSV = "metadata.csv"
CHROMA_DB = "./chroma_db"

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

chroma = chromadb.PersistentClient(path=CHROMA_DB)
collection = chroma.get_or_create_collection("usask-programs")

def load_metadata():
    """Map filename -> {title, college, level, url} from metadata.csv."""
    meta = {}
    with open(METADATA_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            meta[row["filename"]] = row
    return meta # {filename: {title, college, level, url}, ...}


def chunk_text(text, size=400, overlap=50):
    """Split text into chunks of approximately size, with overlap."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), size-overlap):
        chunk = " ".join(words[i:i+size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def embed_text(text):
    """Embed text using OpenAI embeddings."""
    resp = client.embeddings.create(model="text-embedding-3-small", input=text)
    return [d.embedding for d in resp.data] # list of lists of floats
    # [
    # [0.1, -0.2, ...],
    # [0.5, 0.9, ...],
    # [-0.3, 0.4, ...]
    # ]
    # each list of floats is a vector embedding of length 1536


def ingest():
    meta = load_metadata() # {filename: {title, college, level, url}, ...}
    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".txt")] # list of filenames in data/
    print(f"Found {len(files)} files to ingest.")

    all_ids, all_texts, all_metas = [], [], []
    for fname in files:
        with open(os.path.join(DATA_DIR, fname), encoding="utf-8") as f:
            text = f.read() # read the text file as a string
        chunks = chunk_text(text) # split the text into chunks
        info = meta.get(fname, {}) # get the metadata for the file

        for i, chunk in enumerate(chunks):
            # each chunk gets a unique ID, its own text, a copy of the metadata (Even though metadata is repeated per chunk.)
            all_ids.append(f"{fname}::chunk{i}") # 
            all_texts.append(chunk) # add the chunk to the list of texts
            all_metas.append({
                "source": fname,
                "title": info.get("title", fname),
                "college": info.get("college", "Unknown"),
                "level": info.get("level", "Unknown"), 
                "url": info.get("url", "")
            })
    print(f"Total chunks: {len(all_texts)}. Embedding in batches...")

    # Embed in batches of 100
    BATCH_SIZE = 100
    for start in range(0, len(all_texts), BATCH_SIZE):
        b_ids = all_ids[start:start + BATCH_SIZE]
        b_texts = all_texts[start:start + BATCH_SIZE]
        b_metas = all_metas[start:start + BATCH_SIZE]

        embeddings = embed_text(b_texts) # list of lists of embeddings
        collection.add(
            ids=b_ids,
            embeddings=embeddings,
            documents=b_texts,
            metadatas=b_metas
        )
        print(f"  embedded {min(start + BATCH_SIZE, len(all_texts))}/{len(all_texts)}")
    
    print(f"\nDone. Collection now has {collection.count()} chunks.")

if __name__ == "__main__":
    ingest()