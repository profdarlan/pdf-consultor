# ==========================================
# PDF Consultor - Chat Service (Atualizado com PromptManager)
# ==========================================

from typing import List, Dict, Any, Optional
import tiktoken

from openai import OpenAI

from app.config import settings
from app.models import ChatMessage, ChatResponse, DocumentCategory
from app.rag_service import rag_service
from app.raptor_service import raptor_service
from app.prompts import PromptManager, DocType, DetailLevel


class ChatService:
    """Serviço de chat com RAG, RAPTOR e prompts aprimorados"""

    def __init__(self):
        self.llm_client = None
        self.encoding = None
        self.prompt_manager = PromptManager()
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
            print("  AVISO: OPENAI_API_KEY não configurada. Chat não funcionará.")

        # Inicializar tokenizer
        self.encoding = tiktoken.encoding_for_model(settings.openai_model)

        self.initialized = True
        print("Chat Service inicializado!")

    def count_tokens(self, text: str) -> int:
        """Conta tokens em um texto"""
        if not self.encoding:
            self.encoding = tiktoken.encoding_for_model(settings.openai_model)

        return len(self.encoding.encode(text))

    def _map_category_to_doctype(self, category: DocumentCategory) -> DocType:
        """Mapeia categoria do documento para tipo de prompt"""
        category_map = {
            DocumentCategory.JURIDICO: DocType.JURIDICO,
            DocumentCategory.FINANCEIRO: DocType.FINANCEIRO,
            DocumentCategory.TECNICO: DocType.TECNICO
        }
        return category_map.get(category, DocType.GERAL)

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
                context_parts.append(f"## RESUMO EXECUTIVO DO DOCUMENTO\n{raptor_summary}\n")

        # Adicionar chunks relevantes
        context_parts.append("## TRECHOS RELEVANTES DO DOCUMENTO\n")

        for i, chunk in enumerate(chunks):
            page = chunk["metadata"].get("page", "N/A")
            text = chunk["text"]

            # Truncar para economizar tokens
            if len(text) > 500:
                text = text[:500] + "..."

            context_parts.append(f"\n[Trecho {i+1} - Página {page}]")
            context_parts.append(text)

        # Controlar tamanho do contexto
        full_context = "\n".join(context_parts)

        if self.count_tokens(full_context) > settings.max_context_tokens:
            # Truncar se necessário
            available_tokens = settings.max_context_tokens - 500  # Reservar espaço para prompt

            # Estimar caracteres por token (aproximadamente 4)
            max_chars = available_tokens * 4

            full_context = full_context[:max_chars]
            full_context += "\n\n[⚠️ Contexto truncado devido ao limite de tokens]"

        return full_context

    def chat_with_cot(self, query: str, document_id: str, doc_metadata: Dict[str, Any],
                     history: List[ChatMessage] = [], use_raptor: bool = True) -> ChatResponse:
        """
        Gera resposta usando Chain of Thought estruturado

        Args:
            query: Query do usuário
            document_id: ID do documento
            doc_metadata: Metadados do documento
            history: Histórico de conversa
            use_raptor: Se deve usar RAPTOR

        Returns:
            Resposta do chat com fontes e raciocínio
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

        # 4. Mapear categoria para tipo de prompt
        doc_type = self._map_category_to_doctype(doc_metadata.get("category", DocumentCategory.OUTROS))

        # 5. Construir prompt com CoT
        prompts = self.prompt_manager.get_chat_prompt_with_cot(
            query=query,
            context=context,
            doc_title=doc_metadata.get("title", "Documento"),
            page_count=doc_metadata.get("page_count", 0),
            category=doc_type,
            history=[{"role": msg.role, "content": msg.content} for msg in history]
        )

        # 6. Gerar resposta
        try:
            response = self.llm_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user", "content": prompts["user"]}
                ],
                temperature=0.3,
                max_tokens=2500  # Mais tokens para CoT
            )

            answer = response.choices[0].message.content.strip()

        except Exception as e:
            print(f"Erro ao gerar resposta: {e}")
            answer = f"Erro ao processar sua pergunta: {str(e)}"

        # 7. Validar resposta
        validation = self.prompt_manager.validate_response(answer, query, rag_results)

        # 8. Preparar fontes
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

    def chat(self, query: str, document_id: str, history: List[ChatMessage] = [],
              use_raptor: bool = True, use_cot: bool = False, doc_metadata: Optional[Dict[str, Any]] = None) -> ChatResponse:
        """
        Gera resposta para uma query usando RAG

        Args:
            query: Query do usuário
            document_id: ID do documento
            history: Histórico de conversa
            use_raptor: Se deve usar RAPTOR
            use_cot: Se deve usar Chain of Thought
            doc_metadata: Metadados do documento (necessário para CoT)

        Returns:
            Resposta do chat com fontes
        """
        if not self.initialized:
            self.initialize()

        # Recuperar metadados do documento se não fornecidos
        if doc_metadata is None:
            from app.persistence import persistence
            doc_metadata = persistence.get_document(document_id)
            if not doc_metadata:
                return ChatResponse(
                    answer="Documento não encontrado.",
                    sources=[],
                    model=settings.openai_model
                )

        # Escolher método de geração (CoT vs. simples)
        if use_cot:
            return self.chat_with_cot(query, document_id, doc_metadata, history, use_raptor)

        # ==========================================
        # MÉTODO SIMPLEM (sem CoT explícito)
        # ==========================================

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

        # 4. Mapear categoria para tipo de prompt
        doc_type = self._map_category_to_doctype(doc_metadata.get("category", DocumentCategory.OUTROS))

        # 5. Construir prompt simples
        prompt = self.prompt_manager.get_chat_prompt_simple(
            query=query,
            context=context,
            doc_title=doc_metadata.get("title", "Documento"),
            page_count=doc_metadata.get("page_count", 0),
            category=doc_type
        )

        # 6. Gerar resposta
        try:
            response = self.llm_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": self.prompt_manager.SYSTEM_PROMPTS[doc_type]},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )

            answer = response.choices[0].message.content.strip()

        except Exception as e:
            print(f"Erro ao gerar resposta: {e}")
            answer = f"Erro ao processar sua pergunta: {str(e)}"

        # 7. Preparar fontes
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
        Gera um resumo do documento usando prompts aprimorados

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
            detail_enum = DetailLevel.BRIEF if detail_level == "brief" else DetailLevel.MEDIUM if detail_level == "medium" else DetailLevel.DETAILED
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

        # 4. Obter metadados do documento
        from app.persistence import persistence
        doc_metadata = persistence.get_document(document_id)
        doc_title = doc_metadata.title if doc_metadata else "Documento"
        page_count = doc_metadata.page_count if doc_metadata else 0

        # 5. Concatenar chunks
        combined_text = self.prompt_manager.format_chunks_for_prompt(filtered_chunks)

        # 6. Mapear nível de detalhe
        detail_enum = DetailLevel.BRIEF if detail_level == "brief" else DetailLevel.MEDIUM if detail_level == "medium" else DetailLevel.DETAILED
        doc_type = self._map_category_to_doctype(doc_metadata.category) if doc_metadata else DocType.GERAL

        # 7. Gerar prompt de resumo
        summary_prompt = self.prompt_manager.get_summary_prompt(
            content=combined_text,
            doc_title=doc_title,
            page_count=page_count,
            detail_level=detail_enum,
            category=doc_type
        )

        # 8. Gerar resumo com LLM
        try:
            response = self.llm_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": self.prompt_manager.SYSTEM_PROMPTS[doc_type]},
                    {"role": "user", "content": summary_prompt}
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
