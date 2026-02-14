# ==========================================
# PDF Consultor - Prompt Manager
# ==========================================
# Gerenciador centralizado de prompts com CoT e Few-Shot
# ==========================================

from typing import Dict, Any, List, Optional
from enum import Enum


class DocType(str, Enum):
    """Tipos de documentos para prompts personalizados"""
    JURIDICO = "jurídico"
    FINANCEIRO = "financeiro"
    TECNICO = "técnico"
    GERAL = "geral"


class DetailLevel(str, Enum):
    """Níveis de detalhe para resumos"""
    BRIEF = "breve"
    MEDIUM = "médio"
    DETAILED = "detalhado"


class PromptManager:
    """
    Gerenciador centralizado de prompts para o PDF Consultor

    Funcionalidades:
    - Prompts por tipo de documento
    - Chain of Thought (CoT) estruturado
    - Few-Shot Learning
    - Validação de respostas
    """

    # ==========================================
    # Prompts de System
    # ==========================================

    SYSTEM_PROMPTS = {
        DocType.JURIDICO: """Você é um assistente especializado em análise jurídica de documentos.

Sua abordagem:
1. Analise a pergunta com cuidado, identificando conceitos jurídicos relevantes
2. Identifique os trechos do documento que contêm fundamentação legal, precedentes ou argumentos
3. Raciocine sobre a relação entre os trechos e a pergunta
4. Formule uma resposta clara, precisa e fundamentada
5. Sempre cite a página fonte no formato [Página X]
6. Se houver conflito de informações, mencione ambas as fontes
7. Se não encontrar a resposta, diga explicitamente "Não encontrei esta informação no documento"
8. Mantenha o tom profissional, técnico e formal

Foco:
- Identificar fundamentação legal e precedentes
- Analisar argumentos e contra-argumentos
- Citar dispositivos legais quando aplicável
- Notificar prazos e procedimentos jurídicos""",

        DocType.FINANCEIRO: """Você é um assistente especializado em análise financeira de documentos.

Sua abordagem:
1. Analise a pergunta identificando dados numéricos e indicadores financeiros
2. Identifique os trechos com valores, prazos, taxas e condições
3. Raciocine sobre tendências, comparações e impacto financeiro
4. Formule uma resposta objetiva e analítica
5. Sempre cite a página fonte no formato [Página X]
6. Se houver múltiplos cenários, analise cada um separadamente
7. Se não encontrar a resposta, diga explicitamente "Não encontrei esta informação no documento"
8. Mantenha o tom profissional, analítico e detalhado

Foco:
- Identificar valores, totais e comparações
- Analisar indicadores financeiros e tendências
- Notificar prazos, datas e períodos relevantes
- Calcular totais e comparações quando aplicável""",

        DocType.TECNICO: """Você é um assistente especializado em análise técnica de documentos.

Sua abordagem:
1. Analise a pergunta identificando conceitos técnicos e especificações
2. Identifique os trechos com especificações, procedimentos e requisitos técnicos
3. Raciocine sobre relações de causa-efeito e conformidades
4. Formule uma resposta clara, técnica e esclarecedora
5. Sempre cite a página fonte no formato [Página X]
6. Explique termos técnicos quando necessário
7. Se não encontrar a resposta, diga explicitamente "Não encontrei esta informação no documento"
8. Mantenha o tom profissional, estruturado e educativo

Foco:
- Identificar especificações técnicas e procedimentos
- Analisar conformidades e padrões
- Explicar termos técnicos e processos
- Notificar requisitos e dependências""",

        DocType.GERAL: """Você é um assistente especializado em analisar e responder perguntas sobre documentos.

Sua abordagem:
1. Analise a pergunta com cuidado
2. Identifique os trechos do documento que respondem à pergunta
3. Raciocine sobre a relação entre os trechos e a pergunta
4. Formule uma resposta clara e precisa
5. Sempre cite a página fonte no formato [Página X]
6. Se houver conflito de informações, mencione ambas as fontes
7. Se não encontrar a resposta, diga explicitamente "Não encontrei esta informação no documento"
8. Mantenha o tom profissional, claro e objetivo

Restrições:
- Baseie-se APENAS no contexto fornecido
- Não invente informações externas ao documento
- Seja conciso mas completo"""
    }

    # ==========================================
    # Prompts de Chat com CoT
    # ==========================================

    def get_chat_prompt_with_cot(
        self,
        query: str,
        context: str,
        doc_title: str,
        page_count: int,
        category: DocType = DocType.GERAL,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, str]:
        """
        Gera prompt de chat com Chain of Thought estruturado

        Args:
            query: Pergunta do usuário
            context: Contexto do documento (chunks)
            doc_title: Título do documento
            page_count: Número de páginas
            category: Tipo de documento
            history: Histórico de conversa (últimas 10 trocas)

        Returns:
            Dict com prompts separados para CoT e resposta final
        """
        # Prompt de system
        system_prompt = self.SYSTEM_PROMPTS.get(category, self.SYSTEM_PROMPTS[DocType.GERAL])

        # Histórico formatado
        history_text = ""
        if history:
            history_text = "\n\nHistórico de conversa (últimas 10 trocas):\n"
            for msg in history[-10:]:
                role = "USUÁRIO" if msg.get("role") == "user" else "ASSISTENTE"
                content = msg.get("content", "")[:500]  # Limitar para economizar tokens
                history_text += f"{role}: {content}\n"

        # Prompt completo
        full_prompt = f"""## CONTEXTO DO DOCUMENTO

**Documento:** {doc_title}
**Total de páginas:** {page_count}
**Categoria:** {category.value}

---

Trechos relevantes do documento:

{context}

---

{history_text}

## PERGUNTA DO USUÁRIO

{query}

---

## INSTRUÇÕES

### Etapa 1: Raciocínio (Chain of Thought)
Analise a pergunta e os trechos fornecidos seguindo estas etapas:

1. **Identificação de Trechos Relevantes:**
   - Liste os trechos que diretamente respondem à pergunta
   - Note a página de cada trecho

2. **Análise da Relação:**
   - Explique como cada trecho se relaciona com a pergunta
   - Identifique informações complementares ou contraditórias

3. **Síntese do Raciocínio:**
   - Combine as informações dos trechos relevantes
   - Formule uma resposta preliminar baseada nos trechos

### Etapa 2: Resposta Direta
Com base no seu raciocínio, forneça uma resposta clara e direta ao usuário:

1. **Resposta:**
   - Responda à pergunta de forma clara e concisa
   - Sempre cite a página no formato [Página X]
   - Seja objetivo e direto

2. **Fontes:**
   - Liste as páginas utilizadas: [Página X], [Página Y], ...
   - Se aplicável, identifique trechos específicos

3. **Avisos:**
   - Se houver conflitos ou informações ambíguas, mencione
   - Se a informação não estiver completa, note o que falta

---

**Formato da Resposta:**

[RACIOCÍNIO]
[Trechos Identificados]
- Trecho 1 (Página X): [resumo ou citação]
- Trecho 2 (Página Y): [resumo ou citação]

[Análise da Relação]
[Explique a conexão entre os trechos e a pergunta]

[Conclusão Preliminar]
[Resposta inicial baseada nos trechos]

[RESPOSTA DIRETA]
[Resposta clara e concisa]

[Fontes]
- [Página X]: [breve descrição do conteúdo]
- [Página Y]: [breve descrição do conteúdo]

[Avisos]
[Quaisquer conflitos ou ambiguidades]

---

**Responda no formato acima.**"""

        return {
            "system": system_prompt,
            "user": full_prompt
        }

    def get_chat_prompt_simple(
        self,
        query: str,
        context: str,
        doc_title: str,
        page_count: int,
        category: DocType = DocType.GERAL
    ) -> str:
        """
        Gera prompt de chat simples (sem CoT explícito)

        Útil para respostas mais rápidas com menos tokens
        """
        system_prompt = self.SYSTEM_PROMPTS.get(category, self.SYSTEM_PROMPTS[DocType.GERAL])

        full_prompt = f"""## CONTEXTO DO DOCUMENTO

**Documento:** {doc_title}
**Total de páginas:** {page_count}

---

Trechos relevantes do documento:

{context}

---

## PERGUNTA DO USUÁRIO

{query}

---

## INSTRUÇÕES

Com base nos trechos acima, responda à pergunta do usuário:

1. **Resposta:** Forneça uma resposta clara e precisa
2. **Citação:** Sempre cite a página no formato [Página X]
3. **Clareza:** Seja conciso mas completo
4. **Honestidade:** Se a informação não estiver no documento, diga "Não encontrei esta informação no documento"

---

RESPOSTA:"""

        return full_prompt

    # ==========================================
    # Prompts de Resumo
    # ==========================================

    SUMMARY_INSTRUCTIONS = {
        DetailLevel.BRIEF: {
            "instruction": "um resumo breve (1-2 parágrafos, máximo 150 palavras)",
            "structure": "Tema principal + pontos-chave (máx. 5 bullets)",
            "focus": "Apenas informações essenciais e mais importantes",
            "length_limit": 150
        },
        DetailLevel.MEDIUM: {
            "instruction": "um resumo detalhado (3-5 parágrafos, máximo 300 palavras)",
            "structure": "Introdução + desenvolvimento + conclusão (com seções numeradas)",
            "focus": "Informações principais com contexto suficiente para entender o documento",
            "length_limit": 300
        },
        DetailLevel.DETAILED: {
            "instruction": "um resumo completo e abrangente (500-700 palavras)",
            "structure": "Título + seções temáticas + conclusão + pontos-chave destacados",
            "focus": "Todas as informações relevantes, incluindo detalhes específicos",
            "length_limit": 700
        }
    }

    def get_summary_prompt(
        self,
        content: str,
        doc_title: str,
        page_count: int,
        detail_level: DetailLevel = DetailLevel.MEDIUM,
        category: DocType = DocType.GERAL
    ) -> str:
        """
        Gera prompt para geração de resumo

        Args:
            content: Conteúdo do documento (chunks ou texto completo)
            doc_title: Título do documento
            page_count: Número de páginas
            detail_level: Nível de detalhe desejado
            category: Tipo de documento

        Returns:
            Prompt formatado
        """
        system_prompt = self.SYSTEM_PROMPTS.get(category, self.SYSTEM_PROMPTS[DocType.GERAL])

        instructions = self.SUMMARY_INSTRUCTIONS[detail_level]

        full_prompt = f"""## CONTEXTO DO DOCUMENTO

**Documento:** {doc_title}
**Total de páginas:** {page_count}
**Categoria:** {category.value}

---

Conteúdo do documento:

{content}

---

## INSTRUÇÕES

Crie um resumo do documento acima seguindo estas diretrizes:

**Nível de Detalhe:** {instructions['instruction']}
**Estrutura Exigida:** {instructions['structure']}
**Foco:** {instructions['focus']}
**Limite de palavras:** {instructions['length_limit']}

### Formato da Resposta

# RESUMO: {doc_title}

## Tema Principal
[1-2 frases descrevendo o assunto central do documento]

## {instructions['structure']}

[Desenvolva o resumo aqui seguindo a estrutura especificada]

## Pontos-Chave
• [Ponto 1]
• [Ponto 2]
• [Ponto 3]
...

---

RESUMO:"""

        return full_prompt

    # ==========================================
    # Prompts RAPTOR
    # ==========================================

    RAPTOR_LEVEL_DESCRIPTIONS = {
        1: "primeiro nível de síntese (agrupando trechos relacionados)",
        2: "segundo nível de síntese (criando temas abstratos)",
        3: "terceiro nível de síntese (desenvolvendo conceitos de alto nível)",
        4: "quarto nível de síntese (criando resumo executivo final)"
    }

    def get_raptor_prompt(
        self,
        chunks: List[str],
        level: int = 1,
        context: str = ""
    ) -> str:
        """
        Gera prompt para síntese RAPTOR

        Args:
            chunks: Lista de chunks a serem sintetizados
            level: Nível da hierarquia RAPTOR
            context: Contexto adicional (sínteses de níveis anteriores)

        Returns:
            Prompt formatado
        """
        level_desc = self.RAPTOR_LEVEL_DESCRIPTIONS.get(
            level,
            f"nível {level} de síntese"
        )

        # Format chunks
        chunks_formatted = "\n\n".join([
            f"[Trecho {i+1}] {chunk}"
            for i, chunk in enumerate(chunks)
        ])

        full_prompt = f"""Você é um assistente especializado em criar sínteses hierárquicas de documentos.

### Contexto
{context}

### Tarefa
Crie uma síntese dos trechos abaixo no nível {level}: {level_desc}

### Conteúdo
{chunks_formatted}

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

SÍNTESE:"""

        return full_prompt

    # ==========================================
    # Few-Shot Examples
    # ==========================================

    CHAT_EXAMPLES = {
        DocType.JURIDICO: """### Exemplo de Resposta Correta

**USUÁRIO:** Qual é o prazo de prescrição mencionado no contrato?

**CONTEXTO:**
[Página 3] O prazo de prescrição das ações é de 10 anos, conforme artigo 205 do Código Civil.
[Página 7] No caso específico deste contrato, o prazo começa a contar da data de assinatura.

**ASSISTENTE (Resposta Correta):**

[RACIOCÍNIO]
[Trechos Identificados]
- Trecho 1 (Página 3): O prazo geral de prescrição é de 10 anos (artigo 205 do CC)
- Trecho 2 (Página 7): Neste contrato, o prazo começa da data de assinatura

[Análise da Relação]
O contrato define que o prazo de prescrição começa a contar da assinatura, aplicando-se o prazo geral de 10 anos sobre essa data de início.

[Conclusão Preliminar]
Considerando a data de assinatura do contrato (15/01/2015) e o prazo de 10 anos, a prescrição ocorreria em 15/01/2025. No entanto, hoje é 12/02/2026, o que indica que o contrato ainda está dentro do prazo prescricional.

[RESPOSTA DIRETA]
O prazo de prescrição mencionado no contrato é de 10 anos, conforme o artigo 205 do Código Civil [Página 3]. No caso deste contrato, o prazo de prescrição começou a contar da data de assinatura [Página 7].

Considerando a data de assinatura em 15/01/2015, o prazo de prescrição se encerraria em 15/01/2025. Como hoje é 12/02/2026, o contrato ainda está dentro do prazo prescricional.

[Fontes]
- [Página 3]: Prazo de prescrição de 10 anos (artigo 205 do Código Civil)
- [Página 7]: Início do prazo de prescrição a partir da data de assinatura

[Avisos]
Verificar se houve alguma interrupção ou suspensão do prazo prescricional não mencionada nestes trechos.""",

        DocType.FINANCEIRO: """### Exemplo de Resposta Correta

**USUÁRIO:** Qual é o valor total do contrato?

**CONTEXTO:**
[Página 3] O valor do contrato é de R$ 50.000,00, conforme cláusula 2.1.
[Página 5] Considerando adicional de 10%, o valor final é R$ 55.000,00.

**ASSISTENTE (Resposta Correta):**

[RACIOCÍNIO]
[Trechos Identificados]
- Trecho 1 (Página 3): Valor base do contrato de R$ 50.000,00
- Trecho 2 (Página 5): Adicional de 10% aplicado

[Análise da Relação]
O contrato estabelece um valor base de R$ 50.000,00 (Página 3). Há um adicional de 10% mencionado na Página 5 que deve ser aplicado sobre esse valor.

[Conclusão Preliminar]
Valor adicional: 10% de R$ 50.000,00 = R$ 5.000,00
Valor final: R$ 50.000,00 + R$ 5.000,00 = R$ 55.000,00

[RESPOSTA DIRETA]
O valor total do contrato é de R$ 55.000,00 (Página 5), composto pelo valor base de R$ 50.000,00 (Página 3) acrescido de adicional de 10%.

[Fontes]
- [Página 3]: Valor base do contrato: R$ 50.000,00
- [Página 5]: Valor final com adicional de 10%: R$ 55.000,00

[Avisos]
Nenhum."""
    }

    def get_chat_prompt_with_fewshot(
        self,
        query: str,
        context: str,
        doc_title: str,
        page_count: int,
        category: DocType = DocType.GERAL,
        history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Gera prompt de chat com exemplos few-shot

        Args:
            query: Pergunta do usuário
            context: Contexto do documento
            doc_title: Título do documento
            page_count: Número de páginas
            category: Tipo de documento
            history: Histórico de conversa

        Returns:
            Prompt com exemplos few-shot
        """
        system_prompt = self.SYSTEM_PROMPTS.get(category, self.SYSTEM_PROMPTS[DocType.GERAL])

        # Obter exemplos few-shot para categoria
        examples = self.CHAT_EXAMPLES.get(category, "")

        # Histórico formatado
        history_text = ""
        if history:
            history_text = "\n\nHistórico de conversa (últimas 10 trocas):\n"
            for msg in history[-10:]:
                role = "USUÁRIO" if msg.get("role") == "user" else "ASSISTENTE"
                content = msg.get("content", "")[:500]
                history_text += f"{role}: {content}\n"

        # Prompt completo
        full_prompt = f"""{examples}

---

## CONTEXTO DO DOCUMENTO

**Documento:** {doc_title}
**Total de páginas:** {page_count}

---

Trechos relevantes do documento:

{context}

---

{history_text}

## PERGUNTA DO USUÁRIO

{query}

---

## INSTRUÇÕES

Com base nos trechos acima e seguindo o exemplo fornecido, responda à pergunta do usuário:

1. **Raciocínio:** Analise os trechos relevantes e explique seu raciocínio
2. **Resposta:** Forneça uma resposta clara e precisa
3. **Citação:** Sempre cite a página no formato [Página X]
4. **Formato:** Siga o formato do exemplo acima ([RACIOCÍNIO] e [RESPOSTA DIRETA])

---

RESPOSTA:"""

        return full_prompt

    # ==========================================
    # Validação de Resposta
    # ==========================================

    def validate_response(
        self,
        response: str,
        query: str,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Valida se a resposta atende aos requisitos mínimos

        Args:
            response: Resposta gerada pelo LLM
            query: Pergunta original
            chunks: Chunks utilizados como contexto

        Returns:
            Dict com validação e feedback
        """
        issues = []
        warnings = []
        score = 0

        # Verifica se cita páginas
        has_page_citation = "[Página" in response or "página" in response.lower()
        if not has_page_citation:
            issues.append("Resposta não cita páginas do documento")
        else:
            score += 20

        # Verifica tamanho da resposta
        if len(response) < 50:
            issues.append("Resposta muito curta")
        elif len(response) > 2000:
            warnings.append("Resposta muito longa, considere resumir")
        else:
            score += 20

        # Verifica se responde à pergunta
        query_lower = query.lower()
        response_lower = response.lower()

        # Palavras-chave da query (primeiras 3)
        query_keywords = [word for word in query_lower.split() if len(word) > 3][:3]

        keywords_found = sum(1 for keyword in query_keywords if keyword in response_lower)

        if keywords_found >= len(query_keywords) * 0.5:
            score += 40
        elif keywords_found == 0:
            issues.append("Resposta parece não responder à pergunta")
        else:
            warnings.append(f"Resposta parcial: {keywords_found}/{len(query_keywords)} palavras-chave encontradas")

        # Verifica se usa apenas contexto
        if "não encontrei" in response.lower() and chunks:
            # Se há chunks mas não encontrou, pode estar ok
            score += 20
        elif chunks and "não encontrei" not in response.lower():
            score += 20

        # Classificar qualidade
        if score >= 80:
            quality = "Excelente"
        elif score >= 60:
            quality = "Boa"
        elif score >= 40:
            quality = "Aceitável"
        else:
            quality = "Ruim"

        return {
            "valid": len(issues) == 0,
            "quality": quality,
            "score": score,
            "issues": issues,
            "warnings": warnings
        }

    # ==========================================
    # Utilitários
    # ==========================================

    @staticmethod
    def format_chunks_for_prompt(chunks: List[Dict[str, Any]], max_per_chunk: int = 500) -> str:
        """
        Formata chunks para inserção no prompt

        Args:
            chunks: Lista de chunks com metadados
            max_per_chunk: Máximo de caracteres por chunk

        Returns:
            Chunks formatados para o prompt
        """
        formatted = []
        for i, chunk in enumerate(chunks, 1):
            page = chunk.get("metadata", {}).get("page", "N/A")
            text = chunk.get("text", "")

            # Truncar se necessário
            if len(text) > max_per_chunk:
                text = text[:max_per_chunk] + "..."

            formatted.append(f"[Trecho {i} - Página {page}]\n{text}")

        return "\n\n".join(formatted)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estima número de tokens em um texto
        Aproximação: 1 token ≈ 4 caracteres para português
        """
        return len(text) // 4


# Instância global do gerenciador de prompts
prompt_manager = PromptManager()
