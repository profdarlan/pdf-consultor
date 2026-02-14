# ==========================================
# PDF Consultor - Dockerfile
# ==========================================
# Sistema RAPTOR (Reciprocal Rank Fusion + Abstração Hierárquica)
# Vector Store: FAISS (evita conflito Pydantic)
# ==========================================

FROM python:3.14-slim

# Definir argumentos de build
ARG DEBIAN_FRONTEND=noninteractive
ENV DEBIAN_FRONTEND=${DEBIAN_FRONTEND}

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    curl \
    wget \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-por \
    tesseract-ocr-deu \
    tesseract-ocr-fra \
    tesseract-ocr-spa \
    git \
    && rm -rf /var/lib/apt/lists/*

# Definir diretório de trabalho
WORKDIR /app

# Copiar requirements primeiro (para aproveitar cache Docker)
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY . .

# Criar diretórios necessários
RUN mkdir -p /app/pdfs \
    /app/indexes \
    /app/static \
    /app/logs

# Definir permissões
RUN chmod -R 755 /app

# Expor porta
EXPOSE 8000

# Comando para iniciar o servidor
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
