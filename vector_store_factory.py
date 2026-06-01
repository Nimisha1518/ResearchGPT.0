from langchain_chroma import Chroma


def create_vector_store(config, embeddings):
    backend = config.get("VECTOR_BACKEND") if isinstance(config, dict) else config.VECTOR_BACKEND
    pinecone_api_key = config.get("PINECONE_API_KEY") if isinstance(config, dict) else config.PINECONE_API_KEY
    pinecone_index_name = config.get("PINECONE_INDEX_NAME") if isinstance(config, dict) else config.PINECONE_INDEX_NAME
    chroma_db_dir = config.get("CHROMA_DB_DIR") if isinstance(config, dict) else config.CHROMA_DB_DIR

    if backend == "pinecone":
        if not pinecone_api_key or not pinecone_index_name:
            raise RuntimeError("PINECONE_API_KEY and PINECONE_INDEX_NAME are required when VECTOR_BACKEND=pinecone.")

        from langchain_pinecone import PineconeVectorStore

        return PineconeVectorStore(
            index_name=pinecone_index_name,
            embedding=embeddings,
            pinecone_api_key=pinecone_api_key,
        )

    return Chroma(
        persist_directory=chroma_db_dir,
        embedding_function=embeddings
    )
