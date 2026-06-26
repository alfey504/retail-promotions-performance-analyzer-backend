from qdrant_client import QdrantClient
from qdrant_client.models import ( 
    VectorParams, 
    Distance, 
    SparseVectorParams, 
    Modifier, 
    PointStruct,
    SparseVector,
    Prefetch,
    FusionQuery,
    Fusion
)
from fastembed import SparseTextEmbedding, SparseEmbedding
from services.rag_services.embedding_services import embed_text, sparse_embed_text, embed_sparse

import os
import uuid
COLLECTION_NAME = "promotion_profile.pdf"
SPARSE_MODEL_NAME = "Qdrant/bm25"
DENSE_DIM = 1024

def stable_point_id(chunk: dict):
     return str(uuid.uuid5(uuid.NAMESPACE_URL, str(chunk["id"])))

def get_qdrant_client(): 
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    qdrant_url = os.getenv("QDRANT_URL")

    if qdrant_api_key and qdrant_url:
        return QdrantClient(api_key=qdrant_api_key, url=qdrant_url)
    
def ensure_collection(client: QdrantClient, dense_dim: int):
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={"dense": VectorParams(size=dense_dim, distance=Distance.COSINE)},
            sparse_vectors_config= {"bm25" : SparseVectorParams(modifier=Modifier.IDF)}
        )


def upsert(client: QdrantClient, chunks: list[dict]):
    # print(chunks[0]["embedding"])
    points = [
        PointStruct(
            id = stable_point_id(c),
            vector={
                "dense" : c["embedding"],
                "bm25" : SparseVector(
                    indices=c["sparse_embeddings"].indices.tolist(),
                    values=c["sparse_embeddings"].values.tolist()
                )
             },
             payload={
                "id": c["id"],
                "text" : c["text"],
                **c["meta_data"]
             }
        )
        for c in chunks
    ]   
    batch_size = 100
    for i in range(0, len(points), batch_size):
        client.upsert(collection_name=COLLECTION_NAME, points=points[i: i+batch_size])
        print(f"upserted {len(points)} hybrid points into '{COLLECTION_NAME}'")

def load_to_qdrant(chunks: list[dict]):
    client = get_qdrant_client()
    if client is None:
        raise Exception("unable to fetch qdrant_client")
    ensure_collection(client=client, dense_dim=DENSE_DIM)
    sparse_chunks = embed_sparse(chunks=chunks)
    upsert(client, sparse_chunks)

def search_query(query: str, top_k: int=5, prefetch_limit:int = 20):
    client = get_qdrant_client()
    if client is None:
        raise Exception("failed to fetch Qdrant Client")
    embedded_query = embed_text(query)
    print(len(embedded_query))
    sparse_embed = sparse_embed_text(query)

    query_results = client.query_points(
        collection_name=COLLECTION_NAME,
        prefetch=[
            Prefetch(query=embedded_query, using="dense", limit=prefetch_limit),
            Prefetch(
                query=SparseVector(
                    indices=sparse_embed.indices.tolist(), 
                    values=sparse_embed.values.tolist(),
                ),
                using="bm25",
                limit=prefetch_limit,
            ),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=top_k,
    ).points
    extracted_texts = []
    for query_result in query_results:
        if (query_result is None) or (query_result.payload is None) :
            raise Exception("vector db query returned None")
        print(f"score={query_result.score:.3f}  {query_result.payload.get('promotion_name', query_result.payload.get('chunk_id'))}")
        print(" ", query_result.payload["text"][:160], "...")
        extracted_texts.append(query_result.payload["text"])
    return extracted_texts

    