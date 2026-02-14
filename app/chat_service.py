# ==========================================
# PDF Consultor - Chat Service
# ==========================================

from typing import List, Dict, Any, Optional
import tiktoken

from openai import OpenAI

from app.config import settings
from app.models import ChatMessage, ChatResponse
from app.rag_service import rag_service
from app.raptor_service import raptor_service


class ChatService:
    """Serviço de chat com RAG e RAPTOR"""

    def __init__(self):
        self.llm_client = None
        self.encoding = None
        self.initialized = False

    def initialize(self):
        """Inicializa o serviço de chat"""
        if self.initialized:
            return

        print(f"Inicializando Chat Service...")

        # Inicializar cliente OpenAI
        if settings.openai_api_key:
            self.llm_client = OpenAI(api_key=settings.openai_api_key)
        else:
            print("  AVISO: OPENAI_API_KEY não configurada.")

        # Inicializar tokenizer
        self.encoding = tiktoken.encoding_for_model(settings.openai_model)

        self.initialized = True
        print("Chat Service inicializado!")

    def count_tokens(self, text: str) -> int:
        """Conta tokens em um texto"""
        if not self.encoding:
            self.encoding = tiktoken.encoding_for_model(settings.openai_model)

        return len(self.encoding.encode(text))

    def build_context(self, query: str, chunks: List[Dict[str, Any]],
                     use_raptor: bool, raptor_tree: Optional[Dict[str, Any]] = None) -> str:
        """
        Constrói o contexto para o LLM baseado nos chunks recuperados

        Args:
            query: Query do usuário
            chunks: Chunks recuperados
            use_raptor: Se deve usar RAPTOR
            raptor_tree: Árvore RAPTOR (se aplicável)

        Returns:
            Contexto formatado para o LLM
        """
        context_parts = []

        # Se usar RAPTOR, adicionar resumo do nível mais alto
        if use_raptor and raptor_tree:
            raptor_summary = raptor_service.get_raptor_summary(raptor_tree, level=-1)

            if raptor_summary:
                context_parts.append(f"RESUMO EXECUTIVO DO DOCUMENTO:\n{raptor_summary}\n")

        # Adicionar chunks relevantes
        context_parts.append("TRECHOS RELEVANTES:\n")

        for i, chunk in enumerate(chunks):
            page = chunk["metadata"].get("page", "N/A")
            context_parts.append(f"\n[Trecho {i+1} - Página {page}]:")
            context_parts.append(chunk["text"])

        # Controlar tamanho do contexto
        full_context = "\n".join(context_parts)

        if self.count_tokens(full_context) > settings.max_context_tokens:
            # Truncar se necessário
            available_tokens = settings.max_context_tokens - 500  # Reservar espaço para prompt

            # Estimar caracteres por token (aproximadamente 4)
            max_chars = available_tokens * 4

            full_context = full_context[:max_chars]
            full_context += "\n\n[Contexto truncado devido ao limite de tokens]"

        return full_context

    def build_prompt(self, query: str, context: str, history: List[ChatMessage]) -> str:
        """
        Constrói o prompt para o LLM

        Args:
            query: Query atual do usuário
            context: Contexto dos documentos
            history: Histórico de conversa

        Returns:
            Prompt formatado
        """
        prompt_parts = [
            "Você é um assistente especializado em responder perguntas sobre documentos PDF.",
            "Você deve responder baseando-se APENAS no contexto fornecido abaixo.",
            "Se a informação não estiver no contexto, diga que não encontrou a resposta.",
            "Seja claro, conciso e cite a página das informações quando possível.",
            "",
            "CONTEXTO DO DOCUMENTO:",
            context,
            "",
            "HISTÓRICO DE CONVERSA:",
        ]

        # Adicionar histórico (últimas 5 trocas)
        for msg in history[-10:]:
            role = "USUÁRIO" if msg.role == "user" else "ASSISTENTE"
            prompt_parts.append(f"{role}: {msg.content}")

        prompt_parts.append(f"\nPERGUNTA ATUAL:\n{query}")
        prompt_parts.append("\nRESPOSTA:")

        return "\n".join(prompt_parts)

    def chat(self, query: str, document_id: str, history: List[ChatMessage] = [],
              use_raptor: bool = True) -> ChatResponse:
        """
        Gera resposta para uma query usando RAG

        Args:
            query: Query do usuário
            document_id: ID do documento
            history: Histórico de conversa
            use_raptor: Se deve usar RAPTOR

        Returns:
            Resposta do chat com fontes
        """
        if not self.initialized:
            self.initialize()

        # 1. Recuperar chunks via RAG
        rag_results = rag_service.hybrid_search(
            query=query,
            top_k=settings.top_k_results,
            document_id=document_id
        )

        if not rag_results:
            return ChatResponse(
                answer="Desculpe, não encontrei informações relevantes no documento.",
                sources=[],
                model=settings.openai_model
            )

        # 2. Se usando RAPTOR, carregar árvore e recuperar resumo
        raptor_summary = None
        raptor_tree = None

        if use_raptor:
            raptor_tree = raptor_service.load_raptor_tree(document_id)

            if raptor_tree:
                raptor_summary = raptor_service.get_raptor_summary(raptor_tree)

        # 3. Construir contexto
        context = self.build_context(
            query=query,
            chunks=rag_results,
            use_raptor=use_raptor,
            raptor_tree=raptor_tree
        )

        # 4. Construir prompt
        prompt = self.build_prompt(query, context, history)

        # 5. Gerar resposta
        try:
            response = self.llm_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "Você é um assistente especializado em responder perguntas sobre documentos."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )

            answer = response.choices[0].message.content.strip()

        except Exception as e:
            print(f"Erro ao gerar resposta: {e}")
            answer = f"Erro ao processar sua pergunta: {str(e)}"

        # 6. Preparar fontes
        sources = []
        for chunk in rag_results:
            sources.append({
                "page": chunk["metadata"].get("page", "N/A"),
                "score": chunk["score"],
                "snippet": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"]
            })

        return ChatResponse(
            answer=answer,
            sources=sources,
            raptor_summary=raptor_summary,
            model=settings.openai_model
        )

    def summarize_document(self, document_id: str, pages: Optional[List[int]] = None,
                        detail_level: str = "medium") -> str:
        """
        Gera um resumo do documento

        Args:
            document_id: ID do documento
            pages: Páginas específicas (opcional)
            detail_level: Nível de detalhe ('brief', 'medium', 'detailed')

        Returns:
            Resumo do documento
        """
        if not self.initialized:
            self.initialize()

        # 1. Carregar árvore RAPTOR
        raptor_tree = raptor_service.load_raptor_tree(document_id)

        if raptor_tree:
            # 2. Usar resumo do RAPTOR
            level_map = {"brief": 2, "medium": 1, "detailed": 0}

            target_level = level_map.get(detail_level, -1)

            # Ajustar se nível não existir
            max_available = raptor_tree["depth"]
            if target_level > max_available:
                target_level = max_available

            summary = raptor_service.get_raptor_summary(raptor_tree, level=target_level)

            if summary:
                return summary

        # 3. Se não tem RAPTOR, usar chunks
        chunks = rag_service.get_document_chunks(document_id)

        if not chunks:
            return "Não foi possível gerar um resumo. Documento não indexado."

        # Selecionar chunks baseados em páginas
        if pages:
            filtered_chunks = [c for c in chunks if c["metadata"].get("page") in pages]
        else:
            filtered_chunks = chunks

        if not filtered_chunks:
            filtered_chunks = chunks[:10]  # Usar primeiros 10 chunks

        # Concatenar chunks
        combined_text = "\n\n".join([chunk["text"] for chunk in filtered_chunks])

        # Gerar resumo com LLM
        detail_prompt = {
            "brief": "um resumo breve (1-2 parágrafos)",
            "medium": "um resumo detalhado (3-5 parágrafos)",
            "detailed": "um resumo completo e abrangente"
        }

        prompt = f"""Resuma o seguinte documento de forma {detail_prompt.get(detail_level, 'detalhada')}:

{combined_text}

RESUMO:"""

        try:
            response = self.llm_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "Você é um assistente especializado em resumir documentos de forma clara e estruturada."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"Erro ao gerar resumo: {e}")
            return combined_text[:500] + "..."


# Instância global do serviço de chat
chat_service = ChatService()
