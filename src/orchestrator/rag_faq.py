"""
RAG (Retrieval-Augmented Generation) module for FAQ handling.
Uses OpenAI embeddings and ChromaDB for semantic search and retrieval.
"""

import os
import csv
import json
import numpy as np
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from openai import OpenAI
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv

load_dotenv()

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Thiếu OPENAI_API_KEY (đặt env hoặc .env).")

oai_client = OpenAI(api_key=OPENAI_API_KEY)
EMBEDDING_MODEL = "text-embedding-3-small"

# ChromaDB configuration
CHROMA_DB_PATH = "src/data/chroma_db"
COLLECTION_NAME = "faq_embeddings"
# Default faq path after src/ move
DEFAULT_FAQ_PATH = (Path(__file__).resolve().parents[1] / "data" / "faq_data.csv").as_posix()

class FAQRAG:
    """RAG system for FAQ retrieval and generation using ChromaDB."""
    
    def __init__(self, faq_csv_path: str = None):
        self.faq_csv_path = faq_csv_path or DEFAULT_FAQ_PATH
        self.faq_data: List[Dict[str, str]] = []
        self.client = None
        self.collection = None
        self.initialize_chromadb()
        self.load_faq_data()
        self.setup_embeddings()
    
    def initialize_chromadb(self):
        """Initialize ChromaDB client and collection."""
        try:
            # Create ChromaDB client with persistent storage
            self.client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(name=COLLECTION_NAME)
                print(f"✅ Connected to existing ChromaDB collection: {COLLECTION_NAME}")
            except Exception:
                # Collection doesn't exist, create it
                self.collection = self.client.create_collection(
                    name=COLLECTION_NAME,
                    metadata={"description": "FAQ embeddings for Vexere chatbot"}
                )
                print(f"✅ Created new ChromaDB collection: {COLLECTION_NAME}")
                
        except Exception as e:
            print(f"❌ Error initializing ChromaDB: {str(e)}")
            raise
    
    def load_faq_data(self):
        """Load FAQ data from CSV file."""
        try:
            candidates = [
                self.faq_csv_path,
                "src/data/faq_data.csv",
                "faq_data.csv",
            ]
            csv_path = None
            for p in candidates:
                if p and os.path.exists(p):
                    csv_path = p
                    break
            if not csv_path:
                raise FileNotFoundError(f"FAQ file not found. Tried: {candidates}")
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                self.faq_data = list(reader)
            print(f"✅ Loaded {len(self.faq_data)} FAQ entries from {csv_path}")
        except FileNotFoundError:
            print(f"❌ FAQ file not found: {self.faq_csv_path}")
            self.faq_data = []
        except Exception as e:
            print(f"❌ Error loading FAQ data: {str(e)}")
            self.faq_data = []
    
    def setup_embeddings(self):
        """Setup embeddings in ChromaDB (generate if not exists)."""
        if not self.faq_data:
            return
        
        try:
            # Check if collection has data
            count = self.collection.count()
            
            if count == 0:
                print("🔄 No embeddings found in ChromaDB. Generating new embeddings...")
                self.generate_and_store_embeddings()
            else:
                print(f"✅ Found {count} existing embeddings in ChromaDB")
                
        except Exception as e:
            print(f"❌ Error setting up embeddings: {str(e)}")
            # Fallback: generate embeddings
            self.generate_and_store_embeddings()
    
    def generate_and_store_embeddings(self):
        """Generate embeddings and store them in ChromaDB."""
        if not self.faq_data:
            return
        
        print("🔄 Generating and storing embeddings in ChromaDB...")
        
        # Prepare data for ChromaDB - combine question and answer for better retrieval
        questions = [item['question'] for item in self.faq_data]
        answers = [item['answer'] for item in self.faq_data]
        
        # Create combined text for embedding (question + answer)
        combined_texts = []
        for i, (question, answer) in enumerate(zip(questions, answers)):
            # Combine question and answer for better semantic understanding
            combined_text = f"{question}\n\n{answer}"
            combined_texts.append(combined_text)
        
        ids = [f"faq_{i}" for i in range(len(self.faq_data))]
        
        try:
            # Generate embeddings in batches
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(combined_texts), batch_size):
                batch_texts = combined_texts[i:i + batch_size]
                
                response = oai_client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=batch_texts
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
            
            # Store in ChromaDB
            self.collection.add(
                embeddings=all_embeddings,
                documents=combined_texts,  # Store combined text for better retrieval
                metadatas=[{
                    "question": question, 
                    "answer": answer, 
                    "index": i,
                    "type": "faq"
                } for i, (question, answer) in enumerate(zip(questions, answers))],
                ids=ids
            )
            
            print(f"✅ Generated and stored {len(all_embeddings)} embeddings in ChromaDB")
            print(f"   - Each embedding covers: question + answer")
            
        except Exception as e:
            print(f"❌ Error generating and storing embeddings: {str(e)}")
            raise
    
    def get_question_embedding(self, question: str) -> List[float]:
        """Get embedding for a single question."""
        try:
            response = oai_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=[question]
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"❌ Error getting question embedding: {str(e)}")
            return []
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0
            
            return dot_product / (norm1 * norm2)
        except Exception as e:
            print(f"❌ Error calculating cosine similarity: {str(e)}")
            return 0
    
    def search_similar_questions(self, query: str, top_k: int = 3) -> List[Dict[str, any]]:
        """Search for similar questions using ChromaDB semantic search."""
        if not self.collection:
            return []
        
        try:
            # Get query embedding
            query_embedding = self.get_question_embedding(query)
            if not query_embedding:
                return []
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            similarities = []
            if results['documents'] and results['documents'][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    # Convert distance to similarity (ChromaDB uses cosine distance)
                    similarity = 1 - distance
                    similarities.append({
                        'index': i,
                        'similarity': similarity,
                        'question': metadata['question'],  # Get original question from metadata
                        'answer': metadata['answer'],      # Get original answer from metadata
                        'combined_text': doc               # Full combined text that was embedded
                    })
            
            return similarities
            
        except Exception as e:
            print(f"❌ Error searching similar questions: {str(e)}")
            return []
    
    def get_faq_response(self, query: str, similarity_threshold: float = 0.7) -> Optional[Dict[str, str]]:
        """Get FAQ response for a query."""
        similar_questions = self.search_similar_questions(query, top_k=1)
        
        if not similar_questions:
            return None
        
        best_match = similar_questions[0]
        
        # Only return if similarity is above threshold
        if best_match['similarity'] >= similarity_threshold:
            return {
                'question': best_match['question'],
                'answer': best_match['answer'],
                'similarity': best_match['similarity']
            }
        
        return None
    
    def get_contextual_response(self, query: str, top_k: int = 3) -> str:
        """Get contextual response using multiple similar questions."""
        similar_questions = self.search_similar_questions(query, top_k=top_k)
        
        if not similar_questions:
            return "Xin lỗi, tôi không tìm thấy thông tin liên quan đến câu hỏi của bạn trong cơ sở dữ liệu FAQ."
        
        # If we have a very good match, return it directly
        if similar_questions[0]['similarity'] >= 0.7:
            return similar_questions[0]['answer']
        
        # If we have a reasonable match, return it with context
        if similar_questions[0]['similarity'] >= 0.3:
            best_match = similar_questions[0]
            context = f"**{best_match['question']}**\n\n{best_match['answer']}\n\n"
            
            # Add additional matches if they're reasonably similar
            for match in similar_questions[1:3]:  # Show up to 2 additional matches
                if match['similarity'] >= 0.2:  # Very low threshold for additional context
                    context += f"**{match['question']}**\n{match['answer']}\n\n"
            
            context += "Nếu câu hỏi của bạn không được giải đáp ở trên, vui lòng liên hệ tổng đài 1900 6484 để được hỗ trợ trực tiếp."
            return context
        
        # Otherwise, provide a contextual response
        context = "Dựa trên câu hỏi của bạn, tôi tìm thấy một số thông tin liên quan:\n\n"
        
        for i, match in enumerate(similar_questions, 1):
            if match['similarity'] >= 0.2:  # Very low threshold for more matches
                context += f"{i}. **{match['question']}**\n"
                context += f"{match['answer']}\n\n"
        
        context += "Nếu câu hỏi của bạn không được giải đáp ở trên, vui lòng liên hệ tổng đài 1900 6484 để được hỗ trợ trực tiếp."
        
        return context

# Global FAQ RAG instance
faq_rag = FAQRAG()

def get_faq_response(query: str) -> Optional[str]:
    """Get FAQ response for a query."""
    response = faq_rag.get_faq_response(query)
    if response:
        return response['answer']
    return None

def get_contextual_faq_response(query: str) -> str:
    """Get contextual FAQ response for a query."""
    return faq_rag.get_contextual_response(query)

def reset_chromadb():
    """Reset ChromaDB collection (useful for testing)."""
    try:
        faq_rag.client.delete_collection(COLLECTION_NAME)
        print("✅ ChromaDB collection reset successfully")
    except Exception as e:
        print(f"❌ Error resetting ChromaDB: {str(e)}")

def get_collection_info():
    """Get information about the ChromaDB collection."""
    try:
        count = faq_rag.collection.count()
        print(f"📊 ChromaDB Collection Info:")
        print(f"   - Collection: {COLLECTION_NAME}")
        print(f"   - Total documents: {count}")
        print(f"   - Database path: {CHROMA_DB_PATH}")
    except Exception as e:
        print(f"❌ Error getting collection info: {str(e)}")
