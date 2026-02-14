# 📝 Análise de Prompts e Chain of Thought - PDF Consultor

**Data:** 2026-02-12 01:20 UTC
**Versão:** 1.0.0
**Status:** ✅ Funcional

---

## 🎯 Resumo Executivo

| Aspecto | Status | Avaliação |
|----------|--------|-----------|
| **Prompts de Chat** | ✅ Implementado | ⚠️ Básico, pode ser melhorado |
| **Prompts de Resumo** | ✅ Implementado | ⚠️ Básico, sem CoT explícito |
| **Chain of Thought** | ⚠️ Parcial | ⚠️ Implicito no contexto, não estruturado |
| **RAPTOR Prompts** | ✅ Implementado | ✅ Adequado para clustering |
| **Consistência** | ⚠️ Média | ⚠️ Prompts dispersos nos arquivos |

---

## 📊 Análise Detalhada

### 1. Prompts de Chat (`app/chat_service.py`)

#### Prompt Atual

**Prompt System:**
```python
"Você é um assistente especializado em responder perguntas sobre documentos."
```

**Prompt do Usuário:**
```python
prompt_parts = [
    "Você é um assistente especializado em responder perguntas sobre documentos PDF.",
    "Você deve responder baseando-se APENAS no contexto fornecido abaixo.",
    "Se a informação não estiver no contexto, diga que não encontrou a resposta.",
    "Seja claro, conciso e cite a página das informações quando possível.",
    "",
    "CONTEXTO DO DOCUMENTO:",
    context,
    "",
    "HISTÓRICO DE CONVERSA:",
    # ... histórico ...
    "PERGUNTA ATUAL:\n{query}",
    "RESPOSTA:"
]
```

#### ⚠️ Problemas Identificados

1. **Sem instrução explícita de Chain of Thought**
   - O modelo não é orientado a raciocinar passo a passo
   - Gera resposta direta sem mostrar o processo

2. **Instrução de citação vaga**
   - "cite a página das informações quando possível"
   - Não especifica formato desejado (ex: `[Página X]`)

3. **Sem instruções de incerteza**
   - Não há orientação para quando o modelo tem baixa confiança
   - Deve pedir esclarecimentos

4. **Prompt system muito genérico**
   - "assistente especializado em responder perguntas"
   - Pode ser mais específico sobre o tipo de documento

#### ✅ Sugestões de Melhoria

**Prompt System Aprimorado:**
```python
"""Você é um assistente especializado em analisar e responder perguntas sobre documentos jurídicos, financeiros e técnicos.

Sua abordagem:
1. Analise a pergunta com cuidado
2. Identifique os trechos relevantes no contexto
3. Raciocine sobre a relação entre os trechos e a pergunta
4. Formule uma resposta clara e precisa
5. Sempre cite a página fonte no formato [Página X]
6. Se houver conflito de informações, mencione ambas as fontes
7. Se não encontrar a resposta, diga explicitamente
8. Mantenha o tom profissional e objetivo

Restrições:
- Baseie-se APENAS no contexto fornecido
- Não invente informações externas ao documento
- Seja conciso mas completo"""
```

**Prompt do Usuário com CoT Estruturado:**
```python
prompt_parts = [
    "## CONTEXTO DO DOCUMENTO",
    "",
    f"Documento: {document_title}",
    f"Total de páginas: {page_count}",
    "",
    "Trechos relevantes do documento:",
    "",
]

# Adicionar trechos com citação explícita
for i, chunk in enumerate(chunks, 1):
    prompt_parts.append(f"[Trecho {i} - Página {chunk['page']}]")
    prompt_parts.append(chunk['text'][:500])  # Limitar tamanho
    prompt_parts.append("")

prompt_parts.extend([
    "",
    "## PERGUNTA DO USUÁRIO",
    f"{query}",
    "",
    "## INSTRUÇÕES DE RESPOSTA",
    "",
    "1. **Raciocínio (Chain of Thought):**",
    "   - Liste os trechos relevantes encontrados",
    "   - Explique como cada trecho responde à pergunta",
    "   - Indique se há conflitos ou informações complementares",
    "",
    "2. **Resposta Direta:**",
    "   - Forneça uma resposta clara e concisa",
    "   - Sempre cite a página no formato [Página X]",
    "   - Seja objetivo e direto",
    "",
    "3. **Fontes:**",
    "   - Liste as páginas utilizadas: [Página X], [Página Y], ...",
    "",
    "Agora, forneça sua resposta no formato acima.",
])
```

---

### 2. Prompts de Resumo (`app/chat_service.py` & `app/raptor_service.py`)

#### Prompt Atual (Sumarização)

```python
prompt = f"""Resuma o seguinte documento de forma {detail_level}:

{combined_text}

RESUMO:"""
```

#### ⚠️ Problemas Identificados

1. **Sem instruções de estrutura**
   - Não especifica como organizar o resumo
   - Pode resultar em texto desorganizado

2. **Sem instruções de foco**
   - Não há orientação sobre o que priorizar
   - Pode incluir informações irrelevantes

3. **Sem verificação de qualidade**
   - Não pede para identificar informações principais vs. secundárias

#### ✅ Sugestões de Melhoria

**Prompt Aprimorado:**
```python
detail_prompt_map = {
    "brief": {
        "instruction": "um resumo breve (1-2 parágrafos, máximo 150 palavras)",
        "structure": "Tema principal + pontos-chave (máx. 5 bullets)",
        "focus": "Apenas informações essenciais"
    },
    "medium": {
        "instruction": "um resumo detalhado (3-5 parágrafos, máximo 300 palavras)",
        "structure": "Introdução + desenvolvimento + conclusão (com seções numeradas)",
        "focus": "Informações principais com contexto suficiente"
    },
    "detailed": {
        "instruction": "um resumo completo e abrangente (500-700 palavras)",
        "structure": "Título + seções temáticas + conclusão + pontos-chave destacados",
        "focus": "Todas as informações relevantes, incluindo detalhes específicos"
    }
}

detail_config = detail_prompt_map[detail_level]

prompt = f"""Você é um assistente especializado em criar resumos estruturados de documentos.

### Tarefa
Crie um resumo do documento abaixo seguindo estas instruções:

**Nível de Detalhe:** {detail_config['instruction']}
**Estrutura Exigida:** {detail_config['structure']}
**Foco:** {detail_config['focus']}

### Conteúdo do Documento
{combined_text}

### Formato da Resposta
Use o seguinte formato:

# RESUMO: {document_title}

## Tema Principal
[1-2 frases descrevendo o assunto central do documento]

## {Estrutura conforme nível escolhido}

[Desenvolva o resumo aqui seguindo a estrutura especificada]

## Pontos-Chave
• [Ponto 1]
• [Ponto 2]
• [Ponto 3]
...

---

RESUMO:"""
```

---

### 3. Prompts RAPTOR (`app/raptor_service.py`)

#### Prompt Atual

```python
prompt = f"""Você é um assistente especializado em resumir documentos.

{context}

Abaixo estão trechos de um documento que devem ser resumidos em um único parágrafo coeso:

{combined_text}

RESUMO:"""
```

#### ⚠️ Problemas Identificados

1. **Contexto não utilizado**
   - `{context}` é definido mas raramente preenchido
   - Perde oportunidade de passar contexto de cluster anterior

2. **Sem instruções de coesão**
   - "único parágrafo coeso" é vago
   - Não especifica como conectar ideias

3. **Preso a um parágrafo**
   - Para resumos de múltiplos chunks, um parágrafo pode ser insuficiente

#### ✅ Sugestões de Melhoria

**Prompt Aprimorado:**
```python
def summarize_chunk_group(self, chunks: List[str], context: str = "", level: int = 1) -> str:
    """
    Prompt aprimorado para RAPTOR com CoT
    """

    # Descrever o nível para contexto
    level_description = {
        1: "primeiro nível de síntese (agrupando trechos relacionados)",
        2: "segundo nível de síntese (criando temas abstratos)",
        3: "terceiro nível de síntese (desenvolvendo conceitos de alto nível)"
    }

    combined_text = "\n\n".join([
        f"[Trecho {i+1}] {chunk}"
        for i, chunk in enumerate(chunks)
    ])

    prompt = f"""Você é um assistente especializado em criar sínteses hierárquicas de documentos.

### Contexto
{context}

### Tarefa
Crie uma síntese dos trechos abaixo no nível {level}: {level_description[level]}

### Conteúdo
{combined_text}

### Instruções
1. Identifique os temas comuns entre os trechos
2. Agrupe informações relacionadas
3. Sintetize em uma resposta coesa
4. Mantenha o nível de abstração apropriado
5. Preserve as informações essenciais

### Formato da Resposta
[SÍNTESE NÍVEL {level}]

[Tema Central: ...]

[Síntese em 2-3 frases conectadas]

---

RESUMO:"""

    # ... chamada ao LLM ...
```

---

### 4. Chain of Thought (CoT) - Situação Atual

#### Status: ⚠️ Implicito, não Estruturado

O sistema **NÃO implementa Chain of Thought explícito**. O raciocínio é:

1. **Implícito no prompt** - instrução geral para raciocinar
2. **Dependente do LLM** - modelo decide se mostrar raciocínio
3. **Sem estrutura definida** - não há formato fixo para CoT

#### Como Funciona Atualmente

```python
# chat_service.py - build_prompt()

prompt = """Você é um assistente especializado em responder perguntas sobre documentos PDF.
Você deve responder baseando-se APENAS no contexto fornecido abaixo.
Se a informação não estiver no contexto, diga que não encontrou a resposta.
Seja claro, conciso e cite a página das informações quando possível.

CONTEXTO DO DOCUMENTO:
{context}

PERGUNTA ATUAL:
{query}

RESPOSTA:"""
```

#### Por que CoT Não é Explícito

1. **RAG já filtra contexto**
   - RAG seleciona apenas chunks relevantes
   - CoT explícito pode ser redundante

2. **Latência**
   - CoT estruturado aumenta tempo de resposta
   - Tokens adicionais para raciocínio

3. **Custo**
   - CoT usa mais tokens do LLM
   - Aumenta custo de API

---

## 🚀 Recomendações de Melhoria

### Prioridade Alta

#### 1. Implementar CoT Estruturado (Opcional)

```python
# Novo método em chat_service.py

def build_cot_prompt(self, query: str, context: str, history: List[ChatMessage]) -> dict:
    """
    Gera prompts separados para raciocínio e resposta
    """

    cot_prompt = """Analise a pergunta e o contexto fornecido.

Pergunta: {query}

Trechos do Documento:
{context}

Instruções:
1. Identifique os trechos relevantes para responder à pergunta
2. Explique como cada trecho se relaciona com a pergunta
3. Note se há informações conflitantes
4. Liste as fontes utilizadas

Responda em formato estruturado:
[RACIOCÍNIO]
[Trechos Identificados]
- Trecho X (Página Y): [relação com a pergunta]

[Conclusão]
[Resposta preliminar baseada nos trechos]
"""

    answer_prompt = """Com base no seu raciocínio anterior, forneça uma resposta direta ao usuário.

Pergunta: {query}

Formato:
[RESPOSTA]
[Resposta clara e concisa]
[Fontes: Página X, Página Y, ...]
"""

    return {
        "cot": cot_prompt,
        "answer": answer_prompt
    }
```

**Uso:**
```python
def chat_with_cot(self, query: str, document_id: str, history: List[ChatMessage]):
    # 1. Gerar prompts separados
    prompts = self.build_cot_prompt(query, context, history)

    # 2. Primeira chamada - Raciocínio
    cot_response = self.llm_client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": "Você é um analista de documentos."},
            {"role": "user", "content": prompts["cot"]}
        ],
        temperature=0.1,
        max_tokens=500
    )

    # 3. Segunda chamada - Resposta final
    final_response = self.llm_client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": cot_response.choices[0].message.content},
            {"role": "user", "content": prompts["answer"]}
        ],
        temperature=0.3,
        max_tokens=1000
    )
```

#### 2. Criar Gerenciador de Prompts Centralizado

```python
# app/prompts.py

class PromptManager:
    """Gerenciador centralizado de prompts"""

    # Prompts de Chat
    CHAT_SYSTEM = """Você é um assistente especializado em analisar e responder perguntas sobre {doc_type}.

Sua abordagem:
1. Analise a pergunta com cuidado
2. Identifique os trechos relevantes no contexto
3. Raciocine sobre a relação entre os trechos e a pergunta
4. Formule uma resposta clara e precisa
5. Sempre cite a página fonte no formato [Página X]
6. Se houver conflito de informações, mencione ambas as fontes
7. Se não encontrar a resposta, diga explicitamente

Restrições:
- Baseie-se APENAS no contexto fornecido
- Não invente informações externas ao documento
- Seja conciso mas completo"""

    CHAT_USER = """## CONTEXTO DO DOCUMENTO

Documento: {title}
Total de páginas: {page_count}
Categoria: {category}

Trechos relevantes:
{chunks_formatted}

## PERGUNTA
{query}

## INSTRUÇÕES
Forneça uma resposta clara e precisa baseada nos trechos acima.
Cite sempre a página no formato [Página X].

## RESPOSTA"""

    # Prompts de Resumo
    SUMMARY_BRIEF = """Resuma o documento abaixo em 1-2 parágrafos (máx. 150 palavras).

Foco: Informações essenciais apenas.
Estrutura: Tema principal + até 5 bullets.

Documento:
{content}

RESUMO:"""

    SUMMARY_MEDIUM = """Resuma o documento abaixo em 3-5 parágrafos (máx. 300 palavras).

Estrutura: Introdução + desenvolvimento + conclusão (com seções numeradas).
Foco: Informações principais com contexto suficiente.

Documento:
{content}

RESUMO:"""

    SUMMARY_DETAILED = """Resuma o documento abaixo de forma completa (500-700 palavras).

Estrutura: Título + seções temáticas + conclusão + pontos-chave destacados.
Foco: Todas as informações relevantes, incluindo detalhes específicos.

Documento:
{content}

RESUMO:"""

    # Prompts RAPTOR
    RAPTOR_LEVEL_1 = """Sintetize os trechos abaixo no primeiro nível de abstração.

Contexto: {context}

Trechos:
{chunks}

Instruções:
- Identifique temas comuns
- Agrupe informações relacionadas
- Sintetize em 2-3 frases conectadas

SÍNTESE NÍVEL 1:"""

    RAPTOR_LEVEL_2 = """Sintetize os trechos abaixo no segundo nível de abstração.

Contexto: {context}

Resumos anteriores:
{previous_summaries}

Instruções:
- Desenvolva conceitos de alto nível
- Mantenha coesão entre resumos anteriores
- Abstraia detalhes específicos

SÍNTESE NÍVEL 2:"""

    RAPTOR_LEVEL_3 = """Sintetize os trechos abaixo no terceiro nível de abstração (resumo executivo).

Contexto: {context}

Resumos anteriores:
{previous_summaries}

Instruções:
- Desenvolva conceitos executivos
- Capture o essencial do documento
- Apresente como resumo executivo

RESUMO EXECUTIVO:"""

    @classmethod
    def get_chat_prompt(cls, doc_type="jurídico", **kwargs):
        """Retorna prompt formatado de chat"""
        return cls.CHAT_SYSTEM.format(doc_type=doc_type), cls.CHAT_USER.format(**kwargs)

    @classmethod
    def get_summary_prompt(cls, level="medium", **kwargs):
        """Retorna prompt formatado de resumo"""
        prompt_map = {
            "brief": cls.SUMMARY_BRIEF,
            "medium": cls.SUMMARY_MEDIUM,
            "detailed": cls.SUMMARY_DETAILED
        }
        return prompt_map[level].format(**kwargs)

    @classmethod
    def get_raptor_prompt(cls, level=1, **kwargs):
        """Retorna prompt formatado de RAPTOR"""
        prompt_map = {
            1: cls.RAPTOR_LEVEL_1,
            2: cls.RAPTOR_LEVEL_2,
            3: cls.RAPTOR_LEVEL_3
        }
        return prompt_map[level].format(**kwargs)
```

---

### Prioridade Média

#### 3. Adicionar Prompt de Instruções por Categoria

```python
# app/prompts.py

PROMPTS_BY_CATEGORY = {
    "juridico": """Você é um assistente especializado em análise jurídica.

Foco:
- Identificar fundamentação legal
- Notificar precedentes jurisprudenciais
- Analisar argumentos e contra-argumentos
- Citar dispositivos legais quando aplicável

Tom: Formal, preciso e técnico.""",

    "financeiro": """Você é um assistente especializado em análise financeira.

Foco:
- Identificar dados numéricos e tendências
- Analisar indicadores financeiros
- Notificar períodos e prazos
- Calcular totais e comparações quando aplicável

Tom: Objetivo, analítico e detalhado.""",

    "tecnico": """Você é um assistente especializado em análise técnica.

Foco:
- Identificar especificações técnicas
- Analisar procedimentos e processos
- Notificar conformidades e padrões
- Explicar termos técnicos quando necessário

Tom: Esclarecedor, estruturado e educativo.""",

    "outros": """Você é um assistente especializado em análise de documentos.

Foco:
- Identificar informações principais
- Sintetizar pontos-chave
- Clarificar ambiguidades
- Organizar informações logicamente

Tom: Claro, profissional e adaptável."""
}
```

#### 4. Adicionar Validação de Resposta

```python
# app/chat_service.py

def validate_response(self, response: str, query: str, chunks: List[dict]) -> dict:
    """
    Valida se a resposta contém as fontes citadas
    """
    issues = []

    # Verifica se cita páginas
    if "[Página" not in response and "página" not in response.lower():
        issues.append("Resposta não cita páginas do documento")

    # Verifica se responde à pergunta
    if len(response) < 50:
        issues.append("Resposta muito curta")

    # Verifica se usa apenas contexto
    # (simplificado - em produção seria mais complexo)

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": []  # Avisos não-críticos
    }
```

---

### Prioridade Baixa

#### 5. Adicionar Exemplos de Few-Shot nos Prompts

```python
# Prompts com exemplos para melhor performance

CHAT_WITH_EXAMPLES = """Você é um assistente especializado em responder perguntas sobre documentos.

Exemplo de resposta correta:

USUÁRIO: Qual é o valor total do contrato?

CONTEXTO:
[Página 3] O valor do contrato é de R$ 50.000,00, conforme cláusula 2.1.
[Página 5] Considerando adicional de 10%, o valor final é R$ 55.000,00.

ASSISTENTE: [RACIOCÍNIO]
- O contrato estabelece um valor base de R$ 50.000,00 (Página 3)
- Há um adicional de 10% mencionado na Página 5
- Valor adicional: 10% de R$ 50.000,00 = R$ 5.000,00
- Valor final: R$ 50.000,00 + R$ 5.000,00 = R$ 55.000,00

[RESPOSTA]
O valor total do contrato é de R$ 55.000,00 (Página 5), composto pelo valor base de R$ 50.000,00 (Página 3) acrescido de adicional de 10%.

---

Agora, responda à pergunta do usuário seguindo o mesmo padrão.

CONTEXTO:
{context}

PERGUNTA:
{query}

RESPOSTA:"""
```

---

## 📊 Comparação: Atual vs. Melhorias

| Aspecto | Atual | Com Melhorias |
|----------|--------|--------------|
| **Estrutura de Prompts** | Disperso nos arquivos | Centralizado em `prompts.py` |
| **CoT Explícito** | ❌ Não implementado | ✅ Opcional via `build_cot_prompt()` |
| **Instruções Específicas** | ⚠️ Genéricas | ✅ Por categoria e nível |
| **Few-Shot Learning** | ❌ Não implementado | ✅ Exemplos nos prompts |
| **Validação de Resposta** | ❌ Não implementado | ✅ `validate_response()` |
| **Formato de Citações** | Vago | ✅ Padronizado `[Página X]` |
| **Contexto de Categoria** | ❌ Não utilizado | ✅ System prompt adaptado |

---

## 🎯 Conclusão

### Status Atual: ⚠️ Funcional mas Pode ser Melhorado

**Pontos Fortes:**
- ✅ Sistema funcional e operacional
- ✅ RAG e RAPTOR implementados
- ✅ Busca híbrida eficiente

**Pontos Fracos:**
- ⚠️ Prompts básicos e genéricos
- ⚠️ Sem CoT estruturado
- ⚠️ Pouca personalização por categoria
- ⚠️ Instruções de citação vagas

### Recomendação Principal

**Implementar um gerenciador de prompts centralizado** (`app/prompts.py`) que:

1. Centralize todos os prompts
2. Permita personalização por categoria
3. Suporte CoT opcional
4. Inclua exemplos few-shot
5. Valide respostas geradas

### Impacto Estimado

| Métrica | Atual | Com Melhorias |
|----------|--------|--------------|
| Qualidade das respostas | 7/10 | 9/10 |
| Precisão de citações | 6/10 | 9/10 |
| Coerência do CoT | N/A | 8/10 |
| Custo (tokens) | Base | +20-30% |
| Latência | Base | +10-20% |

**Decisão:** Implementar melhorias gradualmente, começando pelo PromptManager centralizado.

---

**Documento criado:** 2026-02-12 01:20 UTC
**Próxima revisão:** Após implementar PromptManager
