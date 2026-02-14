# ==========================================
# PDF Consultor - Persistence Service
# ==========================================

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.config import settings
from app.models import (
    DocumentMetadata, DocumentCategory,
    NoteMetadata, NoteType
)


class PersistenceService:
    """Serviço de persistência de metadados e notas"""

    def __init__(self):
        self.docs_file = settings.indexes_path / "documents.json"
        self.notes_file = settings.notes_path / "notes.json"

        # Garantir que arquivos existam
        self.docs_file.parent.mkdir(parents=True, exist_ok=True)
        self.notes_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_json(self, filepath: Path) -> Dict[str, Any]:
        """Carrega um arquivo JSON"""
        if not filepath.exists():
            return {}

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao carregar {filepath}: {e}")
            return {}

    def _save_json(self, filepath: Path, data: Dict[str, Any]):
        """Salva dados em um arquivo JSON"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # --- Documentos ---

    def save_document(self, doc: DocumentMetadata) -> None:
        """Salva metadados de um documento"""
        docs = self._load_json(self.docs_file)
        docs[doc.id] = doc.model_dump()

        self._save_json(self.docs_file, docs)

    def get_document(self, document_id: str) -> Optional[DocumentMetadata]:
        """Recupera metadados de um documento"""
        docs = self._load_json(self.docs_file)

        if document_id not in docs:
            return None

        return DocumentMetadata(**docs[document_id])

    def get_all_documents(self) -> List[DocumentMetadata]:
        """Recupera todos os documentos"""
        docs = self._load_json(self.docs_file)

        return [DocumentMetadata(**doc) for doc in docs.values()]

    def get_documents_by_category(self, category: DocumentCategory) -> List[DocumentMetadata]:
        """Recupera documentos por categoria"""
        docs = self._load_json(self.docs_file)

        return [
            DocumentMetadata(**doc)
            for doc in docs.values()
            if doc.get("category") == category.value
        ]

    def get_documents_by_parent(self, parent_id: str) -> List[DocumentMetadata]:
        """Recupera anexos de um documento principal"""
        docs = self._load_json(self.docs_file)

        return [
            DocumentMetadata(**doc)
            for doc in docs.values()
            if doc.get("parent_id") == parent_id
        ]

    def update_document(self, document_id: str, updates: Dict[str, Any]) -> bool:
        """Atualiza metadados de um documento"""
        docs = self._load_json(self.docs_file)

        if document_id not in docs:
            return False

        docs[document_id].update(updates)
        docs[document_id]["updated_at"] = datetime.now().isoformat()

        self._save_json(self.docs_file, docs)
        return True

    def delete_document(self, document_id: str) -> bool:
        """Remove metadados de um documento"""
        docs = self._load_json(self.docs_file)

        if document_id not in docs:
            return False

        del docs[document_id]
        self._save_json(self.docs_file, docs)
        return True

    def set_document_indexed(self, document_id: str, chunk_count: int,
                            raptor_layers: Optional[int] = None) -> None:
        """Marca documento como indexado"""
        self.update_document(document_id, {
            "is_indexed": True,
            "indexed_at": datetime.now().isoformat(),
            "chunk_count": chunk_count,
            "raptor_layers": raptor_layers
        })

    # --- Notas ---

    def save_note(self, note: NoteMetadata) -> None:
        """Salva uma anotação"""
        notes = self._load_json(self.notes_file)
        notes[note.id] = note.model_dump()

        self._save_json(self.notes_file, notes)

    def get_note(self, note_id: str) -> Optional[NoteMetadata]:
        """Recupera uma anotação"""
        notes = self._load_json(self.notes_file)

        if note_id not in notes:
            return None

        return NoteMetadata(**notes[note_id])

    def get_notes_by_document(self, document_id: str) -> List[NoteMetadata]:
        """Recupera todas as anotações de um documento"""
        notes = self._load_json(self.notes_file)

        return [
            NoteMetadata(**note)
            for note in notes.values()
            if note.get("document_id") == document_id
        ]

    def update_note(self, note_id: str, updates: Dict[str, Any]) -> bool:
        """Atualiza uma anotação"""
        notes = self._load_json(self.notes_file)

        if note_id not in notes:
            return False

        notes[note_id].update(updates)
        notes[note_id]["updated_at"] = datetime.now().isoformat()

        self._save_json(self.notes_file, notes)
        return True

    def delete_note(self, note_id: str) -> bool:
        """Remove uma anotação"""
        notes = self._load_json(self.notes_file)

        if note_id not in notes:
            return False

        del notes[note_id]
        self._save_json(self.notes_file, notes)
        return True

    def delete_notes_by_document(self, document_id: str) -> int:
        """Remove todas as anotações de um documento"""
        notes = self._load_json(self.notes_file)

        to_delete = [
            note_id for note_id, note in notes.items()
            if note.get("document_id") == document_id
        ]

        for note_id in to_delete:
            del notes[note_id]

        self._save_json(self.notes_file, notes)

        return len(to_delete)


# Instância global do serviço de persistência
persistence = PersistenceService()
