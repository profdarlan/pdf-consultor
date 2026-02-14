# ==========================================
# PDF Consultor - RAPTOR Service
# ==========================================
# Recursive Abstractive Processing for Tree Organized Retrieval
# ==========================================

from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity

from sentence_transformers import SentenceTransformer
from openai import OpenAI

from app.config import settings
from app.models import DocumentMetadata


class RAPTORService:
    """
    Serviço RAPTOR (Recursive Abstractive Processing for Tree Organized Retrieval)

    Cria uma hierarquia de resumos para permitir recuperação eficiente
    em diferentes níveis de detalhe.
    """

    def __init__(self):
        self.embeddings_model = None
        self.llm_client = None
        self.initialized = False

    def initialize(self):
        """Inicializa o serviço RAPTOR"""
        if self.initialized:
            return

        print(f"Inicializando RAPTOR Service...")
        print(f"  Embeddings model: {settings.huggingface_model}")

        # Carregar modelo de embeddings
        self.embeddings_model = SentenceTransformer(
            settings.huggingface_model,
            device=settings.huggingface_device
        )

        # Inicializar cliente OpenAI
        if settings.openai_api_key:
            self.llm_client = OpenAI(api_key=settings.openai_api_key)
        else:
            print("  AVISO: OPENAI_API_KEY não configurada. RAPTOR não funcionará.")

        self.initialized = True
        print("RAPTOR Service inicializado!")

    def cluster_chunks(self, chunks: List[str], n_clusters: int) -> List[List[int]]:
        """
        Agrupa chunks semelhantes usando K-Means

        Args:
            chunks: Lista de textos
            n_clusters: Número de clusters

        Returns:
            Lista de listas, cada uma contendo os índices dos chunks do cluster
        """
        if not self.initialized:
            self.initialize()

        if len(chunks) < n_clusters:
            # Se tem menos chunks que clusters, retorna cada chunk como um cluster
            return [[i] for i in range(len(chunks))]

        # Gerar embeddings
        embeddings = self.embeddings_model.encode(chunks, convert_to_numpy=True)

        # Aplicar K-Means
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(embeddings)

        # Organizar chunks por cluster
        clusters = defaultdict(list)
        for i, label in enumerate(cluster_labels):
            clusters[label].append(i)

        return list(clusters.values())

    def summarize_chunk_group(self, chunks: List[str], context: str = "") -> str:
        """
        Gera um resumo abstrativo para um grupo de chunks usando LLM

        Args:
            chunks: Lista de chunks a serem resumidos
            context: Contexto adicional (opcional)

        Returns:
            Resumo gerado pelo LLM
        """
        if not self.initialized or not self.llm_client:
            # Se não tem LLM, concatena chunks simplesmente
            return " ".join(chunks[:3])

        # Concatenar chunks
        combined_text = "\n\n".join([f"Chunk {i+1}: {chunk}" for i, chunk in enumerate(chunks)])

        prompt = f"""Você é um assistente especializado em resumir documentos.

{context}

Abaixo estão trechos de um documento que devem ser resumidos em um único parágrafo coeso:

{combined_text}

RESUMO:"""

        try:
            response = self.llm_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "Você é um assistente especializado em resumir documentos de forma clara e concisa."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"Erro ao gerar resumo: {e}")
            return " ".join(chunks[:2])

    def build_raptor_tree(self, chunks: List[str],
                         max_depth: int = 3,
                         min_chunks: int = 4) -> Dict[str, Any]:
        """
        Constrói a árvore RAPTOR recursivamente

        Args:
            chunks: Lista de chunks do documento
            max_depth: Profundidade máxima da árvore
            min_chunks: Número mínimo de chunks para criar um cluster

        Returns:
            Dicionário representando a árvore de resumos
        """
        if not self.initialized:
            self.initialize()

        tree = {
            "nodes": [],
            "summaries": {},
            "clusters": {},
            "depth": 0
        }

        # Nível 0: chunks originais
        tree["nodes"] = [{"id": f"chunk_{i}", "text": chunk, "level": 0}
                         for i, chunk in enumerate(chunks)]
        tree["summaries"]["level_0"] = {f"chunk_{i}": chunk for i, chunk in enumerate(chunks)}

        # Construir níveis hierárquicos
        current_chunks = chunks
        current_level = 1

        while current_level <= max_depth and len(current_chunks) >= min_chunks:
            # Determinar número de clusters
            n_clusters = max(2, len(current_chunks) // min_chunks)

            # Agrupar chunks
            clusters = self.cluster_chunks(current_chunks, n_clusters)
            tree["clusters"][f"level_{current_level}"] = clusters

            # Gerar resumos para cada cluster
            summaries = {}
            for cluster_idx, cluster_indices in enumerate(clusters):
                cluster_chunks = [current_chunks[i] for i in cluster_indices]
                summary = self.summarize_chunk_group(cluster_chunks)

                summary_id = f"summary_level{current_level}_cluster{cluster_idx}"
                summaries[summary_id] = summary

                tree["nodes"].append({
                    "id": summary_id,
                    "text": summary,
                    "level": current_level,
                    "children": [f"chunk_{i}" if current_level == 1 else
                                f"summary_level{current_level-1}_cluster{c}"
                                for i, c in enumerate(cluster_indices)]
                })

            tree["summaries"][f"level_{current_level}"] = summaries

            # Usar resumos como chunks para o próximo nível
            current_chunks = list(summaries.values())
            current_level += 1

        tree["depth"] = current_level - 1

        return tree

    def retrieve_from_raptor(self, tree: Dict[str, Any], query: str,
                            top_k: int = 3,
                            target_level: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Recupera chunks/resumos da árvore RAPTOR baseado na query

        Args:
            tree: Árvore RAPTOR
            query: Query do usuário
            top_k: Número de resultados a retornar
            target_level: Nível alvo (None = busca em todos os níveis)

        Returns:
            Lista de chunks/resumos ordenados por relevância
        """
        if not self.initialized:
            self.initialize()

        # Determinar quais níveis buscar
        if target_level is not None:
            levels_to_search = [target_level]
        else:
            # Buscar em todos os níveis
            levels_to_search = list(range(tree["depth"] + 1))

        # Gerar embedding da query
        query_embedding = self.embeddings_model.encode(query, convert_to_numpy=True)

        # Buscar em cada nível
        all_results = []

        for level in levels_to_search:
            level_key = f"level_{level}"
            if level_key not in tree["summaries"]:
                continue

            level_summaries = tree["summaries"][level_key]

            # Gerar embeddings
            summary_ids = list(level_summaries.keys())
            summary_texts = list(level_summaries.values())
            embeddings = self.embeddings_model.encode(summary_texts, convert_to_numpy=True)

            # Calcular similaridade
            similarities = cosine_similarity(
                query_embedding.reshape(1, -1),
                embeddings
            )[0]

            # Adicionar resultados
            for i, (summary_id, similarity) in enumerate(zip(summary_ids, similarities)):
                all_results.append({
                    "id": summary_id,
                    "text": summary_texts[i],
                    "level": level,
                    "score": float(similarity),
                    "type": "summary" if level > 0 else "chunk"
                })

        # Ordenar por relevância
        all_results.sort(key=lambda x: x["score"], reverse=True)

        return all_results[:top_k]

    def get_raptor_summary(self, tree: Dict[str, Any], level: int = -1) -> str:
        """
        Retorna um resumo da árvore RAPTOR

        Args:
            tree: Árvore RAPTOR
            level: Nível desejado (-1 = nível mais alto/resumo final)

        Returns:
            Resumo do nível especificado
        """
        if level == -1:
            level = tree["depth"]

        level_key = f"level_{level}"

        if level_key not in tree["summaries"]:
            return ""

        summaries = tree["summaries"][level_key]

        if not summaries:
            return ""

        # Se tem múltiplos resumos no nível, concatena
        if len(summaries) > 1:
            return "\n\n".join(summaries.values())
        else:
            return list(summaries.values())[0]

    def save_raptor_tree(self, tree: Dict[str, Any], document_id: str):
        """Salva a árvore RAPTOR em disco"""
        import json
        from pathlib import Path

        tree_path = settings.indexes_path / f"raptor_{document_id}.json"

        with open(tree_path, "w", encoding="utf-8") as f:
            json.dump(tree, f, ensure_ascii=False, indent=2)

    def load_raptor_tree(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Carrega a árvore RAPTOR do disco"""
        import json
        from pathlib import Path

        tree_path = settings.indexes_path / f"raptor_{document_id}.json"

        if not tree_path.exists():
            return None

        with open(tree_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def build_and_index_document(self, chunks: List[str], document_id: str) -> Dict[str, Any]:
        """
        Constrói a árvore RAPTOR para um documento e salva

        Args:
            chunks: Lista de chunks do documento
            document_id: ID do documento

        Returns:
            Árvore RAPTOR gerada
        """
        tree = self.build_raptor_tree(
            chunks=chunks,
            max_depth=settings.raptor_max_depth,
            min_chunks=settings.raptor_min_chunks
        )

        self.save_raptor_tree(tree, document_id)

        return tree


# Instância global do serviço RAPTOR
raptor_service = RAPTORService()
