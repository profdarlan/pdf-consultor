# ==========================================
# PDF Consultor - PDF Processing Service
# ==========================================

import hashlib
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from pypdf import PdfReader
from pdfplumber import PDF
import pytesseract
from PIL import Image

from app.config import settings
from app.models import DocumentCategory


class PDFProcessor:
    """Serviço para processamento de arquivos PDF"""

    def __init__(self):
        self.pdfs_path = settings.pdfs_path

    def generate_document_id(self, filename: str) -> str:
        """Gera ID único para documento baseado no nome e timestamp"""
        content = f"{filename}_{datetime.now().timestamp()}"
        return hashlib.md5(content.encode()).hexdigest()

    def extract_metadata(self, pdf_path: Path) -> Dict[str, Any]:
        """Extrai metadados básicos do PDF"""
        reader = PdfReader(pdf_path)

        metadata = {
            "page_count": len(reader.pages),
            "title": reader.metadata.title if reader.metadata and reader.metadata.title else pdf_path.stem,
            "author": reader.metadata.author if reader.metadata else None,
            "subject": reader.metadata.subject if reader.metadata else None,
            "creator": reader.metadata.creator if reader.metadata else None,
            "producer": reader.metadata.producer if reader.metadata else None,
            "creation_date": reader.metadata.creation_date if reader.metadata else None,
            "modification_date": reader.metadata.modification_date if reader.metadata else None,
        }

        return metadata

    def extract_text(self, pdf_path: Path, pages: Optional[List[int]] = None) -> Dict[int, str]:
        """Extrai texto de um PDF, opcionalmente de páginas específicas"""
        reader = PdfReader(pdf_path)
        text_by_page = {}

        for i, page in enumerate(reader.pages):
            if pages is None or (i + 1) in pages:
                text = page.extract_text()
                if text and text.strip():
                    text_by_page[i + 1] = text

        return text_by_page

    def extract_text_with_layout(self, pdf_path: Path) -> Dict[int, str]:
        """Extrai texto preservando layout usando pdfplumber"""
        text_by_page = {}

        with PDF.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text and text.strip():
                    text_by_page[i + 1] = text

        return text_by_page

    def extract_tables(self, pdf_path: Path) -> List[List[List[str]]]:
        """Extrai tabelas de um PDF"""
        tables = []

        with PDF.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)

        return tables

    def ocr_page(self, pdf_path: Path, page_num: int) -> str:
        """Faz OCR de uma página específica usando Tesseract"""
        from pdf2image import convert_from_path

        images = convert_from_path(
            pdf_path,
            first_page=page_num,
            last_page=page_num,
            dpi=300
        )

        if images:
            text = pytesseract.image_to_string(images[0], lang='por')
            return text

        return ""

    def is_scanned(self, pdf_path: Path, sample_pages: int = 3) -> bool:
        """Verifica se o PDF parece ser digitalizado (texto não selecionável)"""
        reader = PdfReader(pdf_path)

        pages_to_check = min(sample_pages, len(reader.pages))
        scanned_count = 0

        for i in range(pages_to_check):
            text = reader.pages[i].extract_text()
            if not text or len(text.strip()) < 50:
                scanned_count += 1

        return scanned_count / pages_to_check > 0.7

    def get_document_info(self, pdf_path: Path, document_id: str,
                         category: DocumentCategory = DocumentCategory.OUTROS,
                         parent_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtém informações completas de um documento"""
        from app.models import DocumentMetadata

        metadata = self.extract_metadata(pdf_path)

        doc_info = {
            "id": document_id,
            "filename": pdf_path.name,
            "title": metadata["title"] or pdf_path.stem,
            "category": category,
            "path": str(pdf_path.relative_to(self.pdfs_path)),
            "file_size": pdf_path.stat().st_size,
            "page_count": metadata["page_count"],
            "created_at": datetime.fromtimestamp(pdf_path.stat().st_ctime),
            "updated_at": datetime.fromtimestamp(pdf_path.stat().st_mtime),
            "indexed_at": None,
            "is_indexed": False,
            "parent_id": parent_id,
        }

        return doc_info

    def detect_category_from_path(self, pdf_path: Path) -> DocumentCategory:
        """Detecta categoria baseada no caminho do arquivo"""
        parts = pdf_path.parts

        if DocumentCategory.JURIDICO.value in parts:
            return DocumentCategory.JURIDICO
        elif DocumentCategory.FINANCEIRO.value in parts:
            return DocumentCategory.FINANCEIRO
        elif DocumentCategory.TECNICO.value in parts:
            return DocumentCategory.TECNICO
        else:
            return DocumentCategory.OUTROS

    def get_all_pdfs(self) -> List[Path]:
        """Lista todos os arquivos PDF no diretório de trabalho"""
        pdf_files = []

        for pdf_file in self.pdfs_path.rglob("*.pdf"):
            if pdf_file.is_file():
                pdf_files.append(pdf_file)

        return sorted(pdf_files)

    def get_pdfs_by_category(self, category: DocumentCategory) -> List[Path]:
        """Lista PDFs por categoria"""
        category_path = self.pdfs_path / category.value

        if not category_path.exists():
            return []

        return sorted(category_path.rglob("*.pdf"))

    def get_pdf_by_id(self, document_id: str) -> Optional[Path]:
        """Encontra um PDF pelo ID (busca no índice de metadados)"""
        # Isso será implementado na camada de persistência
        # Por enquanto, retorna None
        return None


# Instância global do processador de PDF
pdf_processor = PDFProcessor()
