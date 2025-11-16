"""
Conversation History Manager with RAG-based Vector Storage
Stores conversation history and retrieves relevant context using embeddings
"""
import os
import json
from datetime import datetime
from typing import List, Dict, Optional

import faiss
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


class ConversationManager:
    def __init__(self, persist_directory: str = "./data/faiss_db"):
        """Initialize conversation manager with vector storage"""
        self.persist_directory = persist_directory
        self.index_path = os.path.join(persist_directory, "index")
        
        # Initialize Ollama embeddings (runs locally)
        self.embeddings = OllamaEmbeddings(
            model="embeddinggemma:latest",  # Fast, efficient embedding model
            base_url="http://localhost:11434"  # Default Ollama URL
        )
        
        # Initialize or load FAISS vector store
        os.makedirs(persist_directory, exist_ok=True)
        
        if os.path.exists(self.index_path):
            # Load existing index
            self.vectorstore = FAISS.load_local(
                self.index_path,
                self.embeddings,
                allow_dangerous_deserialization=True
            )
        else:
            # Create new empty index with a dummy document
            dummy_doc = Document(page_content="Initial document", metadata={})
            self.vectorstore = FAISS.from_documents([dummy_doc], self.embeddings)
        
        # In-memory conversation history (for current session)
        self.current_session: List[Dict] = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def add_interaction(
        self,
        goal: str,
        target_url: str,
        dom_structure: Dict,
        action_plan: Dict,
        result: Optional[Dict] = None
    ):
        """Add a user interaction to history and vector storage"""
        
        interaction = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "goal": goal,
            "target_url": target_url,
            "action_plan": action_plan,
            "result": result,
            "success": result.get("success") if result else None
        }
        
        # Add to current session
        self.current_session.append(interaction)
        
        # Create document for vector storage
        # Combine relevant information for embedding
        content = f"""
Goal: {goal}
URL: {target_url}
Actions: {len(action_plan.get('actions', []))} steps
Action Types: {', '.join([a.get('type') for a in action_plan.get('actions', [])])}
Success: {result.get('success') if result else 'Unknown'}

Action Details:
{json.dumps(action_plan, indent=2)}
"""
        
        metadata = {
            "session_id": self.session_id,
            "timestamp": interaction["timestamp"],
            "goal": goal,
            "target_url": target_url,
            "num_actions": len(action_plan.get('actions', [])),
            "success": str(result.get("success")) if result else "unknown"
        }
        
        doc = Document(page_content=content, metadata=metadata)
        
        # Add to vector store
        self.vectorstore.add_documents([doc])
        
        # Save the index to disk
        self.vectorstore.save_local(self.index_path)
    
    def get_relevant_context(
        self, 
        goal: str, 
        target_url: str = "",
        k: int = 3
    ) -> List[Dict]:
        """Retrieve relevant past interactions using similarity search"""
        
        query = f"Goal: {goal}\nURL: {target_url}"
        
        # Search for similar interactions
        # Note: FAISS doesn't support metadata filtering, so we get all results
        results = self.vectorstore.similarity_search_with_score(
            query=query,
            k=k * 2  # Get more results to filter
        )
        
        relevant_context = []
        for doc, score in results:
            # Filter for successful ones if we have target_url
            if target_url and doc.metadata.get("success") != "True":
                continue
            
            relevant_context.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "similarity_score": float(score)
            })
            
            # Stop once we have k results
            if len(relevant_context) >= k:
                break
        
        return relevant_context
    
    def get_session_history(self) -> List[Dict]:
        """Get all interactions from current session"""
        return self.current_session
    
    def format_context_for_prompt(self, relevant_context: List[Dict]) -> str:
        """Format retrieved context for inclusion in LLM prompt"""
        if not relevant_context:
            return ""
        
        formatted = "\n\n=== RELEVANT PAST INTERACTIONS ===\n"
        formatted += "Here are similar tasks you've successfully completed before:\n\n"
        
        for i, ctx in enumerate(relevant_context, 1):
            formatted += f"--- Example {i} (Similarity: {ctx['similarity_score']:.2f}) ---\n"
            formatted += ctx['content']
            formatted += "\n"
        
        return formatted
    
    def clear_session(self):
        """Clear current session history"""
        self.current_session = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def get_statistics(self) -> Dict:
        """Get statistics about stored interactions"""
        # Get all documents from FAISS
        try:
            # FAISS stores documents differently, use docstore
            total_interactions = len(self.vectorstore.docstore._dict)
            
            # Count successes
            successes = sum(
                1 for doc in self.vectorstore.docstore._dict.values()
                if doc.metadata.get('success') == 'True'
            )
        except:
            total_interactions = 0
            successes = 0
        
        return {
            "total_interactions": total_interactions,
            "successful_interactions": successes,
            "current_session_length": len(self.current_session),
            "session_id": self.session_id
        }
