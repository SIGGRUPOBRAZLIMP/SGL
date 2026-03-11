"""
SGL - Download de Documentos de Editais

Baixa documentos das plataformas e envia para o Dropbox.
Suporta: PNCP, ComprasGov (via PNCP), BBMNET, Licitar Digital.

Fluxo:
  1. Detecta plataforma de origem do edital
  2. Baixa arquivos via API da plataforma
  3. Extrai texto do PDF (para uso pela IA)
  4. Upload para Dropbox em pasta organizada
  5. Salva referencias na tabela edital_arquivos (com texto_extraido)
"""
import logging
import os
import re
import time
from datetime import datetime, timezone
from threading import Thread

import requests

logger = logging.getLogger(__name__)

PNCP_API_BASE = "https://pncp.gov.br/pncp-api/v1"
DOWNLOAD_TIMEOUT = 30


# ============================================================
# EXTRACAO DE TEXTO DO PDF
# ============================================================

def _extrair_texto_pdf(pdf_bytes):
    """
    Extrai texto de bytes de um PDF.
    Tenta pdfplumber primeiro, depois PyMuPDF como fallback.
    """
    if not pdf_bytes or len(pdf_bytes) < 100:
        return ''

    if not pdf_bytes[:5] == b'%PDF-':
        logger.warning("Arquivo nao e PDF (header: %s)", pdf_bytes[:20])
        return ''

    texto = ''

    # Tentar pdfplumber
    try:
        import pdfplumber
        import io
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            paginas = []
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    paginas.append(t)
            texto = '\n\n'.join(paginas)
            if texto.strip():
                logger.info("pdfplumber extraiu %d chars de %d paginas", len(texto), len(pdf.pages))
                return texto.strip()
    except Exception as e:
        logger.warning("pdfplumber falhou: %s", e)

    # Fallback: PyMuPDF (fitz)
    try:
        import fitz
        import io
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        paginas = []
        for page in doc:
            t = page.get_text()
            if t:
                paginas.append(t)
        total_pages = doc.page_count
        doc.close()
        texto = '\n\n'.join(paginas)
        if texto.strip():
            logger.info("PyMuPDF extraiu %d chars de %d paginas", len(texto), total_pages)
            return texto.strip()
    except Exception as e:
        logger.warning("PyMuPDF falhou: %s", e)

    logger.warning("Nenhum extrator conseguiu obter texto do PDF (%d bytes)", len(pdf_bytes))
    return ''


# ============================================================
# FUNCOES AUXILIARES
# ============================================================

def _parse_pncp_info(edital):
    """Extrai CNPJ, ano e sequencial de um edital PNCP/ComprasGov."""
    cnpj = edital.orgao_cnpj
    ano = edital.ano_compra
    seq = edital.sequencial_compra

    if cnpj and ano and seq:
        cnpj_limpo = re.sub(r'[^0-9]', '', cnpj)
        return cnpj_limpo, int(ano), int(seq)

    ncp = edital.numero_controle_pncp
    if ncp:
        match = re.match(r'^(\d{14})-\d+-(\d+)/(\d{4})$', ncp)
        if match:
            return match.group(1), int(match.group(3)), int(match.group(2))

    url = edital.url_original or ''
    match = re.search(r'editais/(\d{14})-\d+-(\d+)/(\d{4})', url)
    if match:
        return match.group(1), int(match.group(3)), int(match.group(2))

    return None, None, None


def _download_file(url, timeout=DOWNLOAD_TIMEOUT):
    """Baixa arquivo de uma URL. Retorna (bytes, content_type, filename)."""
    try:
        resp = requests.get(url, timeout=timeout, stream=True, allow_redirects=True)
        if resp.status_code == 200:
            content = resp.content
            ct = resp.headers.get('Content-Type', 'application/octet-stream')
            cd = resp.headers.get('Content-Disposition', '')
            fname = None
            if 'filename' in cd:
                match = re.search(r'filename[*]?="?([^";]+)"?', cd)
                if match:
                    fname = match.group(1).strip()
            return content, ct, fname
        else:
            logger.warning("Download HTTP %d: %s", resp.status_code, url[:200])
            return None, None, None
    except Exception as e:
        logger.error("Erro download %s: %s", url[:200], e)
        return None, None, None


# ============================================================
# DOWNLOAD POR PLATAFORMA
# ============================================================

def _baixar_documentos_pncp(edital):
    """Baixa documentos do PNCP."""
    cnpj, ano, seq = _parse_pncp_info(edital)
    if not cnpj or not ano or not seq:
        logger.warning(
            "PNCP: Nao foi possivel extrair CNPJ/ano/seq do edital %d (plataforma=%s)",
            edital.id, edital.plataforma_origem,
        )
        return []

    url_lista = f"{PNCP_API_BASE}/orgaos/{cnpj}/compras/{ano}/{seq}/arquivos"
    try:
        resp = requests.get(url_lista, timeout=15)
        if resp.status_code != 200:
            logger.warning("PNCP lista arquivos HTTP %d para edital %d", resp.status_code, edital.id)
            return []
        arquivos_api = resp.json()
    except Exception as e:
        logger.error("PNCP erro listar arquivos edital %d: %s", edital.id, e)
        return []

    if not isinstance(arquivos_api, list):
        logger.warning("PNCP retorno inesperado para edital %d: %s", edital.id, type(arquivos_api))
        return []

    documentos = []
    for i, arq in enumerate(arquivos_api):
        seq_doc = arq.get("sequencialDocumento", i + 1)
        titulo = arq.get("titulo") or arq.get("tituloDocumento") or f"documento_{seq_doc}"
        url_download = arq.get("url") or f"{PNCP_API_BASE}/orgaos/{cnpj}/compras/{ano}/{seq}/arquivos/{seq_doc}"

        content, ct, fname = _download_file(url_download)
        if content:
            nome_arquivo = fname or f"{titulo}.pdf"
            nome_arquivo = re.sub(r'[\\/:*?"<>|]', '_', nome_arquivo)

            tipo = "edital" if i == 0 else "anexo"
            titulo_lower = (titulo or "").lower()
            if "anexo" in titulo_lower:
                tipo = "anexo"
            elif "ata" in titulo_lower:
                tipo = "ata"
            elif "contrato" in titulo_lower:
                tipo = "contrato"
            elif "edital" in titulo_lower or "aviso" in titulo_lower:
                tipo = "edital"

            # EXTRAIR TEXTO DO PDF
            texto = ''
            if (ct and 'pdf' in ct.lower()) or nome_arquivo.lower().endswith('.pdf'):
                texto = _extrair_texto_pdf(content)

            documentos.append({
                "nome": nome_arquivo,
                "bytes": content,
                "content_type": ct,
                "url_original": url_download,
                "tipo": tipo,
                "titulo_api": titulo,
                "texto_extraido": texto,
            })

        time.sleep(0.3)

    logger.info("PNCP: %d documentos baixados para edital %d", len(documentos), edital.id)
    return documentos


def _baixar_documentos_bbmnet(edital):
    """BBMNET: tenta PNCP primeiro, depois URL original."""
    documentos = []

    if edital.numero_controle_pncp or edital.orgao_cnpj:
        docs_pncp = _baixar_documentos_pncp(edital)
        if docs_pncp:
            return docs_pncp

    urls_tentar = [edital.url_original, edital.link_sistema_origem]
    for url in urls_tentar:
        if url and url.startswith('http'):
            content, ct, fname = _download_file(url)
            if content and len(content) > 1000:
                nome = fname or f"edital_bbmnet_{edital.id}.pdf"

                texto = ''
                if nome.lower().endswith('.pdf') or (ct and 'pdf' in ct.lower()):
                    texto = _extrair_texto_pdf(content)

                documentos.append({
                    "nome": nome,
                    "bytes": content,
                    "content_type": ct,
                    "url_original": url,
                    "tipo": "edital",
                    "texto_extraido": texto,
                })
                break

    logger.info("BBMNET: %d documentos baixados para edital %d", len(documentos), edital.id)
    return documentos


def _baixar_documentos_licitardigital(edital):
    """Licitar Digital: usa Partner API para listar documentos."""
    documentos = []

    id_externo = edital.id_externo if hasattr(edital, 'id_externo') else None

    if not id_externo and edital.url_original:
        match = re.search(r'/process(?:o)?/(\d+)', edital.url_original or '')
        if match:
            id_externo = match.group(1)

    if not id_externo:
        logger.warning("Licitar Digital: sem ID externo para edital %d", edital.id)
        return []

    base_url = os.environ.get("LICITAR_PARTNER_BASE_URL", "")
    client_id = os.environ.get("LICITAR_PARTNER_CLIENT_ID", "")
    client_secret = os.environ.get("LICITAR_PARTNER_CLIENT_SECRET", "")

    if not base_url or not client_id:
        logger.warning("Licitar Digital: credenciais nao configuradas")
        return []

    import base64
    auth_str = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    try:
        url_docs = f"{base_url}/api/v1/public/processDocuments"
        resp = requests.get(
            url_docs,
            params={"processId": id_externo},
            headers={"Authorization": f"Basic {auth_str}"},
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning("Licitar docs HTTP %d para edital %d", resp.status_code, edital.id)
            return []

        docs_api = resp.json()
        docs_list = docs_api if isinstance(docs_api, list) else docs_api.get("documents", [])

    except Exception as e:
        logger.error("Licitar docs erro edital %d: %s", edital.id, e)
        return []

    for doc in docs_list:
        url_download = doc.get("url") or doc.get("downloadUrl") or doc.get("fileUrl")
        nome = doc.get("name") or doc.get("fileName") or f"documento_licitar_{edital.id}.pdf"

        if url_download:
            content, ct, fname = _download_file(url_download)
            if content:
                final_name = fname or nome
                texto = ''
                if final_name.lower().endswith('.pdf') or (ct and 'pdf' in ct.lower()):
                    texto = _extrair_texto_pdf(content)

                documentos.append({
                    "nome": final_name,
                    "bytes": content,
                    "content_type": ct or "application/pdf",
                    "url_original": url_download,
                    "tipo": "edital" if len(documentos) == 0 else "anexo",
                    "texto_extraido": texto,
                })
            time.sleep(0.3)

    logger.info("Licitar Digital: %d documentos baixados para edital %d", len(documentos), edital.id)
    return documentos


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def baixar_e_enviar_dropbox(edital_id, app=None):
    """Pipeline completo: baixa documentos, extrai texto, envia para Dropbox, salva no banco."""
    from . import dropbox_service

    if app is None:
        from flask import current_app
        app = current_app._get_current_object()

    with app.app_context():
        from ..models.database import db, Edital, EditalArquivo

        edital = Edital.query.get(edital_id)
        if not edital:
            logger.error("Edital %d nao encontrado para download", edital_id)
            return

        plataforma = edital.plataforma_origem or ""
        logger.info(
            "Iniciando download de documentos: edital=%d plataforma=%s orgao=%s",
            edital.id, plataforma, edital.orgao_razao_social,
        )

        if plataforma in ("pncp", "comprasgov"):
            documentos = _baixar_documentos_pncp(edital)
        elif plataforma == "bbmnet":
            documentos = _baixar_documentos_bbmnet(edital)
        elif plataforma == "licitardigital":
            documentos = _baixar_documentos_licitardigital(edital)
        else:
            documentos = _baixar_documentos_pncp(edital)

        if not documentos:
            logger.warning("Nenhum documento encontrado para edital %d", edital.id)
            return

        pasta_dropbox = dropbox_service.gerar_pasta_edital(edital)
        dropbox_service.criar_pasta(pasta_dropbox)

        salvos = 0
        for doc in documentos:
            try:
                dropbox_path = f"{pasta_dropbox}/{doc['nome']}"
                resultado = dropbox_service.upload_arquivo(
                    doc["bytes"],
                    dropbox_path,
                    nome_arquivo=doc["nome"],
                )

                if not resultado:
                    continue

                texto = doc.get("texto_extraido", "")

                existente = EditalArquivo.query.filter_by(
                    edital_id=edital.id,
                    nome_arquivo=doc["nome"],
                ).first()

                if existente:
                    existente.url_cloudinary = resultado.get("shared_link") or resultado["dropbox_path"]
                    existente.tamanho_bytes = resultado["tamanho"]
                    if texto and not existente.texto_extraido:
                        existente.texto_extraido = texto
                else:
                    arquivo = EditalArquivo(
                        edital_id=edital.id,
                        tipo=doc.get("tipo", "edital"),
                        nome_arquivo=doc["nome"],
                        url_cloudinary=resultado.get("shared_link") or resultado["dropbox_path"],
                        url_original=doc.get("url_original"),
                        tamanho_bytes=resultado["tamanho"],
                        mime_type=doc.get("content_type", "application/pdf"),
                        texto_extraido=texto,
                    )
                    db.session.add(arquivo)

                db.session.commit()
                salvos += 1

                if texto:
                    logger.info(
                        "Texto extraido: edital=%d arquivo='%s' (%d chars)",
                        edital.id, doc["nome"], len(texto),
                    )

            except Exception as e:
                db.session.rollback()
                logger.error(
                    "Erro salvar arquivo '%s' edital %d: %s",
                    doc.get("nome"), edital.id, e,
                )

        logger.info(
            "Download concluido: edital=%d, %d/%d documentos salvos no Dropbox",
            edital.id, salvos, len(documentos),
        )

        # ========== ENCADEAR: EXTRAÇÃO AI + PLANILHA ==========
        # Agora que temos o texto extraído, podemos gerar itens via AI
        # e depois gerar a planilha com os itens preenchidos
        try:
            from ..services.captacao_service import CaptacaoService
            from flask import current_app

            service = CaptacaoService(current_app.config)
            resultado_ai = service.extrair_itens_edital(edital_id)

            qtd_itens = resultado_ai.get('total_itens', 0)
            logger.info("AI extraiu %d itens do edital %d", qtd_itens, edital_id)
        except Exception as e:
            logger.warning("Erro extrair itens AI edital %d: %s", edital_id, e)

        # Gerar planilha de cotação (agora com itens preenchidos)
        try:
            from ..services.planilha_cotacao_service import gerar_e_enviar_planilha
            gerar_e_enviar_planilha(edital_id, app)
            logger.info("Planilha de cotacao gerada para edital %d", edital_id)
        except Exception as e:
            logger.warning("Erro gerar planilha edital %d: %s", edital_id, e)


def disparar_download_async(edital_id, app):
    """Dispara download em background thread."""
    thread = Thread(
        target=baixar_e_enviar_dropbox,
        args=(edital_id, app),
        daemon=True,
    )
    thread.start()
    logger.info("Download assincrono disparado para edital %d", edital_id)
    return thread
