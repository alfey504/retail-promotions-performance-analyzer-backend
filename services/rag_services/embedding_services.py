from huggingface_hub import InferenceClient
from pathlib import Path
import json 
from fastembed import SparseTextEmbedding, SparseEmbedding

BASE_URL = "http://127.0.0.1:8080"
SPARSE_MODEL_NAME = "Qdrant/bm25"


def embed_chunks(chunks: list[dict], name: str, force_invalidate_cache = False) -> list[dict]:
    if not force_invalidate_cache:
        embedded_chunks = load_from_cache(name)
        if embedded_chunks is not None:
            return embedded_chunks

    client = InferenceClient(BASE_URL)
    embedded_chunks = []

    total_chunks = len(chunks)
    for idx, chunk in enumerate(chunks):
        embedded_chunk = chunk
        print(f"embedding chunk {idx +1 }/{total_chunks}")
        embeddings = client.feature_extraction(chunk["text"])
        print("Done")
        embedded_chunk["embedding"]=embeddings[0].tolist()
        embedded_chunks.append(embedded_chunk)
    
    save_cache(embedded_chunks, name)
    return embedded_chunks

def save_cache(chunks: list[dict], name: str): 
    folder_path = Path("__embedded_vector_cache")
    file_path = folder_path / f"__embedded_vector_{name}.json"

    folder_path.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump({"embedded_chunk": chunks}, file, indent=4)

def load_from_cache(name: str) -> list[dict] | None:
    file_path = Path(f"__embedded_vector_cache/embedded_vector_{name}.json")
    if not file_path.exists():
        return None
    with open(file_path,"r") as file:
        data = json.load(file)
        return data["embedded_chunk"]
    
def embed_text(text: str) -> list:
    inference_client = InferenceClient(base_url=BASE_URL)
    embedded_text = inference_client.feature_extraction(text)
    return embedded_text[0].tolist()

def embed_sparse(chunks: list[dict]) -> list[dict]:
    sparse_embedding_model = SparseTextEmbedding(SPARSE_MODEL_NAME)
    sparse_vecs = list(sparse_embedding_model.embed([c["text"] for c in chunks]))
    for chunk, sparse_vec in zip(chunks, sparse_vecs):
        chunk["sparse_embeddings"] = sparse_vec
    return chunks

def sparse_embed_text(text: str) -> SparseEmbedding:
    sparse_embedding_model = SparseTextEmbedding(SPARSE_MODEL_NAME)
    return list(sparse_embedding_model.embed(text))[0]