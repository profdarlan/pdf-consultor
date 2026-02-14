# 📄 PDF Consultor - Sistema de Consulta Inteligente

Sistema RAPTOR (Reciprocal Rank Fusion + Abstração Hierárquica) para consulta inteligente de PDFs.

## 🚀 Características

- ✅ **Busca Híbrida**: Combina busca vetorial (embeddings) + busca por palavra-chave (BM25)
- ✅ **Vector Store**: **FAISS** (evita conflito Pydantic v1/v2)
- ✅ **Reciprocal Rank Fusion (RRF)**: Combina resultados de múltiplos algoritmos
- ✅ **Abstração Hierárquica (RAPTOR)**: Sumarização recursiva de documentos longos
- ✅ **Multi-Documento**: Indexação simultânea de múltiplos PDFs
- ✅ **API RESTful**: FastAPI com documentação Swagger
- ✅ **Interface Web**: Swagger UI + Upload de PDFs
- ✅ **RAG**: Retrieval-Augmented Generation com LLM

## 🛠️ Stack Tecnológica

- **Framework**: FastAPI 0.129.0
- **Vector Store**: FAISS 1.13.2
- **Embeddings**: Sentence Transformers (all-MiniLM-L6-v2)
- **Busca**: Scikit-learn (BM25 + Hybrid)
- **LLM**: OpenAI (configurável)
- **Processamento PDF**: pdfplumber, pypdf, pytesseract
- **Python**: 3.14

## 📦 Instalação

### 1. Via Docker (Recomendado)

```bash
# Clonar repositório
git clone <REPO_URL>
cd pdf-consultor

# Construir e rodar
docker-compose up -d

# Verificar logs
docker-compose logs -f

# Acessar Swagger UI
http://localhost:8000/docs
```

### 2. Via Docker Build Manual

```bash
# Construir imagem
docker build -t pdf-consultor:latest .

# Rodar container
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/pdfs:/app/pdfs \
  -v $(pwd)/indexes:/app/indexes \
  pdf-consultor:latest

# Verificar logs
docker logs -f <CONTAINER_ID>
```

### 3. Via Python Local

```bash
# Criar ambiente virtual
python3 -m venv venv2
source venv2/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Inicializar serviços
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Acessar Swagger UI
http://localhost:8000/docs
```

## 📝 Configuração

### Variáveis de Ambiente

- `PYTHONUNBUFFERED`: Desativar buffer de Python (recomendado: `1`)
- `TZ`: Timezone (padrão: `America/Sao_Paulo`)
- `OPENAI_API_KEY`: API key do OpenAI (opcional, para features RAG)

### Configuração do Servidor

- **Host**: `0.0.0.0` (todas as interfaces) ou IP específico
- **Porta**: `8000` (padrão)
- **Workers**: `1` (padrão para single-threaded FAISS)

## 📁 Estrutura de Diretórios

```
pdf-consultor/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── models.py            # Pydantic models
│   ├── config.py            # Configuration
│   ├── pdf_processor.py     # PDF processing
│   ├── rag_service.py       # FAISS RAG service (UPDATED!)
│   ├── raptor_service.py     # RAPTOR abstractions
│   ├── chat_service.py      # Chat & LLM
│   └── persistence.py       # Data persistence
├── pdfs/                     # Arquivos PDF (montado volume)
├── indexes/                   # Índices FAISS (montado volume)
├── static/                    # Arquivos estáticos web
├── requirements.txt            # Dependências Python
├── Dockerfile                 # Dockerfile
├── docker-compose.yml          # Docker Compose
└── README.md                  # Este arquivo
```

## 🔧 Notas de Migração

### De ChromaDB para FAISS

O sistema foi migrado de **ChromaDB** para **FAISS** para evitar conflitos com Pydantic v2 no Python 3.14.

**Alterações principais:**

1. **rag_service.py**: Reimplementado para usar FAISS
   - `faiss.IndexFlatIP` (Inner Product) ao invés de ChromaDB Client
   - Normalização L2 de embeddings (para cosine similarity)
   - Armazenamento em memória (mais rápido que ChromaDB)

2. **requirements.txt**: Atualizado
   - Removido: `chromadb>=0.5.0`, `langchain-chroma>=1.1.0`
   - Adicionado: `faiss-cpu>=1.7.4`

3. **Dockerfile**: Atualizado para Python 3.14

### Limitações FAISS

- **Não persistente por padrão**: Índices são salvos em memória
  - Solução: Montar volume `/app/indexes` para persistência
- **Não suporta deleção**: FAISS não suporta remoção incremental de vetores
  - Solução: Recriar índice ao deletar documento
- **Single-threaded**: FAISS CPU não suporta concorrência
  - Solução: Use `workers=1` em uvicorn

## 🚀 Uso

### 1. Upload de PDFs

```bash
# Via cURL
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@documento.pdf" \
  -F "category=OUTROS"

# Via Swagger UI
Acesse: http://localhost:8000/docs
POST /api/documents/upload
```

### 2. Busca em PDFs

```bash
# Busca híbrida (vetorial + palavra-chave)
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "inteligência artificial",
    "top_k": 5,
    "document_id": "doc123"
  }'
```

### 3. Chat com PDFs

```bash
# Chat RAPTOR
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Explique o conceito de RAPTOR",
    "document_id": "doc123",
    "use_raptor": true,
    "max_tokens": 1000
  }'
```

## 📚 Referências

- [FAISS Facebook AI Similarity Search](https://github.com/facebookresearch/faiss)
- [Sentence Transformers](https://www.sbert.net/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Pydantic v2](https://docs.pydantic.dev/)

## 🐛 Troubleshooting

### Problema: Conexão recusada na porta 8000

**Causa 1**: Servidor não está rodando
```bash
# Verificar processo
ps aux | grep uvicorn

# Verificar logs
docker logs -f pdf-consultor
```

**Causa 2**: Firewall ou port forward
```bash
# Verificar se porta 8000 está aberta
lsof -i :8000

# Testar conexão
curl -v http://localhost:8000/
```

### Problema: Erro "unable to infer type for attribute"

**Causa**: Conflito Pydantic v1/v2 (ChromaDB + Python 3.14)

**Solução**: Use FAISS ao invés de ChromaDB
```bash
# Verificar requirements
cat requirements.txt | grep -E "chroma|faiss"

# Deve conter:
faiss-cpu>=1.7.4
# E NÃO deve conter:
chromadb>=0.5.0
langchain-chroma>=1.1.0
```

## 📄 Licença

MIT License - Ver arquivo LICENSE para detalhes.

## 👥 Autores

Desenvolvido para [PDF Consultor](https://github.com/seu-usuario/pdf-consultor)
