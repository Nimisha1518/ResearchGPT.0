import os
from dotenv import load_dotenv
load_dotenv(override=True)

from config import Config
from rag_engine import ResearchPaperRAG

def test_rag():
    print("Testing RAG Initialization...")
    rag = ResearchPaperRAG(
        chroma_db_dir=Config.CHROMA_DB_DIR,
        gemini_api_key=os.getenv("GEMINI_API_KEY")
    )
    print("\nInitialization successful.")
    
    print("\nTesting simple Gemini API response...")
    response = rag.answer_query("Hello, how are you?", [])
    print("\nResponse from API:")
    print(response)

if __name__ == "__main__":
    test_rag()
