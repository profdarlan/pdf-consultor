#!/bin/bash
# ==========================================
# PDF Consultor - Script de Execução
# ==========================================

# Ativar ambiente virtual
source venv/bin/activate

# Verificar se .env existe
if [ ! -f ".env" ]; then
    echo "❌ Arquivo .env não encontrado."
    echo "   Execute: cp .env.example .env"
    echo "   Edite .env e configure suas credenciais."
    exit 1
fi

# Iniciar servidor
echo "🚀 Iniciando PDF Consultor..."
echo "   Host: 0.0.0.0 (acesso LAN)"
echo "   Porta: 8000"
echo ""
echo "   Acesse: http://localhost:8000"
echo ""
echo "   Para outros dispositivos:"
echo "   http://$(hostname -I | awk '{print $1}' 2>/dev/null):8000"
echo ""
echo "Pressione Ctrl+C para parar."
echo "========================================="
echo ""

# Iniciar com uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
