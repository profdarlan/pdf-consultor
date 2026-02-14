# ==========================================
# PDF Consultor - FastAPI Application
# ==========================================

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import shutil
import uuid

from app.config import settings
from app.models import (
    DocumentList, DocumentUpdate, DocumentCategory,
    NoteList, NoteMetadata, NoteType,
    ChatRequest, ChatResponse,
    SummaryRequest, SummaryResponse,
    APIResponse
)
from app.pdf_processor import pdf_processor
from app.rag_service import rag_service
from app.raptor_service import raptor_service
from app.chat_service import chat_service
from app.persistence import persistence


# Criar aplicação FastAPI
app = FastAPI(
    title="PDF Consultor",
    description="Sistema de consulta a PDFs com RAG, RAPTOR e busca híbrida",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- Inicialização ---

@app.on_event("startup")
async def startup_event():
    """Inicializar serviços no startup"""
    print("\n" + "="*60)
    print("  PDF CONSULTOR - Inicializando")
    print("="*60 + "\n")

    # Inicializar serviços
    rag_service.initialize()
    raptor_service.initialize()
    chat_service.initialize()

    print("\nServiços inicializados com sucesso!")
    print(f"Servidor rodando em: http://{settings.host}:{settings.port}")
    print("="*60 + "\n")


# --- Rotas de Documentos ---

@app.get("/api/documents", response_model=DocumentList)
async def list_documents(category: Optional[DocumentCategory] = None):
    """Lista todos os documentos (ou por categoria)"""
    if category:
        docs = persistence.get_documents_by_category(category)
    else:
        docs = persistence.get_all_documents()

    return DocumentList(documents=docs, total=len(docs))


@app.get("/api/documents/{document_id}")
async def get_document(document_id: str):
    """Recupera metadados de um documento específico"""
    doc = persistence.get_document(document_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    return doc


@app.put("/api/documents/{document_id}")
async def update_document(document_id: str, update: DocumentUpdate):
    """Atualiza título e categoria de um documento"""
    success = persistence.update_document(document_id, {
        "title": update.title,
        "category": update.category.value if update.category else None
    })

    if not success:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    return APIResponse(success=True, message="Documento atualizado com sucesso")


@app.delete("/api/documents/{document_id}")
async def delete_document(document_id: str, background_tasks: BackgroundTasks):
    """Exclui um documento e todos os seus anexos/índices"""
    doc = persistence.get_document(document_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    # Deletar arquivo
    pdf_path = settings.pdfs_path / doc.path
    if pdf_path.exists():
        pdf_path.unlink()

    # Deletar do índice RAG
    background_tasks.add_task(rag_service.delete_document, document_id)

    # Deletar índice RAPTOR
    raptor_tree_path = settings.indexes_path / f"raptor_{document_id}.json"
    if raptor_tree_path.exists():
        raptor_tree_path.unlink()

    # Deletar notas
    persistence.delete_notes_by_document(document_id)

    # Deletar metadados
    persistence.delete_document(document_id)

    # Deletar anexos
    attachments = persistence.get_documents_by_parent(document_id)
    for attachment in attachments:
        await delete_document(attachment.id, background_tasks)

    return APIResponse(success=True, message="Documento excluído com sucesso")


@app.get("/api/documents/{document_id}/download")
async def download_document(document_id: str):
    """Baixa um arquivo PDF"""
    doc = persistence.get_document(document_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    pdf_path = settings.pdfs_path / doc.path

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=doc.filename
    )


@app.get("/api/documents/{document_id}/attachments")
async def get_attachments(document_id: str):
    """Lista anexos de um documento"""
    attachments = persistence.get_documents_by_parent(document_id)

    return DocumentList(documents=attachments, total=len(attachments))


@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    category: DocumentCategory = DocumentCategory.OUTROS,
    parent_id: Optional[str] = None,
    background_tasks: BackgroundTasks = None
):
    """Faz upload de um novo documento PDF"""
    # Validar arquivo
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são permitidos")

    # Criar diretório da categoria se não existir
    category_path = settings.pdfs_path / category.value
    category_path.mkdir(parents=True, exist_ok=True)

    # Salvar arquivo
    filename = file.filename
    file_path = category_path / filename

    # Se arquivo já existe, adicionar sufixo
    counter = 1
    while file_path.exists():
        name, ext = filename.rsplit('.', 1)
        file_path = category_path / f"{name}_{counter}.{ext}"
        counter += 1

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Gerar ID e metadados
    from app.pdf_processor import PDFProcessor
    processor = PDFProcessor()

    document_id = processor.generate_document_id(file_path.name)
    metadata = processor.extract_metadata(file_path)

    doc = DocumentMetadata(
        id=document_id,
        filename=file_path.name,
        title=metadata["title"] or file_path.stem,
        category=category,
        path=str(file_path.relative_to(settings.pdfs_path)),
        file_size=file_path.stat().st_size,
        page_count=metadata["page_count"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        is_indexed=False,
        parent_id=parent_id
    )

    # Salvar metadados
    persistence.save_document(doc)

    # Indexar em background
    if background_tasks:
        background_tasks.add_task(index_document, document_id, file_path)

    return doc


def index_document(document_id: str, pdf_path: Path):
    """Indexa um documento em background"""
    from app.pdf_processor import PDFProcessor

    print(f"Indexando documento {document_id}...")

    processor = PDFProcessor()

    # Extrair texto
    text_by_page = processor.extract_text_with_layout(pdf_path)

    # Criar chunks
    chunks = []
    for page_num, text in text_by_page.items():
        if text.strip():
            chunks.append({
                "text": text,
                "page": page_num
            })

    # Adicionar ao RAG
    rag_service.add_documents(chunks, document_id)

    # Construir RAPTOR
    chunk_texts = [chunk["text"] for chunk in chunks]
    raptor_service.build_and_index_document(chunk_texts, document_id)

    # Marcar como indexado
    persistence.set_document_indexed(document_id, len(chunks))

    print(f"Documento {document_id} indexado com {len(chunks)} chunks")


@app.post("/api/documents/{document_id}/reindex")
async def reindex_document(document_id: str, background_tasks: BackgroundTasks):
    """Reindexa um documento existente"""
    doc = persistence.get_document(document_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    pdf_path = settings.pdfs_path / doc.path

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    # Deletar índices antigos
    rag_service.delete_document(document_id)

    raptor_tree_path = settings.indexes_path / f"raptor_{document_id}.json"
    if raptor_tree_path.exists():
        raptor_tree_path.unlink()

    # Reindexar
    background_tasks.add_task(index_document, document_id, pdf_path)

    return APIResponse(success=True, message="Documento está sendo reindexado")


# --- Rotas de Chat ---

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Processa uma pergunta sobre um documento"""
    if not chat_service.initialized:
        raise HTTPException(status_code=500, detail="Serviço de chat não inicializado")

    response = chat_service.chat(
        query=request.query,
        document_id=request.document_id,
        history=request.history,
        use_raptor=request.use_raptor
    )

    return response


@app.post("/api/documents/{document_id}/summary", response_model=SummaryResponse)
async def summarize_document(document_id: str, request: SummaryRequest):
    """Gera um resumo do documento"""
    if not chat_service.initialized:
        raise HTTPException(status_code=500, detail="Serviço de chat não inicializado")

    summary = chat_service.summarize_document(
        document_id=document_id,
        pages=request.pages,
        detail_level=request.detail_level
    )

    doc = persistence.get_document(document_id)

    return SummaryResponse(
        summary=summary,
        page_count=doc.page_count if doc else 0,
        model=settings.openai_model
    )


# --- Rotas de Notas ---

@app.get("/api/documents/{document_id}/notes", response_model=NoteList)
async def get_notes(document_id: str):
    """Lista todas as anotações de um documento"""
    notes = persistence.get_notes_by_document(document_id)

    return NoteList(notes=notes, total=len(notes))


@app.post("/api/documents/{document_id}/notes")
async def create_note(document_id: str, note: NoteMetadata):
    """Cria uma nova anotação"""
    note.id = str(uuid.uuid4())
    note.document_id = document_id

    persistence.save_note(note)

    return note


@app.put("/api/notes/{note_id}")
async def update_note(note_id: str, note: NoteMetadata):
    """Atualiza uma anotação"""
    success = persistence.update_note(note_id, {
        "content": note.content,
        "updated_at": datetime.now().isoformat()
    })

    if not success:
        raise HTTPException(status_code=404, detail="Nota não encontrada")

    return APIResponse(success=True, message="Nota atualizada com sucesso")


@app.delete("/api/notes/{note_id}")
async def delete_note(note_id: str):
    """Exclui uma anotação"""
    success = persistence.delete_note(note_id)

    if not success:
        raise HTTPException(status_code=404, detail="Nota não encontrada")

    return APIResponse(success=True, message="Nota excluída com sucesso")


# --- Rotas de Visualização ---

@app.get("/api/documents/{document_id}/page/{page_number}")
async def get_page_image(document_id: str, page_number: int):
    """Retorna uma página do PDF como imagem"""
    doc = persistence.get_document(document_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    pdf_path = settings.pdfs_path / doc.path

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    # Converter página para imagem
    from pdf2image import convert_from_path
    from PIL import Image
    import io

    try:
        images = convert_from_path(
            pdf_path,
            first_page=page_number,
            last_page=page_number,
            dpi=150
        )

        if not images:
            raise HTTPException(status_code=404, detail="Página não encontrada")

        # Converter para bytes
        img_byte_arr = io.BytesIO()
        images[0].save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()

        return FileResponse(
            path=pdf_path,  # Retornar o arquivo diretamente (navegador renderiza PDF)
            media_type="application/pdf"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar página: {str(e)}")


# --- Rotas de Sistema ---

@app.get("/api/stats")
async def get_stats():
    """Retorna estatísticas do sistema"""
    docs = persistence.get_all_documents()

    indexed_count = sum(1 for doc in docs if doc.is_indexed)

    index_stats = rag_service.get_index_stats()

    return {
        "total_documents": len(docs),
        "indexed_documents": indexed_count,
        "total_chunks": index_stats["total_chunks"],
        "categories": {
            "juridico": len([d for d in docs if d.category == DocumentCategory.JURIDICO]),
            "financeiro": len([d for d in docs if d.category == DocumentCategory.FINANCEIRO]),
            "tecnico": len([d for d in docs if d.category == DocumentCategory.TECNICO]),
            "outros": len([d for d in docs if d.category == DocumentCategory.OUTROS])
        }
    }


@app.get("/")
async def root():
    """Rota raiz - retorna o HTML principal"""
    from fastapi.responses import HTMLResponse

    html_path = Path("templates/index.html")

    if not html_path.exists():
        return {"message": "Interface HTML não encontrada. Use a API REST."}

    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


# --- Execução Local ---

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=settings.workers
    )
