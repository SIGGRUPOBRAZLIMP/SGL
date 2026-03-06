"""
SGL - Serviço Dropbox
Upload de arquivos de editais para Dropbox.

Env vars necessárias:
    DROPBOX_APP_KEY        - App key do Dropbox
    DROPBOX_APP_SECRET     - App secret do Dropbox
    DROPBOX_REFRESH_TOKEN  - Refresh token (longa duração)
    DROPBOX_ACCESS_TOKEN   - Access token (curta duração, alternativa ao refresh)
    DROPBOX_ROOT_FOLDER    - Pasta raiz (default: /SGL-Editais)

Instalação: pip install dropbox
"""
import logging
import os
import re

import dropbox
from dropbox.exceptions import ApiError
from dropbox.files import WriteMode

logger = logging.getLogger(__name__)

# Pasta raiz no Dropbox
ROOT_FOLDER = os.environ.get("DROPBOX_ROOT_FOLDER", "/SGL-Editais")


def _get_client():
    """Cria cliente Dropbox com refresh token (preferido) ou access token."""
    refresh_token = os.environ.get("DROPBOX_REFRESH_TOKEN")
    app_key = os.environ.get("DROPBOX_APP_KEY")
    app_secret = os.environ.get("DROPBOX_APP_SECRET")
    access_token = os.environ.get("DROPBOX_ACCESS_TOKEN")

    if refresh_token and app_key and app_secret:
        return dropbox.Dropbox(
            oauth2_refresh_token=refresh_token,
            app_key=app_key,
            app_secret=app_secret,
        )
    elif access_token:
        return dropbox.Dropbox(access_token)
    else:
        raise RuntimeError(
            "Dropbox não configurado. Defina DROPBOX_REFRESH_TOKEN + APP_KEY + APP_SECRET "
            "ou DROPBOX_ACCESS_TOKEN nas env vars."
        )


def _sanitize_filename(name):
    """Remove caracteres inválidos de nomes de pasta/arquivo."""
    name = re.sub(r'[\\/:*?"<>|]', '-', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:100]  # Limitar tamanho


def gerar_pasta_edital(edital):
    """
    Gera path da pasta no Dropbox para um edital.
    Formato: /SGL-Editais/{id}_{plataforma}_{orgao_resumido}
    """
    orgao = _sanitize_filename(edital.orgao_razao_social or "Sem-Orgao")[:60]
    plataforma = (edital.plataforma_origem or "desconhecido").upper()
    pasta = f"{ROOT_FOLDER}/{edital.id}_{plataforma}_{orgao}"
    return pasta


def upload_arquivo(conteudo_bytes, dropbox_path, nome_arquivo=None):
    """
    Faz upload de arquivo para o Dropbox.

    Args:
        conteudo_bytes: bytes do arquivo
        dropbox_path: caminho completo no Dropbox (ex: /SGL-Editais/123_PNCP_Orgao/edital.pdf)
        nome_arquivo: nome para log

    Returns:
        dict com {dropbox_path, shared_link, tamanho} ou None em erro
    """
    try:
        dbx = _get_client()
        result = dbx.files_upload(
            conteudo_bytes,
            dropbox_path,
            mode=WriteMode.overwrite,
            mute=True,
        )

        logger.info(
            "Dropbox upload OK: %s (%d bytes)",
            nome_arquivo or dropbox_path, len(conteudo_bytes),
        )

        # Tentar criar link compartilhável
        shared_link = None
        try:
            link_meta = dbx.sharing_create_shared_link_with_settings(dropbox_path)
            shared_link = link_meta.url
        except ApiError as e:
            # Link já existe
            if e.error.is_shared_link_already_exists():
                links = dbx.sharing_list_shared_links(path=dropbox_path).links
                if links:
                    shared_link = links[0].url
            else:
                logger.warning("Não foi possível criar link compartilhável: %s", e)

        return {
            "dropbox_path": result.path_display,
            "shared_link": shared_link,
            "tamanho": result.size,
        }

    except Exception as e:
        logger.error("Erro upload Dropbox '%s': %s", nome_arquivo or dropbox_path, e)
        return None


def criar_pasta(dropbox_path):
    """Cria pasta no Dropbox (ignora se já existe)."""
    try:
        dbx = _get_client()
        dbx.files_create_folder_v2(dropbox_path)
        logger.info("Pasta criada no Dropbox: %s", dropbox_path)
    except ApiError as e:
        if e.error.is_path() and e.error.get_path().is_conflict():
            pass  # Pasta já existe — OK
        else:
            logger.warning("Erro criar pasta Dropbox %s: %s", dropbox_path, e)


def testar_conexao():
    """Testa se a conexão com o Dropbox está funcionando."""
    try:
        dbx = _get_client()
        account = dbx.users_get_current_account()
        return {
            "ok": True,
            "nome": account.name.display_name,
            "email": account.email,
        }
    except Exception as e:
        return {"ok": False, "erro": str(e)}
