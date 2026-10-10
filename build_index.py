import re
import chromadb

text = open("docs/metrics.md", encoding="utf-8").read()
chunks = [c.strip() for c in re.split(r"\n(?=## )", text) if c.strip().startswith("## ")]

client = chromadb.PersistentClient(path="chroma_db")
try:
    client.delete_collection("metrics")
except Exception:
    pass
collection = client.create_collection("metrics")
collection.add(documents=chunks, ids=[f"metric-{i}" for i in range(len(chunks))])
print(f"Indexed {len(chunks)} chunks")