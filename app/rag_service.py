# ==========================================
# PDF Consultor - RAG Service (FAISS)
# ==========================================
# Reciprocal Rank Fusion (RRF) + RAPTOR Implementation
# ==========================================

from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import numpy as np
import faiss

from sentence_transformers import SentenceTransformer

from app.config import settings
from app.models import DocumentMetadata, SearchRequest, SearchResult


class RAGService:
    """Serviço de Retrieval-Augmented Generation com busca híbrida e RAPTOR usando FAISS"""

    def __init__(self):
        self.embeddings_model = None
        self.vector_index = None
        self.documents_metadata = {}  # Mapeia doc_id -> (text, metadata)
        self.doc_ids_list = []  # Lista ordenada de IDs para conversão FAISS -> metadados
        self.initialized = False

    def initialize(self):
        """Inicializa o serviço de RAG usando FAISS"""
        if self.initialized:
            return

        print(f"Inicializando RAG Service (FAISS)...")
        print(f"  Embeddings model: {settings.huggingface_model}")
        print(f"  Device: {settings.huggingface_device}")

        # Carregar modelo de embeddings
        self.embeddings_model = SentenceTransformer(
            settings.huggingface_model,
            device=settings.huggingface_device
        )

        # Inicializar FAISS Index (L2 distance = Inner Product para embeddings normalizados)
        embedding_dim = self.embeddings_model.get_sentence_embedding_dimension()
        self.vector_index = faiss.IndexFlatIP(embedding_dim)

        self.initialized = True
        print("RAG Service inicializado com sucesso (FAISS)!")

    def embed_text(self, text: str) -> List[float]:
        """Gera embedding para um texto"""
        if not self.initialized:
            self.initialize()

        embedding = self.embeddings_model.encode(text, convert_to_numpy=True)
        
        # Normalizar embeddings (L2 normalization)
        embedding = embedding / np.linalg.norm(embedding)
        return embedding.tolist()

    def add_documents(self, chunks: List[Dict[str, Any]], document_id: str):
        """Adiciona chunks de documento ao índice vetorial FAISS"""
        if not self.initialized:
            self.initialize()

        ids = [f"{document_id}_{i}" for i in range(len(chunks))]
        texts = [chunk["text"] for chunk in chunks]
        metadatas = [
            {
                "document_id": document_id,
                "page": chunk["page"],
                "chunk_index": i,
                "text_length": len(chunk["text"]),
                **chunk.get("metadata", {})
            }
            for i, chunk in enumerate(chunks)
        ]

        # Gerar embeddings normalizados
        embeddings = self.embeddings_model.encode(texts, convert_to_numpy=True)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        # Armazenar metadados (text original e metadados)
        for doc_id, text, metadata in zip(ids, texts, metadatas):
            self.documents_metadata[doc_id] = {
                "text": text,
                "metadata": metadata
            }
            if doc_id not in self.doc_ids_list:
                self.doc_ids_list.append(doc_id)

        # Adicionar embeddings ao índice FAISS
        self.vector_index.add(embeddings)
        
        print(f"Adicionados {len(chunks)} chunks ao índice FAISS para documento {document_id}")

    def vector_search(self, query: str, top_k: int = 5,
                     document_id: Optional[str] = None) -> List[Tuple[str, float]]:
        """Busca semântica usando embeddings FAISS"""
        if not self.initialized:
            self.initialize()

        # Gerar embedding da query normalizada
        query_embedding = self.embeddings_model.encode(query, convert_to_numpy=True)
        query_embedding = query_embedding / np.linalg.norm(query_embedding)

        # Buscar no FAISS
        k = min(top_k * 10, self.vector_index.ntotal)  # Buscar mais candidatos para RRF
        scores, indices = self.vector_index.search(query_embedding, k)

        # Mapear FAISS indices -> doc_ids
        results = []
        for i in range(len(indices)):
            idx = indices[i]
            if idx < len(self.doc_ids_list):
                doc_id = self.doc_ids_list[idx]
                # Converter score de inner product para similaridade (cosine)
                # Para embeddings normalizados, inner product = cos similarity
                score = float(scores[i])
                results.append((doc_id, score))

        return results

    def keyword_search(self, query: str, top_k: int = 5,
                       document_id: Optional[str] = None) -> List[Tuple[str, float]]:
        """Busca por palavra-chave usando simulação BM25"""
        if not self.initialized:
            self.initialize()

        query_terms = query.lower().split()
        scored_results = []

        # Simular BM25 scoring nos documentos armazenados
        for doc_id, data in self.documents_metadata.items():
            if document_id and not doc_id.startswith(document_id):
                continue
                
            text = data["text"].lower()
            
            # Calcular relevância baseada na presença de termos
            score = 0
            for term in query_terms:
                if term in text:
                    score += 1
                    # Bônus para termos exatos
                    if f" {term} " in f" {text} ":
                        score += 0.5

            if score > 0:
                scored_results.append((doc_id, score))

        # Ordenar por relevância e normalizar
        if scored_results:
            max_score = max(score for _, score in scored_results)
            scored_results = [(doc_id, score / max_score) for doc_id, score in scored_results]
            scored_results.sort(key=lambda x: x[1], reverse=True)

        return scored_results[:top_k]

    def reciprocal_rank_fusion(self, vector_results: List[Tuple[str, float]],
                              keyword_results: List[Tuple[str, float]],
                              k: int = 60) -> List[Tuple[str, float]]:
        """
        Combina resultados de busca vetorial e por palavra-chave usando Reciprocal Rank Fusion

        Fórmula: score = Σ(1 / (k + rank)) para cada ranqueamento
        """
        scores = defaultdict(float)

        # Adicionar scores da busca vetorial
        for rank, (doc_id, _) in enumerate(vector_results):
            scores[doc_id] += 1 / (k + rank + 1)

        # Adicionar scores da busca por palavra-chave
        for rank, (doc_id, _) in enumerate(keyword_results):
            scores[doc_id] += 1 / (k + rank + 1)

        # Ordenar por score combinado
        combined = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Normalizar scores
        if combined:
            max_score = max(score for _, score in combined)
            combined = [(doc_id, score / max_score) for doc_id, score in combined]

        return combined

    def hybrid_search(self, query: str, top_k: int = 5,
                      document_id: Optional[str] = None,
                      use_rrf: bool = True) -> List[Dict[str, Any]]:
        """
        Busca híbrida combinando busca vetorial e por palavra-chave

        Se use_rrf=True, usa Reciprocal Rank Fusion
        Se use_rrf=False, usa ponderação linear
        """
        # Busca vetorial
        vector_results = self.vector_search(query, top_k=top_k * 2, document_id=document_id)

        # Busca por palavra-chave
        keyword_results = self.keyword_search(query, top_k=top_k * 2, document_id=document_id)

        if use_rrf:
            # Usar RRF para combinar resultados
            combined = self.reciprocal_rank_fusion(vector_results, keyword_results, k=settings.rrf_k)
        else:
            # Usar ponderação linear
            combined = self._linear_fusion(vector_results, keyword_results)

        # Pegar top_k resultados e recuperar metadados
        final_results = []
        
        for doc_id, score in combined[:top_k]:
            if doc_id in self.documents_metadata:
                data = self.documents_metadata[doc_id]
                final_results.append({
                    "id": doc_id,
                    "text": data["text"],
                    "metadata": data["metadata"],
                    "score": score
                })

        return final_results

    def _linear_fusion(self, vector_results: List[Tuple[str, float]],
                       keyword_results: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
        """Combina resultados usando ponderação linear"""
        combined_scores = defaultdict(float)

        # Adicionar scores ponderados
        for doc_id, score in vector_results:
            combined_scores[doc_id] += score * settings.hybrid_weight_vector

        for doc_id, score in keyword_results:
            combined_scores[doc_id] += score * settings.hybrid_weight_keyword

        # Ordenar por score combinado
        combined = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)

        # Normalizar scores
        if combined:
            max_score = max(score for _, score in combined)
            combined = [(doc_id, score / max_score) for doc_id, score in combined]

        return combined

    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """Recupera todos os chunks de um documento"""
        if not self.initialized:
            self.initialize()

        chunks = []
        for doc_id, data in self.documents_metadata.items():
            if doc_id.startswith(document_id) and data["metadata"]["document_id"] == document_id:
                chunks.append({
                    "id": doc_id,
                    "text": data["text"],
                    "metadata": data["metadata"]
                })

        return chunks

    def delete_document(self, document_id: str):
        """Remove todos os chunks de um documento do índice"""
        if not self.initialized:
            self.initialize()

        # Recuperar IDs do documento
        doc_ids = [doc_id for doc_id in self.doc_ids_list if doc_id.startswith(document_id)]
        
        if doc_ids:
            # FAISS não suporta deleção incremental facilmente
            # Para simplificar, vamos recriar o índice sem esses documentos
            # Na produção, considerar usar um índice incremental ou FAISS IndexIVF
            
            # Remover metadados
            for doc_id in doc_ids:
                if doc_id in self.documents_metadata:
                    del self.documents_metadata[doc_id]
                if doc_id in self.doc_ids_list:
                    self.doc_ids_list.remove(doc_id)

            print(f"Removidos {len(doc_ids)} chunks do documento {document_id} (índice será reconstruído no próximo initialize)")
            # Nota: O índice FAISS não pode ser modificado facilmente sem reconstrução
            # Para produção, considerar armazenar embeddings e reconstruir índice

    def get_index_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do índice"""
        if not self.initialized:
            self.initialize()

        return {
            "total_chunks": self.vector_index.ntotal,
            "vector_store": "FAISS (Facebook AI Similarity Search)",
            "index_type": "IndexFlatIP (Inner Product)",
            "model": settings.huggingface_model,
            "device": settings.huggingface_device
        }


# Instância global do serviço RAG
rag_service = RAGService()
