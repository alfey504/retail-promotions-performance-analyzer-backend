from services.db_services.session import init_db
from services.kpi_services.historic_kpi_calculators.historic_uplift import historic_uplift
from api.user_services.create_user import create_user
from api.api import get_app
import uvicorn
import os 

from services.rag_services.markdown_loader import chunk_markdown_by_heading
from services.rag_services.embedding_services import embed_chunks
from services.rag_services.qdrant_services import load_to_qdrant
from langchain_openai import ChatOpenAI
from services.rag_services.qdrant_services import PROMOTION_GUIDEBOOK_COLLECTION_NAME

def main():

    # chunks = chunk_markdown_by_heading("documents/sales_guidebook.md")
    # embeddings = embed_chunks(chunks, "sales_guidebook")
    # load_to_qdrant(embeddings, collection=PROMOTION_GUIDEBOOK_COLLECTION_NAME)

    init_db()
    app = get_app()

    uvicorn.run(app, env_file=".emv")

    # llm = ChatOpenAI(
    #     model="gpt-oss-120b",
    #     api_key=os.getenv("CEREBRAS_API_KEY"),
    #     base_url="https://api.cerebras.ai/v1",
    #     default_headers={
    #         "X-Cerebras-3rd-Party-Integration": "langgraph"
    #     }
    # )
    # response = llm.invoke("hello how are you ")
    # print(response.content)

    


if __name__ == "__main__":
    main()

