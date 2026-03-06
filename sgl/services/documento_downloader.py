"""
SGL - Download de Documentos de Editais

Baixa documentos das plataformas e envia para o Dropbox.
Suporta: PNCP, ComprasGov (via PNCP), BBMNET, Licitar Digital.

Fluxo:
  1. Detecta plataforma de origem do edital
  2. Baixa arquivos via API da plataforma
  3. Upload para Dropbox em pasta organizada
  4. Salva referências na tabela edital_arquivos
"""
import logging
import os
import re
import time
import hashlib
from datetime import datetime, timezone
from threading import Thread

import requests

logger = logging.getLogger(__name__)

PNCP_API_BASE = "https://pncp.gov.br/pncp-api/v1"
DOWNLOAD_TIMEOUT = 30  # segundos por arquivo


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def _parse_pncp_info(edital):
    """
    Extrai CNPJ, ano e sequencial de um edital PNCP/ComprasGov.
    Tenta múltiplas fontes: campos diretos, numero_controle_pncp, url_original.

    Returns:
        tuple (cnpj, ano, sequencial) ou (None, None, None)
    """
    cnpj = edital.orgao_cnpj
    ano = edital.ano_compra
    seq = edital.sequencial_compra

    if cnpj and ano and seq:
        cnpj_limpo = re.sub(r'[^0-9]', '', cnpj)
        return cnpj_limpo, int(ano), int(seq)

    # Tentar extrair do numero_controle_pncp: "00394502000144-1-000818/2026"
    ncp = edital.numero_controle_pncp
    if ncp:
        match = re.match(r'^(\d{14})-\d+-(\d+)/(\d{4})$', ncp)
        if match:
            return match.group(1), int(match.group(3)), int(match.group(2))

    # Tentar extrair da URL original: https://pncp.gov.br/app/editais/CNPJ-X-SEQ/ANO
    url = edital.url_original or ''
    match = re.search(r'editais/(\d{14})-\d+-(\d+)/(\d{4})', url)
    if match:
        return match.group(1), int(match.group(3)), int(match.group(2))

    return None, None, None


def _download_file(url, timeout=DOWNLOAD_TIMEOUT):
    """Baixa arquivo de uma URL. Retorna (bytes, content_type, filename) ou (None, None, None)."""
    try:
        resp = requests.get(url, timeout=timeout, stream=True, allow_redirects=True)
        if resp.status_code == 200:
            content = resp.content
            ct = resp.headers.get('Content-Type', 'application/octet-stream')
            # Tentar pegar nome do Content-Disposition
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
    """
    Baixa documentos do PNCP.
    Endpoint: GET /v1/orgaos/{cnpj}/compras/{ano}/{seq}/arquivos
    Retorna lista de {nome, bytes, content_type, url_original, tipo}
    """
    cnpj, ano, seq = _parse_pncp_info(edital)
    if not cnpj or not ano or not seq:
        logger.warning(
            "PNCP: Não foi possível extrair CNPJ/ano/seq do edital %d (plataforma=%s)",
            edital.id, edital.plataforma_origem,
        )
        return []

    # Listar arquivos
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
            # Determinar nome do arquivo
            nome_arquivo = fname or f"{titulo}.pdf"
            nome_arquivo = re.sub(r'[\\/:*?"<>|]', '_', nome_arquivo)

            # Determinar tipo
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

            documentos.append({
                "nome": nome_arquivo,
                "bytes": content,
                "content_type": ct,
                "url_original": url_download,
                "tipo": tipo,
                "titulo_api": titulo,
            })

        time.sleep(0.3)  # Rate limit

    logger.info("PNCP: %d documentos baixados para edital %d", len(documentos), edital.id)
    return documentos


def _baixar_documentos_bbmnet(edital):
    """
    BBMNET: documentos geralmente acessíveis via link no portal.
    Tenta baixar da url_original e link_sistema_origem.
    Muitos editais BBMNET também estão no PNCP — tenta ambos.
    """
    documentos = []

    # 1. Tentar via PNCP (muitos editais BBMNET publicam lá)
    if edital.numero_controle_pncp or edital.orgao_cnpj:
        docs_pncp = _baixar_documentos_pncp(edital)
        if docs_pncp:
            return docs_pncp

    # 2. Tentar baixar da URL original (link direto para o edital no BBMNET)
    urls_tentar = [edital.url_original, edital.link_sistema_origem]
    for url in urls_tentar:
        if url and url.startswith('http'):
            content, ct, fname = _download_file(url)
            if content and len(content) > 1000:  # Não é uma página HTML de erro
                nome = fname or f"edital_bbmnet_{edital.id}.pdf"
                documentos.append({
                    "nome": nome,
                    "bytes": content,
                    "content_type": ct,
                    "url_original": url,
                    "tipo": "edital",
                })
                break

    logger.info("BBMNET: %d documentos baixados para edital %d", len(documentos), edital.id)
    return documentos


def _baixar_documentos_licitardigital(edital):
    """
    Licitar Digital: usa Partner API para listar documentos.
    Endpoint: GET /api/v1/public/processDocuments?processId={id}
    """
    documentos = []

    # Precisa do ID externo do processo no Licitar Digital
    id_externo = edital.id_externo if hasattr(edital, 'id_externo') else None

    # Tentar extrair ID da url_original
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
        logger.warning("Licitar Digital: credenciais não configuradas")
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
                documentos.append({
                    "nome": fname or nome,
                    "bytes": content,
                    "content_type": ct or "application/pdf",
                    "url_original": url_download,
                    "tipo": "edital" if len(documentos) == 0 else "anexo",
                })
            time.sleep(0.3)

    logger.info("Licitar Digital: %d documentos baixados para edital %d", len(documentos), edital.id)
    return documentos


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def baixar_e_enviar_dropbox(edital_id, app=None):
    """
    Pipeline completo: baixa documentos do edital e envia para Dropbox.
    Roda em background thread.

    Args:
        edital_id: int ID do edital
        app: Flask app (para contexto)
    """
    from . import dropbox_service

    # Precisa de contexto Flask para acessar o banco
    if app is None:
        from flask import current_app
        app = current_app._get_current_object()

    with app.app_context():
        from ..models.database import db, Edital, EditalArquivo

        edital = Edital.query.get(edital_id)
        if not edital:
            logger.error("Edital %d não encontrado para download", edital_id)
            return

        plataforma = edital.plataforma_origem or ""
        logger.info(
            "Iniciando download de documentos: edital=%d plataforma=%s orgao=%s",
            edital.id, plataforma, edital.orgao_razao_social,
        )

        # Selecionar downloader por plataforma
        if plataforma in ("pncp", "comprasgov"):
            documentos = _baixar_documentos_pncp(edital)
        elif plataforma == "bbmnet":
            documentos = _baixar_documentos_bbmnet(edital)
        elif plataforma == "licitardigital":
            documentos = _baixar_documentos_licitardigital(edital)
        else:
            # Tentar PNCP como fallback
            documentos = _baixar_documentos_pncp(edital)

        if not documentos:
            logger.warning("Nenhum documento encontrado para edital %d", edital.id)
            return

        # Criar pasta no Dropbox
        pasta_dropbox = dropbox_service.gerar_pasta_edital(edital)
        dropbox_service.criar_pasta(pasta_dropbox)

        salvos = 0
        for doc in documentos:
            try:
                # Upload para Dropbox
                dropbox_path = f"{pasta_dropbox}/{doc['nome']}"
                resultado = dropbox_service.upload_arquivo(
                    doc["bytes"],
                    dropbox_path,
                    nome_arquivo=doc["nome"],
                )

                if not resultado:
                    continue

                # Salvar referência no banco
                # Verificar se já existe (por nome + edital_id)
                existente = EditalArquivo.query.filter_by(
                    edital_id=edital.id,
                    nome_arquivo=doc["nome"],
                ).first()

                if existente:
                    existente.url_cloudinary = resultado.get("shared_link") or resultado["dropbox_path"]
                    existente.tamanho_bytes = resultado["tamanho"]
                else:
                    arquivo = EditalArquivo(
                        edital_id=edital.id,
                        tipo=doc.get("tipo", "edital"),
                        nome_arquivo=doc["nome"],
                        url_cloudinary=resultado.get("shared_link") or resultado["dropbox_path"],
                        url_original=doc.get("url_original"),
                        tamanho_bytes=resultado["tamanho"],
                        mime_type=doc.get("content_type", "application/pdf"),
                    )
                    db.session.add(arquivo)

                db.session.commit()
                salvos += 1

            except Exception as e:
                db.session.rollback()
                logger.error(
                    "Erro salvar arquivo '%s' edital %d: %s",
                    doc.get("nome"), edital.id, e,
                )

        logger.info(
            "Download concluído: edital=%d, %d/%d documentos salvos no Dropbox",
            edital.id, salvos, len(documentos),
        )


def disparar_download_async(edital_id, app):
    """
    Dispara download em background thread.
    Chamado automaticamente ao aprovar edital na triagem.
    """
    thread = Thread(
        target=baixar_e_enviar_dropbox,
        args=(edital_id, app),
        daemon=True,
    )
    thread.start()
    logger.info("Download assíncrono disparado para edital %d", edital_id)
    return thread
