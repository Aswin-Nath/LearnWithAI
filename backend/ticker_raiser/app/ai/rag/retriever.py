import os
from typing import List
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
import app
PERSIST_DIR = os.path.join(
    os.path.dirname(os.path.abspath(app.__file__)),
    "chroma_db"
)
class ChromaRetriever:
    """Handles all semantic retrieval from persistent Chroma store."""
    
    def __init__(self):
        self.persist_dir =PERSIST_DIR
        print(f"🔗 RAG Layer connecting to DB at: {self.persist_dir}")
        
        self.embeddings = HuggingFaceEmbeddings(model_name="all-mpnet-base-v2")
        self.problem_collections = {}
    
    def _get_collection(self, problem_id: int):
        """Get or load a problem's Chroma collection."""
        if problem_id not in self.problem_collections:
            collection_name = f"problem_{problem_id}"
            self.problem_collections[problem_id] = Chroma(
                collection_name=collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_dir
            )
        return self.problem_collections[problem_id]
    
    def retrieve(self, problem_id: int, query: str, k: int = 5) -> List[dict]:
        """
        Retrieve top-k most relevant chunks for a query.
        
        Args:
            problem_id: Problem ID to search within
            query: User query or code to search for
            k: Number of results to return
            
        Returns:
            List of dicts with keys: content, section, distance
        """
        try:
            collection = self._get_collection(problem_id)
            results = collection.similarity_search_with_score(query, k=k)
            
            chunks = []
            for doc, distance in results:
                chunks.append({
                    "content": doc.page_content,
                    "section": doc.metadata.get("section", "Unknown"),
                    "distance": distance,
                    "problem_id": problem_id
                })
            return chunks
        except Exception as e:
            print(f"Retrieval error: {e}")
            return []

retriever = ChromaRetriever()
