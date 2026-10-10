import chromadb

client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_or_create_collection("metrics")


def retrieve_context(question, k=3):
    result = collection.query(query_texts=[question], n_results=k)
    return "\n\n".join(result["documents"][0])