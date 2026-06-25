from services.rag_services.qdrant_services import search_query
from services.pipeline_services.pipe import pipe_data
from services.db_services.session import init_db
def main():
    init_db()    
    pipe_data()



if __name__ == "__main__":
    main()

