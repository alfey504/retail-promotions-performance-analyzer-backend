from rag_services.qdrant_services import search_query
def main():
    texts = search_query("Summer sales")  
    print(len(texts)) 
    
    return


if __name__ == "__main__":
    main()

