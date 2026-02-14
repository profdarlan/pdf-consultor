// ==========================================
// PDF Consultor - Frontend JavaScript
// ==========================================

let currentDocument = null;
let currentCategory = 'all';
let chatHistory = [];

// API Base URL
const API_BASE = '/api';

// ==========================================
// Document Management
// ==========================================

async function loadDocuments() {
    try {
        const url = currentCategory === 'all'
            ? `${API_BASE}/documents`
            : `${API_BASE}/documents?category=${currentCategory}`;

        const response = await fetch(url);
        const data = await response.json();

        displayDocuments(data.documents);
    } catch (error) {
        console.error('Erro ao carregar documentos:', error);
        showNotification('Erro ao carregar documentos', 'error');
    }
}

function displayDocuments(documents) {
    const container = document.getElementById('document-list');

    if (documents.length === 0) {
        container.innerHTML = `
            <div class="text-center py-8 text-gray-500">
                <i class="fas fa-folder-open text-3xl mb-2"></i>
                <p>Nenhum documento encontrado</p>
            </div>
        `;
        return;
    }

    container.innerHTML = documents.map(doc => `
        <div class="document-card p-3 bg-gray-50 rounded-lg hover:bg-blue-50 cursor-pointer transition border border-gray-200"
             onclick="openDocument('${doc.id}')"
             data-id="${doc.id}">
            <div class="flex items-start space-x-3">
                <i class="fas fa-file-pdf text-2xl text-red-500 mt-1"></i>
                <div class="flex-1 min-w-0">
                    <h4 class="font-medium text-gray-800 truncate" title="${doc.title}">${doc.title}</h4>
                    <div class="flex items-center space-x-2 mt-1">
                        <span class="text-xs px-2 py-0.5 rounded-full ${getCategoryColor(doc.category)}">
                            ${getCategoryLabel(doc.category)}
                        </span>
                        <span class="text-xs text-gray-500">${doc.page_count} pgs</span>
                        ${doc.is_indexed ? '<span class="text-xs text-green-600"><i class="fas fa-check-circle"></i> Indexado</span>' : ''}
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

function getCategoryColor(category) {
    const colors = {
        'juridico': 'bg-purple-100 text-purple-700',
        'financeiro': 'bg-green-100 text-green-700',
        'tecnico': 'bg-blue-100 text-blue-700',
        'outros': 'bg-gray-100 text-gray-700'
    };
    return colors[category] || colors.outros;
}

function getCategoryLabel(category) {
    const labels = {
        'juridico': 'Jurídico',
        'financeiro': 'Financeiro',
        'tecnico': 'Técnico',
        'outros': 'Outros'
    };
    return labels[category] || category;
}

function filterByCategory(category) {
    currentCategory = category;

    // Update button styles
    document.querySelectorAll('.category-btn').forEach(btn => {
        if (btn.dataset.category === category) {
            btn.classList.add('active', 'bg-blue-100', 'text-blue-700');
            btn.classList.remove('bg-gray-100', 'text-gray-700');
        } else {
            btn.classList.remove('active', 'bg-blue-100', 'text-blue-700');
            btn.classList.add('bg-gray-100', 'text-gray-700');
        }
    });

    loadDocuments();
}

function refreshDocuments() {
    showNotification('Atualizando documentos...', 'info');
    loadDocuments();
}

// ==========================================
// Document Viewer
// ==========================================

async function openDocument(documentId) {
    try {
        const response = await fetch(`${API_BASE}/documents/${documentId}`);
        currentDocument = await response.json();

        // Update UI
        document.getElementById('doc-title').textContent = currentDocument.title;
        document.getElementById('doc-category').textContent = getCategoryLabel(currentDocument.category);
        document.getElementById('doc-category').className = `px-2 py-1 text-xs rounded-full ${getCategoryColor(currentDocument.category)}`;

        // Update breadcrumb
        document.getElementById('breadcrumb-current').classList.remove('hidden');
        document.getElementById('breadcrumb-doc-title').textContent = currentDocument.title;

        // Show document viewer, hide welcome screen
        document.getElementById('welcome-screen').classList.add('hidden');
        document.getElementById('document-viewer').classList.remove('hidden');

        // Load PDF
        const pdfUrl = `${API_BASE}/documents/${documentId}/download`;
        document.getElementById('pdf-frame').src = pdfUrl;

        // Clear chat
        chatHistory = [];
        document.getElementById('chat-messages').innerHTML = `
            <div class="text-center py-8 text-gray-500">
                <i class="fas fa-robot text-4xl mb-3 text-gray-300"></i>
                <p>Faça uma pergunta sobre o documento</p>
            </div>
        `;

    } catch (error) {
        console.error('Erro ao abrir documento:', error);
        showNotification('Erro ao abrir documento', 'error');
    }
}

function downloadDocument() {
    if (!currentDocument) return;

    window.open(`${API_BASE}/documents/${currentDocument.id}/download`, '_blank');
}

async function deleteDocument() {
    if (!currentDocument) return;

    if (!confirm(`Tem certeza que deseja excluir "${currentDocument.title}"?`)) {
        return;
    }

    try {
        await fetch(`${API_BASE}/documents/${currentDocument.id}`, {
            method: 'DELETE'
        });

        showNotification('Documento excluído com sucesso', 'success');

        // Reset UI
        currentDocument = null;
        document.getElementById('welcome-screen').classList.remove('hidden');
        document.getElementById('document-viewer').classList.add('hidden');

        // Reload document list
        loadDocuments();

    } catch (error) {
        console.error('Erro ao excluir documento:', error);
        showNotification('Erro ao excluir documento', 'error');
    }
}

// ==========================================
// Chat
// ==========================================

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const query = input.value.trim();

    if (!query || !currentDocument) return;

    // Add user message
    addChatMessage('user', query);

    // Clear input
    input.value = '';

    // Show typing indicator
    showTypingIndicator();

    try {
        const useRaptor = document.getElementById('use-raptor').checked;
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                document_id: currentDocument.id,
                query: query,
                history: chatHistory,
                use_raptor: useRaptor
            })
        });

        const data = await response.json();

        // Remove typing indicator
        hideTypingIndicator();

        // Add assistant message
        addChatMessage('assistant', data.answer);

        // Add to history
        chatHistory.push({ role: 'user', content: query });
        chatHistory.push({ role: 'assistant', content: data.answer });

        // Show sources if available
        if (data.sources && data.sources.length > 0) {
            showSources(data.sources);
        }

    } catch (error) {
        console.error('Erro ao enviar mensagem:', error);
        hideTypingIndicator();
        showNotification('Erro ao processar pergunta', 'error');
    }
}

function addChatMessage(role, content) {
    const container = document.getElementById('chat-messages');
    const isUser = role === 'user';

    const messageHtml = `
        <div class="flex ${isUser ? 'justify-end' : 'justify-start'}">
            <div class="max-w-[80%] ${isUser ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-800'} rounded-2xl px-4 py-3">
                <div class="flex items-start space-x-2">
                    <i class="fas ${isUser ? 'fa-user' : 'fa-robot'} mt-0.5"></i>
                    <div class="flex-1">
                        <p class="text-sm whitespace-pre-wrap">${content}</p>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Remove empty state if first message
    if (container.querySelector('.text-center')) {
        container.innerHTML = '';
    }

    container.insertAdjacentHTML('beforeend', messageHtml);
    container.scrollTop = container.scrollHeight;
}

function showTypingIndicator() {
    const container = document.getElementById('chat-messages');
    const indicator = `
        <div id="typing-indicator" class="flex justify-start">
            <div class="bg-gray-100 rounded-2xl px-4 py-3">
                <div class="typing-indicator flex space-x-1">
                    <span class="w-2 h-2 bg-gray-400 rounded-full"></span>
                    <span class="w-2 h-2 bg-gray-400 rounded-full"></span>
                    <span class="w-2 h-2 bg-gray-400 rounded-full"></span>
                </div>
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', indicator);
    container.scrollTop = container.scrollHeight;
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) indicator.remove();
}

function showSources(sources) {
    const container = document.getElementById('chat-messages');

    const sourcesHtml = `
        <div class="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
            <h4 class="text-sm font-semibold text-blue-800 mb-2 flex items-center space-x-2">
                <i class="fas fa-book"></i>
                <span>Fontes</span>
            </h4>
            ${sources.map(source => `
                <div class="text-sm mb-2 p-2 bg-white rounded border border-blue-200">
                    <div class="flex items-center justify-between mb-1">
                        <span class="font-medium text-blue-700">Página ${source.page}</span>
                        <span class="text-xs text-gray-500">Score: ${(source.score * 100).toFixed(0)}%</span>
                    </div>
                    <p class="text-gray-600 text-xs truncate">${source.snippet}</p>
                </div>
            `).join('')}
        </div>
    `;

    container.insertAdjacentHTML('beforeend', sourcesHtml);
    container.scrollTop = container.scrollHeight;
}

// ==========================================
// Summary
// ==========================================

async function generateSummary(detailLevel = 'medium') {
    if (!currentDocument) return;

    const contentDiv = document.getElementById('summary-content');

    contentDiv.innerHTML = `
        <div class="text-center py-8 text-gray-500">
            <i class="fas fa-spinner fa-spin text-2xl mb-2"></i>
            <p>Gerando resumo...</p>
        </div>
    `;

    try {
        const response = await fetch(`${API_BASE}/documents/${currentDocument.id}/summary`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                detail_level: detailLevel
            })
        });

        const data = await response.json();

        contentDiv.innerHTML = `
            <div class="prose max-w-none">
                <p class="text-gray-700 whitespace-pre-wrap">${data.summary}</p>
                <p class="text-sm text-gray-500 mt-4">Modelo: ${data.model} | Páginas: ${data.page_count}</p>
            </div>
        `;

    } catch (error) {
        console.error('Erro ao gerar resumo:', error);
        contentDiv.innerHTML = `
            <div class="text-center py-8 text-red-500">
                <i class="fas fa-exclamation-triangle text-2xl mb-2"></i>
                <p>Erro ao gerar resumo</p>
            </div>
        `;
    }
}

function copySummary() {
    const contentDiv = document.getElementById('summary-content');
    const text = contentDiv.textContent;

    navigator.clipboard.writeText(text).then(() => {
        showNotification('Resumo copiado para a área de transferência', 'success');
    }).catch(() => {
        showNotification('Erro ao copiar resumo', 'error');
    });
}

// ==========================================
// Upload
// ==========================================

async function uploadDocument() {
    const fileInput = document.getElementById('upload-file');
    const categorySelect = document.getElementById('upload-category');
    const parentSelect = document.getElementById('upload-parent');

    const file = fileInput.files[0];

    if (!file) {
        showNotification('Selecione um arquivo PDF', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('category', categorySelect.value);
    if (parentSelect.value) {
        formData.append('parent_id', parentSelect.value);
    }

    try {
        const response = await fetch(`${API_BASE}/documents/upload`, {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            showNotification('Documento uploadado com sucesso', 'success');
            hideUploadModal();

            // Reload documents
            loadDocuments();
        } else {
            throw new Error('Upload falhou');
        }

    } catch (error) {
        console.error('Erro ao fazer upload:', error);
        showNotification('Erro ao fazer upload', 'error');
    }
}

async function loadParentDocuments() {
    try {
        const response = await fetch(`${API_BASE}/documents`);
        const data = await response.json();

        const parentSelect = document.getElementById('upload-parent');
        parentSelect.innerHTML = '<option value="">Nenhum</option>' +
            data.documents
                .filter(doc => !doc.parent_id)
                .map(doc => `<option value="${doc.id}">${doc.title}</option>`)
                .join('');

    } catch (error) {
        console.error('Erro ao carregar documentos principais:', error);
    }
}

// ==========================================
// Edit
// ==========================================

async function saveEdit() {
    if (!currentDocument) return;

    const title = document.getElementById('edit-title').value;
    const category = document.getElementById('edit-category').value;

    try {
        await fetch(`${API_BASE}/documents/${currentDocument.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, category })
        });

        showNotification('Documento atualizado com sucesso', 'success');
        hideEditModal();

        // Reload current document info
        await openDocument(currentDocument.id);

        // Reload document list
        loadDocuments();

    } catch (error) {
        console.error('Erro ao atualizar documento:', error);
        showNotification('Erro ao atualizar documento', 'error');
    }
}

// ==========================================
// Modal Management
// ==========================================

function showUploadModal() {
    document.getElementById('upload-modal').classList.remove('hidden');
    document.getElementById('upload-modal').classList.add('flex');
    loadParentDocuments();
}

function hideUploadModal() {
    document.getElementById('upload-modal').classList.add('hidden');
    document.getElementById('upload-modal').classList.remove('flex');
    document.getElementById('upload-file').value = '';
}

function showSummaryModal() {
    document.getElementById('summary-modal').classList.remove('hidden');
    document.getElementById('summary-modal').classList.add('flex');
    generateSummary('medium');
}

function hideSummaryModal() {
    document.getElementById('summary-modal').classList.add('hidden');
    document.getElementById('summary-modal').classList.remove('flex');
}

function showEditModal() {
    if (!currentDocument) return;

    document.getElementById('edit-title').value = currentDocument.title;
    document.getElementById('edit-category').value = currentDocument.category;

    document.getElementById('edit-modal').classList.remove('hidden');
    document.getElementById('edit-modal').classList.add('flex');
}

function hideEditModal() {
    document.getElementById('edit-modal').classList.add('hidden');
    document.getElementById('edit-modal').classList.remove('flex');
}

function showNotes() {
    showNotification('Funcionalidade de anotações em desenvolvimento', 'info');
}

function showAttachments() {
    showNotification('Funcionalidade de anexos em desenvolvimento', 'info');
}

// ==========================================
// Notifications
// ==========================================

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');

    const colors = {
        'success': 'bg-green-500',
        'error': 'bg-red-500',
        'info': 'bg-blue-500',
        'warning': 'bg-yellow-500'
    };

    const icons = {
        'success': 'fa-check-circle',
        'error': 'fa-exclamation-circle',
        'info': 'fa-info-circle',
        'warning': 'fa-exclamation-triangle'
    };

    notification.className = `fixed top-4 right-4 ${colors[type]} text-white px-4 py-3 rounded-lg shadow-lg z-50 flex items-center space-x-2 animate-pulse`;
    notification.innerHTML = `
        <i class="fas ${icons[type]}"></i>
        <span>${message}</span>
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// ==========================================
// Initialize
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    loadDocuments();
});
