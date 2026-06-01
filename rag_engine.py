import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from vector_store_factory import create_vector_store

class ResearchPaperRAG:
    def __init__(self, config, gemini_api_key=None):
        self.config = config
        self.gemini_api_key = gemini_api_key
        
        print("Initializing Embeddings model (sentence-transformers/all-MiniLM-L6-v2)...")
        # Load HuggingFace embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        vector_backend = self.config.get("VECTOR_BACKEND") if isinstance(self.config, dict) else self.config.VECTOR_BACKEND
        print(f"Initializing vector store backend: {vector_backend}")
        self.vector_store = create_vector_store(self.config, self.embeddings)

    @classmethod
    def from_config(cls, config):
        return cls(config, gemini_api_key=config.get("GEMINI_API_KEY") if isinstance(config, dict) else config.GEMINI_API_KEY)

    def process_pdf(self, file_path, document_id=None, user_id=None, source_filename=None):
        """
        Loads a PDF file, splits it into chunks, and stores them in ChromaDB.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        filename = source_filename or os.path.basename(file_path)
        print(f"Loading and processing PDF: {filename}...")
        
        # Load PDF using PyPDFLoader
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        
        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = text_splitter.split_documents(docs)
        
        # Add metadata and ensure file identification
        for chunk in chunks:
            chunk.metadata["source"] = filename
            chunk.metadata["filename"] = filename
            if document_id is not None:
                chunk.metadata["document_id"] = document_id
            if user_id is not None:
                chunk.metadata["user_id"] = user_id
            
        # Add to vector store
        self.vector_store.add_documents(chunks)
        print(f"Successfully processed {filename}. Ingested {len(chunks)} chunks into vector store.")
        return len(chunks)

    def _build_filter(self, user_id=None, filename=None, document_id=None):
        filters = []
        if user_id is not None:
            filters.append({"user_id": user_id})
        if filename:
            filters.append({"source": filename})
        if document_id is not None:
            filters.append({"document_id": document_id})

        if len(filters) == 1:
            return filters[0]
        if len(filters) > 1:
            return {"$and": filters}
        return None

    def delete_paper(self, filename=None, user_id=None, document_id=None):
        """
        Deletes all chunks associated with a specific filename from ChromaDB.
        """
        print(f"Deleting paper '{filename or document_id}' from vector store...")
        try:
            where_filter = self._build_filter(user_id=user_id, filename=filename, document_id=document_id)
            vector_backend = self.config.get("VECTOR_BACKEND") if isinstance(self.config, dict) else self.config.VECTOR_BACKEND
            if vector_backend == "pinecone":
                self.vector_store.delete(filter=where_filter)
            else:
                self.vector_store.delete(where=where_filter)
            print(f"Successfully deleted '{filename or document_id}' from vector store.")
            return True
        except Exception as e:
            print(f"Error deleting paper from vector store: {e}")
            raise e

    def retrieve_relevant_chunks(self, query, filter_filename=None, top_k=5, user_id=None):
        """
        Retrieves top K chunks matching the query. Optional filter by filename.
        """
        search_filter = self._build_filter(user_id=user_id, filename=filter_filename)
        
        # Perform similarity search with scores
        results = self.vector_store.similarity_search_with_relevance_scores(
            query, 
            k=top_k, 
            filter=search_filter
        )
        return results

    def generate_standalone_query(self, query, chat_history):
        """
        Rephrases follow-up queries using chat history to make them standalone.
        """
        if not chat_history:
            return query
            
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set.")

        # Format chat history
        history_str = ""
        for role, msg in chat_history:
            history_str += f"{role.capitalize()}: {msg}\n"
            
        prompt = f"""Given the following conversation and a follow-up question, rephrase the follow-up question to be a standalone question, in its original language, that contains all necessary context from the conversation. Do not answer the question, just return the rephrased standalone question.

Chat History:
{history_str}
Follow-up Question: {query}
Standalone Question:"""

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", 
            google_api_key=self.gemini_api_key, 
            temperature=0
        )
        response = llm.invoke(prompt)
        return response.content.strip()

    def answer_query(self, query, chat_history, filter_filename=None, user_id=None):
        """
        Answers a user query based on relevant document context.
        """
        if not self.gemini_api_key:
            return {
                "answer": "Error: Gemini API Key is missing. Please set GEMINI_API_KEY in your .env file.",
                "sources": [],
                "standalone_query": query
            }

        # 1. Generate a standalone query incorporating chat context
        try:
            standalone_query = self.generate_standalone_query(query, chat_history)
        except Exception as e:
            print(f"Error generating standalone query: {e}")
            standalone_query = query
            
        # 2. Retrieve relevant chunks from ChromaDB
        try:
            results = self.retrieve_relevant_chunks(standalone_query, filter_filename, top_k=5, user_id=user_id)
        except Exception as e:
            print(f"Error retrieving from ChromaDB: {e}")
            return {
                "answer": f"Error searching the vector database: {str(e)}",
                "sources": [],
                "standalone_query": standalone_query
            }

        # 3. Structure retrieved passages and sources
        context_str = ""
        sources = []
        
        for idx, (doc, score) in enumerate(results):
            page = doc.metadata.get("page", 0) + 1  # Make page 1-indexed
            filename = doc.metadata.get("source", "Unknown")
            content = doc.page_content
            
            context_str += f"--- Context Chunk {idx+1} (Source: {filename}, Page: {page}) ---\n{content}\n\n"
            sources.append({
                "chunk_index": idx + 1,
                "filename": filename,
                "page": page,
                "content": content,
                "score": float(score) if score is not None else 0.0
            })

        # If no context found
        if not sources:
            return {
                "answer": "No relevant context was found in the uploaded research papers. Please upload documents first or ask a question related to the uploaded papers.",
                "sources": [],
                "standalone_query": standalone_query
            }

        # 4. Formulate the prompt
        recent_history = chat_history[-6:] if chat_history else []
        history_str = "\n".join([f"{role.capitalize()}: {msg}" for role, msg in recent_history])
        
        prompt = f"""You are an elite AI Research Assistant. Your goal is to help the user understand research papers.
Answer the user's question as accurately, professionally, and concisely as possible based ONLY on the retrieved contexts below.
If the information to answer the question is not present in the provided context, state clearly that the answer cannot be found in the uploaded papers. Do not make up facts.

When answering, reference the source chunks by inserting citations like [1], [2], etc., matching the Context Chunk indices provided.

Uploaded Paper Contexts:
{context_str}

Recent Chat History (if any):
{history_str}

User Question: {query}

AI Answer:"""

        # 5. Get response from Gemini
        try:
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash", 
                google_api_key=self.gemini_api_key, 
                temperature=0.2
            )
            response = llm.invoke(prompt)
            answer_text = response.content
        except Exception as e:
            answer_text = f"Error generating response from Gemini API: {str(e)}"

        return {
            "answer": answer_text,
            "sources": sources,
            "standalone_query": standalone_query
        }

    def summarize_paper(self, filename, user_id=None):
        """
        Generates a summary of the paper by pulling sample chunks (beginning and end).
        """
        if not self.gemini_api_key:
            return "Error: Gemini API Key is missing. Please set GEMINI_API_KEY in your .env file."

        try:
            # Query all chunks from the vector store matching filename
            where_filter = self._build_filter(user_id=user_id, filename=filename)
            vector_backend = self.config.get("VECTOR_BACKEND") if isinstance(self.config, dict) else self.config.VECTOR_BACKEND
            if vector_backend != "pinecone" and hasattr(self.vector_store, "get"):
                results = self.vector_store.get(where=where_filter)
                docs = results.get("documents", []) if results else []
                metadatas = results.get("metadatas", []) if results else []
            else:
                matches = self.retrieve_relevant_chunks(
                    "abstract introduction methodology results findings conclusion",
                    filter_filename=filename,
                    top_k=8,
                    user_id=user_id,
                )
                docs = [doc.page_content for doc, _score in matches]
                metadatas = [doc.metadata for doc, _score in matches]

            if not docs:
                return "No content found for this file. Please make sure it was uploaded and processed correctly."
            
            # Zip and sort by page number
            zipped = list(zip(docs, metadatas))
            zipped.sort(key=lambda x: x[1].get("page", 0))
            
            # Select key chunks (up to 8)
            selected_chunks = []
            n = len(zipped)
            if n <= 8:
                selected_chunks = zipped
            else:
                # 4 from start (Intro/Abstract)
                selected_chunks.extend(zipped[:4])
                # 4 from end (Conclusion/References)
                selected_chunks.extend(zipped[-4:])
                
            summary_context = ""
            for doc, meta in selected_chunks:
                page = meta.get("page", 0) + 1
                summary_context += f"[Page {page} Chunk]\n{doc}\n\n"
                
            prompt = f"""You are an elite AI Research Assistant. Below are selected passages from the research paper "{filename}".
Please generate a comprehensive, highly-structured executive summary of this paper.
Your summary should include:
1. **Title & Overview**: Brief summary of the paper's core objective.
2. **Key Methodology**: How the research was conducted.
3. **Major Findings & Results**: Core discoveries.
4. **Conclusion & Significance**: Why this paper matters and its implications.

Passages from the paper:
{summary_context}

Structured Summary:"""

            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash", 
                google_api_key=self.gemini_api_key, 
                temperature=0.3
            )
            response = llm.invoke(prompt)
            return response.content
        except Exception as e:
            return f"Error generating summary: {str(e)}"

    def semantic_search(self, query, filter_filename=None, top_k=5, user_id=None):
        """
        Runs similarity search and returns a serializable list of matches.
        """
        try:
            results = self.retrieve_relevant_chunks(query, filter_filename, top_k, user_id=user_id)
            formatted_results = []
            for doc, score in results:
                formatted_results.append({
                    "filename": doc.metadata.get("source", "Unknown"),
                    "page": doc.metadata.get("page", 0) + 1,
                    "content": doc.page_content,
                    "score": float(score) if score is not None else 0.0
                })
            return formatted_results
        except Exception as e:
            print(f"Error in semantic search: {e}")
            raise e
