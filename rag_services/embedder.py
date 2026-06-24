from huggingface_hub import InferenceClient
from pathlib import Path
import json 

BASE_URL = "http://127.0.0.1:8080"

def embed_chunks(chunks: list[dict], force_invalidate_cache = False) -> list[dict]:
    if not force_invalidate_cache:
        embeded_chunks = load_from_cache()
        if embeded_chunks is not None:
            return embeded_chunks

    client = InferenceClient(BASE_URL)
    embeded_chunks = []

    total_chunks = len(chunks)
    for idx, chunk in enumerate(chunks):
        embeded_chunk = chunk
        print(f"embedding chunk {idx +1 }/{total_chunks}")
        embeddings = client.feature_extraction(chunk["text"])
        print("Done")
        embeded_chunk["embedding"]=embeddings[0].tolist()
        embeded_chunks.append(embeded_chunk)
    
    save_cache(embeded_chunks)
    return embeded_chunks

def save_cache(chunks: list[dict]): 
    folder_path = Path("__embeded_vector_cache")
    file_path = folder_path / "embeded_vector.json"

    folder_path.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump({"embeded_chunk": chunks}, file, indent=4)

def load_from_cache() -> list[dict] | None:
    file_path = Path("__embeded_vector_cache/embeded_vector.json")
    if not file_path.exists():
        return None
    with open(file_path,"r") as file:
        data = json.load(file)
        return data["embeded_chunk"]
    
def embedd_text(text: str) -> list:
    inference_client = InferenceClient(base_url=BASE_URL)
    embedded_text = inference_client.feature_extraction(text)
    return embedded_text[0].tolist()