# ==========================================
# PDF Consultor - Data Models
# ==========================================

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class DocumentCategory(str, Enum):
    """Categorias de documentos"""
    JURIDICO = "juridico"
    FINANCEIRO = "financeiro"
    TECNICO = "tecnico"
    OUTROS = "outros"


class DocumentMetadata(BaseModel):
    """Metadados de um documento PDF"""
    id: str = Field(..., description="ID único do documento")
    filename: str = Field(..., description="Nome do arquivo")
    title: str = Field(..., description="Título do documento")
    category: DocumentCategory = Field(..., description="Categoria do documento")
    path: str = Field(..., description="Caminho do arquivo")
    file_size: int = Field(..., description="Tamanho do arquivo em bytes")
    page_count: int = Field(..., description="Número de páginas")
    created_at: datetime = Field(default_factory=datetime.now, description="Data de criação")
    updated_at: datetime = Field(default_factory=datetime.now, description="Data de atualização")
    indexed_at: Optional[datetime] = Field(None, description="Data da última indexação")
    is_indexed: bool = Field(default=False, description="Se o documento está indexado")
    parent_id: Optional[str] = Field(None, description="ID do documento principal (se for anexo)")


class DocumentList(BaseModel):
    """Lista de documentos para API"""
    documents: List[DocumentMetadata]
    total: int = Field(..., description="Número total de documentos")


class DocumentUpdate(BaseModel):
    """Modelo para atualização de documento"""
    title: Optional[str] = Field(None, description="Novo título")
    category: Optional[DocumentCategory] = Field(None, description="Nova categoria")


class NoteType(str, Enum):
    """Tipos de anotações"""
    GLOBAL = "global"
    PAGE = "page"
    SELECTION = "selection"


class NoteMetadata(BaseModel):
    """Metadados de uma anotação"""
    id: str = Field(..., description="ID único da anotação")
    document_id: str = Field(..., description="ID do documento")
    note_type: NoteType = Field(..., description="Tipo da anotação")
    content: str = Field(..., description="Conteúdo da anotação")
    page_number: Optional[int] = Field(None, description="Número da página (para anotações de página)")
    text_selection: Optional[str] = Field(None, description="Texto selecionado (para anotações de seleção)")
    created_at: datetime = Field(default_factory=datetime.now, description="Data de criação")
    updated_at: datetime = Field(default_factory=datetime.now, description="Data de atualização")


class NoteList(BaseModel):
    """Lista de anotações para API"""
    notes: List[NoteMetadata]
    total: int = Field(..., description="Número total de anotações")


class ChatMessage(BaseModel):
    """Mensagem de chat"""
    role: str = Field(..., description="Role: 'user' ou 'assistant'")
    content: str = Field(..., description="Conteúdo da mensagem")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp da mensagem")


class ChatRequest(BaseModel):
    """Requisição de chat"""
    document_id: str = Field(..., description="ID do documento")
    query: str = Field(..., description="Pergunta do usuário")
    history: List[ChatMessage] = Field(default_factory=list, description="Histórico de conversa")
    use_raptor: bool = Field(default=True, description="Usar RAPTOR para resposta")


class ChatResponse(BaseModel):
    """Resposta do chat"""
    answer: str = Field(..., description="Resposta gerada")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Fontes utilizadas")
    raptor_summary: Optional[str] = Field(None, description="Resumo RAPTOR (se aplicável)")
    model: str = Field(..., description="Modelo LLM utilizado")


class SummaryRequest(BaseModel):
    """Requisição de resumo"""
    document_id: str = Field(..., description="ID do documento")
    pages: Optional[List[int]] = Field(None, description="Páginas específicas para resumir (opcional)")
    detail_level: str = Field(default="medium", description="Nível de detalhe: 'brief', 'medium', 'detailed'")


class SummaryResponse(BaseModel):
    """Resposta de resumo"""
    summary: str = Field(..., description="Resumo gerado")
    page_count: int = Field(..., description="Número de páginas resumidas")
    model: str = Field(..., description="Modelo LLM utilizado")


class SearchRequest(BaseModel):
    """Requisição de busca"""
    query: str = Field(..., description="Termo de busca")
    category: Optional[DocumentCategory] = Field(None, description="Filtrar por categoria")
    limit: int = Field(default=10, description="Número máximo de resultados")


class SearchResult(BaseModel):
    """Resultado de busca"""
    document_id: str = Field(..., description="ID do documento")
    filename: str = Field(..., description="Nome do arquivo")
    title: str = Field(..., description="Título do documento")
    category: DocumentCategory = Field(..., description="Categoria")
    score: float = Field(..., description="Pontuação de relevância")
    snippet: Optional[str] = Field(None, description="Trecho relevante")


class IndexationStatus(BaseModel):
    """Status de indexação"""
    document_id: str = Field(..., description="ID do documento")
    is_indexed: bool = Field(..., description="Se está indexado")
    indexed_at: Optional[datetime] = Field(None, description="Data da última indexação")
    chunk_count: Optional[int] = Field(None, description="Número de chunks indexados")
    raptor_layers: Optional[int] = Field(None, description="Número de camadas RAPTOR")


class APIResponse(BaseModel):
    """Resposta genérica da API"""
    success: bool = Field(..., description="Se a operação foi bem-sucedida")
    message: str = Field(..., description="Mensagem de status")
    data: Optional[Any] = Field(None, description="Dados adicionais")
