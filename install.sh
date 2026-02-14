#!/bin/bash
# ==========================================
# PDF Consultor - Script de Instalação
# ==========================================

set -e  # Para no erro

echo "========================================="
echo "  PDF CONSULTOR - Instalação"
echo "========================================="
echo ""

# Detectar sistema operacional
OS="$(uname -s)"
case "${OS}" in
    Linux*)     OS=Linux;;
    Darwin*)    OS=Mac;;
    *)          OS="UNKNOWN:${OS}"
esac

echo "Sistema operacional detectado: ${OS}"
echo ""

# ==========================================
# 1. Verificar Python
# ==========================================

echo "📦 Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Por favor, instale Python 3.10+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
echo "✅ Python versão: ${PYTHON_VERSION}"

if [ "$(echo "${PYTHON_VERSION} < 3.10" | bc)" -eq 1 ]; then
    echo "❌ Python 3.10+ necessário. Versão atual: ${PYTHON_VERSION}"
    exit 1
fi
echo ""

# ==========================================
# 2. Instalar dependências do sistema
# ==========================================

echo "🔧 Instalando dependências do sistema..."

if [ "${OS}" = "Linux" ]; then
    echo "Detectado Linux (Debian/Ubuntu)..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv \
        poppler-utils tesseract-ocr tesseract-ocr-por \
        git curl wget

elif [ "${OS}" = "Mac" ]; then
    echo "Detectado macOS..."
    if ! command -v brew &> /dev/null; then
        echo "Homebrew não encontrado. Instalando..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    brew install python@3.11 poppler tesseract tesseract-lang
fi

echo "✅ Dependências do sistema instaladas"
echo ""

# ==========================================
# 3. Criar ambiente virtual
# ==========================================

echo "🐍 Criando ambiente virtual..."

if [ -d "venv" ]; then
    echo "⚠️  Ambiente virtual já existe. Removendo..."
    rm -rf venv
fi

python3 -m venv venv

echo "✅ Ambiente virtual criado"
echo ""

# ==========================================
# 4. Ativar ambiente virtual
# ==========================================

echo "🔌 Ativando ambiente virtual..."
source venv/bin/activate

# Atualizar pip
echo "📦 Atualizando pip..."
pip install --upgrade pip setuptools wheel

echo ""

# ==========================================
# 5. Instalar dependências Python
# ==========================================

echo "📥 Instalando dependências Python..."
pip install -r requirements.txt

echo "✅ Dependências Python instaladas"
echo ""

# ==========================================
# 6. Criar diretórios necessários
# ==========================================

echo "📁 Criando diretórios..."
mkdir -p trabalho/{juridico,financeiro,tecnico,outros}
mkdir -p indexes notes logs
mkdir -p static/{css,js}

echo "✅ Diretórios criados"
echo ""

# ==========================================
# 7. Configurar .env
# ==========================================

echo "⚙️  Configurando .env..."

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ Arquivo .env criado"
    echo ""
    echo "⚠️  IMPORTANTE: Configure sua OPENAI_API_KEY em .env"
    echo "   nano .env"
    echo ""
else
    echo "✅ Arquivo .env já existe"
fi

# Verificar se OPENAI_API_KEY está configurada
if grep -q "OPENAI_API_KEY=sk-" .env; then
    echo "✅ OPENAI_API_KEY configurada"
else
    echo "⚠️  OPENAI_API_KEY não configurada"
    echo ""
    echo "   Para usar, edite .env e adicione:"
    echo "   OPENAI_API_KEY=sk-sua-chave-aqui"
    echo ""
    echo "   Ou use Ollama (grátis):"
    echo "   OLLAMA_BASE_URL=http://localhost:11434"
    echo "   OLLAMA_MODEL=llama3.2"
fi

echo ""

# ==========================================
# 8. Verificar instalação
# ==========================================

echo "🔍 Verificando instalação..."

python3 -c "
import sys
try:
    import fastapi
    import chromadb
    import sentence_transformers
    import openai
    import sklearn
    print('✅ Todas as dependências importadas com sucesso')
except ImportError as e:
    print(f'❌ Erro de importação: {e}')
    sys.exit(1)
"

echo ""

# ==========================================
# 9. Informações finais
# ==========================================

echo "========================================="
echo "  Instalação concluída! 🎉"
echo "========================================="
echo ""
echo "Próximos passos:"
echo ""
echo "1. Configure sua API Key (se ainda não configurou):"
echo "   nano .env"
echo ""
echo "2. Execute o servidor:"
echo "   ./run.sh"
echo ""
echo "   Ou manualmente:"
echo "   source venv/bin/activate"
echo "   uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "3. Acesse no navegador:"
echo "   http://localhost:8000"
echo ""
echo "   Para outros dispositivos na rede:"
echo "   http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo "Para parar o servidor, pressione Ctrl+C"
echo ""
echo "========================================="
echo "  Bons estudos! 📚"
echo "========================================="
