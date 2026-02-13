"""
SGL - Interpretador de Editais via Claude API
PRIORIDADE desde o início da implantação.

Este serviço utiliza a API do Claude (Anthropic) para:
1. Extrair itens estruturados de editais (PDF convertido em texto)
2. Classificar editais por relevância/segmento
3. Resumir objetos e condições do edital
4. Identificar requisitos de habilitação
"""
import json
import logging
import re
from decimal import Decimal
from typing import Optional

import anthropic

logger = logging.getLogger(__name__)


class EditalInterpreter:
    """
    Interpretador inteligente de editais usando Claude API.
    Extrai dados estruturados de texto de editais para alimentar
    o sistema de cotação automaticamente.
    """
    
    def __init__(self, api_key: str, model: str = 'claude-sonnet-4-5-20250929', max_tokens: int = 8000):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
    
    # =========================================================
    # EXTRAÇÃO DE ITENS DO EDITAL
    # =========================================================
    
    def extrair_itens(self, texto_edital: str, contexto: str = '') -> dict:
        """
        Extrai todos os itens de um edital convertido em texto.
        
        Args:
            texto_edital: Texto completo ou parcial do edital (tabelas de itens)
            contexto: Informações adicionais (número do pregão, órgão, etc.)
        
        Returns:
            dict com:
                - itens: lista de itens extraídos
                - resumo: resumo do objeto
                - total_itens: quantidade total
                - confianca: nível de confiança geral (0.0 a 1.0)
                - observacoes: notas sobre a extração
        """
        prompt = f"""Você é um especialista em licitações públicas brasileiras. 
Analise o texto a seguir, que é um edital ou parte de um edital de licitação pública, e extraia TODOS os itens de compra.

{f"Contexto adicional: {contexto}" if contexto else ""}

Para cada item, extraia as seguintes informações:
- numero_item: número sequencial do item (inteiro)
- descricao: descrição completa do produto/serviço
- codigo_referencia: código CATMAT, CATSER ou outro código de referência (se houver)
- quantidade: quantidade solicitada (número)
- unidade_compra: unidade de medida (UN, CX, KG, PCT, ML, LT, M, M2, M3, FR, TB, etc.)
- preco_unitario_maximo: preço unitário máximo/estimado (número com decimais)
- preco_total_maximo: preço total máximo/estimado (número com decimais)
- grupo_lote: número do lote/grupo se houver agrupamento

REGRAS IMPORTANTES:
1. Mantenha as descrições COMPLETAS como estão no edital, sem abreviar
2. Se o preço máximo não estiver explícito, use o valor estimado/referência
3. Se não houver preço, coloque null
4. Converta todas as quantidades para números (ex: "1.000" → 1000)
5. Se houver lotes/grupos, identifique corretamente
6. Inclua TODOS os itens, mesmo que pareçam repetidos
7. Para cada item, adicione um campo "confianca" (0.0 a 1.0) indicando sua confiança na extração

Responda EXCLUSIVAMENTE com um JSON válido, sem markdown, sem explicações:
{{
    "itens": [
        {{
            "numero_item": 1,
            "descricao": "...",
            "codigo_referencia": "...",
            "quantidade": 100,
            "unidade_compra": "UN",
            "preco_unitario_maximo": 10.50,
            "preco_total_maximo": 1050.00,
            "grupo_lote": "1",
            "confianca": 0.95
        }}
    ],
    "resumo_objeto": "Resumo conciso do objeto da licitação",
    "total_itens": 1,
    "confianca_geral": 0.90,
    "observacoes": "Notas sobre dificuldades ou ambiguidades encontradas"
}}

TEXTO DO EDITAL:
{texto_edital[:30000]}"""  # Limitar texto para não exceder contexto

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            
            texto_resposta = response.content[0].text.strip()
            
            # Limpar possíveis marcadores markdown
            texto_resposta = re.sub(r'^```json\s*', '', texto_resposta)
            texto_resposta = re.sub(r'\s*```$', '', texto_resposta)
            
            resultado = json.loads(texto_resposta)
            
            # Validar e normalizar
            resultado = self._normalizar_resultado_extracao(resultado)
            
            logger.info(
                f"Extração de itens: {resultado['total_itens']} itens encontrados | "
                f"Confiança: {resultado['confianca_geral']}"
            )
            return resultado
            
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear JSON da resposta Claude: {e}")
            return {
                'itens': [],
                'resumo_objeto': '',
                'total_itens': 0,
                'confianca_geral': 0.0,
                'observacoes': f'Erro ao interpretar resposta da IA: {str(e)}'
            }
        except anthropic.APIError as e:
            logger.error(f"Erro na API Claude: {e}")
            raise
    
    # =========================================================
    # CLASSIFICAÇÃO E TRIAGEM AUTOMÁTICA
    # =========================================================
    
    def classificar_relevancia(
        self, 
        objeto_licitacao: str, 
        segmentos_interesse: list[str],
        palavras_chave: list[str] = None
    ) -> dict:
        """
        Classifica se um edital é relevante para os segmentos de atuação da empresa.
        Útil para pré-triagem automática.
        
        Args:
            objeto_licitacao: Texto do objeto da licitação
            segmentos_interesse: Lista de segmentos que a empresa atua
            palavras_chave: Palavras-chave adicionais de interesse
        
        Returns:
            dict com relevancia (0-100), motivo, e sugestão de ação
        """
        prompt = f"""Você é um analista de licitações. Avalie se esta licitação é relevante para uma empresa que atua nos seguintes segmentos:

SEGMENTOS DA EMPRESA: {', '.join(segmentos_interesse)}
{f"PALAVRAS-CHAVE DE INTERESSE: {', '.join(palavras_chave)}" if palavras_chave else ""}

OBJETO DA LICITAÇÃO:
{objeto_licitacao}

Responda EXCLUSIVAMENTE com JSON válido:
{{
    "relevancia": 85,
    "motivo": "Explicação concisa de por que é ou não relevante",
    "segmentos_identificados": ["segmento1", "segmento2"],
    "sugestao": "aprovar" ou "rejeitar" ou "analisar_manualmente",
    "palavras_chave_encontradas": ["palavra1", "palavra2"]
}}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            texto = response.content[0].text.strip()
            texto = re.sub(r'^```json\s*', '', texto)
            texto = re.sub(r'\s*```$', '', texto)
            
            return json.loads(texto)
            
        except Exception as e:
            logger.error(f"Erro na classificação de relevância: {e}")
            return {
                'relevancia': 50,
                'motivo': 'Não foi possível classificar automaticamente',
                'segmentos_identificados': [],
                'sugestao': 'analisar_manualmente',
                'palavras_chave_encontradas': []
            }
    
    # =========================================================
    # RESUMO E ANÁLISE DO EDITAL
    # =========================================================
    
    def resumir_edital(self, texto_edital: str) -> dict:
        """
        Gera um resumo executivo do edital com informações-chave.
        
        Returns:
            dict com resumo, requisitos de habilitação, prazos, etc.
        """
        prompt = f"""Analise este edital de licitação pública e extraia as informações-chave.

Responda EXCLUSIVAMENTE com JSON válido:
{{
    "resumo_objeto": "Descrição concisa do que está sendo comprado",
    "modalidade": "Pregão Eletrônico / Concorrência / etc.",
    "criterio_julgamento": "Menor preço / Maior desconto / etc.",
    "prazo_entrega": "Prazo mencionado para entrega",
    "local_entrega": "Local de entrega mencionado",
    "vigencia_contrato": "Vigência do contrato",
    "garantias_exigidas": ["lista de garantias exigidas"],
    "documentos_habilitacao": ["lista de documentos necessários"],
    "condicoes_pagamento": "Condições de pagamento mencionadas",
    "permite_consorcio": true/false,
    "exclusivo_me_epp": true/false,
    "observacoes_importantes": ["pontos de atenção relevantes"],
    "riscos_identificados": ["possíveis riscos ou dificuldades"]
}}

TEXTO DO EDITAL:
{texto_edital[:25000]}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            texto = response.content[0].text.strip()
            texto = re.sub(r'^```json\s*', '', texto)
            texto = re.sub(r'\s*```$', '', texto)
            
            return json.loads(texto)
            
        except Exception as e:
            logger.error(f"Erro ao resumir edital: {e}")
            return {
                'resumo_objeto': 'Não foi possível gerar resumo automático',
                'observacoes_importantes': [str(e)]
            }
    
    # =========================================================
    # MATCHING DE PRODUTOS COM FORNECEDORES
    # =========================================================
    
    def sugerir_fornecedores(
        self,
        itens_edital: list[dict],
        catalogo_fornecedores: list[dict]
    ) -> list[dict]:
        """
        Sugere fornecedores do catálogo para cada item do edital,
        fazendo matching inteligente por descrição do produto.
        
        Args:
            itens_edital: Lista de itens extraídos do edital
            catalogo_fornecedores: Lista de fornecedores com seus produtos
        
        Returns:
            Lista com sugestões de fornecedor para cada item
        """
        # Limitar dados para não exceder contexto
        itens_resumidos = []
        for item in itens_edital[:50]:
            itens_resumidos.append({
                'numero_item': item.get('numero_item'),
                'descricao': item.get('descricao', '')[:200],
                'unidade_compra': item.get('unidade_compra'),
            })
        
        fornecedores_resumidos = []
        for f in catalogo_fornecedores[:30]:
            fornecedores_resumidos.append({
                'id': f.get('id'),
                'nome': f.get('razao_social', f.get('nome_fantasia', '')),
                'segmentos': f.get('segmentos', []),
                'produtos': f.get('produtos', [])[:10]  # Limitar produtos
            })
        
        prompt = f"""Você é um especialista em compras e licitações. 
Faça o matching entre os itens do edital e os fornecedores disponíveis no catálogo.

ITENS DO EDITAL:
{json.dumps(itens_resumidos, ensure_ascii=False, indent=2)}

FORNECEDORES DISPONÍVEIS:
{json.dumps(fornecedores_resumidos, ensure_ascii=False, indent=2)}

Para cada item, sugira os fornecedores mais adequados.
Responda com JSON:
{{
    "sugestoes": [
        {{
            "numero_item": 1,
            "fornecedores_sugeridos": [
                {{
                    "fornecedor_id": 1,
                    "motivo": "Atua no segmento e fornece produto similar",
                    "confianca": 0.85
                }}
            ]
        }}
    ]
}}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            texto = response.content[0].text.strip()
            texto = re.sub(r'^```json\s*', '', texto)
            texto = re.sub(r'\s*```$', '', texto)
            
            return json.loads(texto)
            
        except Exception as e:
            logger.error(f"Erro ao sugerir fornecedores: {e}")
            return {'sugestoes': []}
    
    # =========================================================
    # HELPERS INTERNOS
    # =========================================================
    
    def _normalizar_resultado_extracao(self, resultado: dict) -> dict:
        """Normaliza e valida o resultado da extração de itens."""
        itens = resultado.get('itens', [])
        
        for item in itens:
            # Garantir tipos numéricos
            for campo in ['quantidade', 'preco_unitario_maximo', 'preco_total_maximo']:
                valor = item.get(campo)
                if valor is not None:
                    try:
                        item[campo] = float(str(valor).replace(',', '.').replace(' ', ''))
                    except (ValueError, TypeError):
                        item[campo] = None
            
            # Garantir numero_item como inteiro
            try:
                item['numero_item'] = int(item.get('numero_item', 0))
            except (ValueError, TypeError):
                item['numero_item'] = 0
            
            # Normalizar unidade
            item['unidade_compra'] = (item.get('unidade_compra') or 'UN').upper().strip()
            
            # Garantir confiança
            try:
                item['confianca'] = min(1.0, max(0.0, float(item.get('confianca', 0.5))))
            except (ValueError, TypeError):
                item['confianca'] = 0.5
        
        resultado['itens'] = itens
        resultado['total_itens'] = len(itens)
        
        try:
            resultado['confianca_geral'] = min(1.0, max(0.0, float(resultado.get('confianca_geral', 0.5))))
        except (ValueError, TypeError):
            resultado['confianca_geral'] = 0.5
        
        return resultado


class PDFTextExtractor:
    """
    Extrai texto de PDFs para alimentar o EditalInterpreter.
    Suporta PDFs digitais e escaneados (via OCR).
    """
    
    @staticmethod
    def extrair_texto_pdfplumber(caminho_pdf: str) -> str:
        """Extrai texto de PDFs digitais usando pdfplumber."""
        try:
            import pdfplumber
            texto = []
            with pdfplumber.open(caminho_pdf) as pdf:
                for pagina in pdf.pages:
                    texto_pagina = pagina.extract_text()
                    if texto_pagina:
                        texto.append(texto_pagina)
                    
                    # Tentar extrair tabelas também
                    tabelas = pagina.extract_tables()
                    for tabela in tabelas:
                        for linha in tabela:
                            if linha:
                                texto.append(' | '.join(str(c) for c in linha if c))
            
            return '\n'.join(texto)
        except ImportError:
            logger.warning("pdfplumber não instalado. Use: pip install pdfplumber")
            return ''
        except Exception as e:
            logger.error(f"Erro ao extrair texto do PDF: {e}")
            return ''
    
    @staticmethod
    def extrair_texto_pymupdf(caminho_pdf: str) -> str:
        """Extrai texto usando PyMuPDF (fitz) — mais rápido."""
        try:
            import fitz  # PyMuPDF
            texto = []
            doc = fitz.open(caminho_pdf)
            for pagina in doc:
                texto.append(pagina.get_text())
            doc.close()
            return '\n'.join(texto)
        except ImportError:
            logger.warning("PyMuPDF não instalado. Use: pip install PyMuPDF")
            return ''
        except Exception as e:
            logger.error(f"Erro ao extrair texto com PyMuPDF: {e}")
            return ''
    
    @staticmethod
    def extrair_texto_ocr(caminho_pdf: str, idioma: str = 'por') -> str:
        """
        Extrai texto de PDFs escaneados usando OCR (Tesseract).
        Requer: tesseract-ocr + pytesseract + pdf2image
        """
        try:
            from pdf2image import convert_from_path
            import pytesseract
            
            imagens = convert_from_path(caminho_pdf, dpi=300)
            texto = []
            for img in imagens:
                texto_pagina = pytesseract.image_to_string(img, lang=idioma)
                if texto_pagina:
                    texto.append(texto_pagina)
            
            return '\n'.join(texto)
        except ImportError:
            logger.warning("Dependências OCR não instaladas. Use: pip install pytesseract pdf2image")
            return ''
        except Exception as e:
            logger.error(f"Erro no OCR: {e}")
            return ''
    
    @classmethod
    def extrair_texto_auto(cls, caminho_pdf: str) -> tuple[str, str]:
        """
        Tenta extrair texto automaticamente, primeiro digital, depois OCR.
        
        Returns:
            Tuple (texto, metodo) — texto extraído e método usado
        """
        # Tentar extração digital primeiro (mais rápido e preciso)
        texto = cls.extrair_texto_pymupdf(caminho_pdf)
        if not texto:
            texto = cls.extrair_texto_pdfplumber(caminho_pdf)
        
        if texto and len(texto.strip()) > 100:
            return texto, 'pdf_parser'
        
        # Fallback: OCR
        logger.info(f"PDF parece ser escaneado, usando OCR: {caminho_pdf}")
        texto_ocr = cls.extrair_texto_ocr(caminho_pdf)
        if texto_ocr:
            return texto_ocr, 'ocr'
        
        return '', 'falha'
