"""
SGL - Scraper BBMNET (bbmnetlicitacoes.com.br)
Autentica via Keycloak OAuth2 e busca editais publicados.
"""
import hashlib
import base64
import os
import re
import logging
import time
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode, urlparse, parse_qs

import requests

logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURAÇÃO
# ============================================================

KEYCLOAK_BASE = "https://auth.bbmnet.com.br/realms/BBM/protocol/openid-connect"
KEYCLOAK_TOKEN_URL = f"{KEYCLOAK_BASE}/token"
KEYCLOAK_AUTH_URL = f"{KEYCLOAK_BASE}/auth"

CLIENT_ID = "cadastro-participantes-admin-site"
REDIRECT_URI = "https://sistema.bbmnet.com.br/visaoeditais/editais"

API_EDITAIS_BASE = "https://bbmnet-cadastro-editais-backend-z7knklmt7a-rj.a.run.app/api/Editais"
API_PARTICIPANTES_BASE = "https://cadastro-participantes-backend-fm2e4c7u4q-rj.a.run.app/api/credenciamento"

# UFs do Sudeste (padrão SGL)
UFS_PADRAO = ["RJ", "SP", "MG", "ES"]

# Mapeamento de modalidades BBMNET
MODALIDADES_BBMNET = {
    1: "Concorrência",
    2: "Concurso",
    3: "Pregão (Setor público)",
    4: "Leilão",
    5: "Diálogo Competitivo",
    6: "Pregão (Setor privado)",
}


class BBMNETScraper:
    """
    Scraper para capturar editais do portal BBMNET.
    Usa autenticação Keycloak (OAuth2 Authorization Code + PKCE).
    """

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        })
        self.access_token = None
        self.token_expiry = None

    # ============================================================
    # AUTENTICAÇÃO KEYCLOAK
    # ============================================================

    def _generate_pkce(self):
        """Gera code_verifier e code_challenge para PKCE."""
        code_verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b'=').decode('ascii')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('ascii')).digest()
        ).rstrip(b'=').decode('ascii')
        return code_verifier, code_challenge

    def autenticar(self) -> bool:
        """
        Autentica no BBMNET via Keycloak.
        Tenta password grant primeiro, depois full OAuth flow.
        """
        # Tentativa 1: Password grant (mais simples)
        if self._tentar_password_grant():
            return True

        # Tentativa 2: Full OAuth2 Authorization Code + PKCE
        logger.info("Password grant falhou, tentando Authorization Code flow...")
        return self._authorization_code_flow()

    def _tentar_password_grant(self) -> bool:
        """Tenta autenticação direta via password grant."""
        try:
            resp = self.session.post(KEYCLOAK_TOKEN_URL, data={
                "grant_type": "password",
                "client_id": CLIENT_ID,
                "username": self.username,
                "password": self.password,
                "scope": "openid email profile",
            }, timeout=15)

            if resp.status_code == 200:
                data = resp.json()
                self.access_token = data["access_token"]
                expires_in = data.get("expires_in", 300)
                self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 30)
                logger.info(f"BBMNET: autenticado via password grant (expira em {expires_in}s)")
                return True
            else:
                logger.debug(f"Password grant negado: {resp.status_code} - {resp.text[:200]}")
                return False
        except Exception as e:
            logger.debug(f"Password grant erro: {e}")
            return False

    def _authorization_code_flow(self) -> bool:
        """
        Simula o fluxo completo OAuth2 Authorization Code + PKCE.
        1. Inicia auth request → recebe página de login
        2. POST credenciais → recebe redirect com code
        3. Troca code por token
        """
        try:
            code_verifier, code_challenge = self._generate_pkce()
            state = base64.urlsafe_b64encode(os.urandom(16)).rstrip(b'=').decode('ascii')
            nonce = base64.urlsafe_b64encode(os.urandom(16)).rstrip(b'=').decode('ascii')

            # 1. Iniciar auth request
            auth_params = {
                "client_id": CLIENT_ID,
                "redirect_uri": REDIRECT_URI,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "nonce": nonce,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }

            # Não seguir redirects automaticamente para capturar cookies
            auth_session = requests.Session()
            auth_session.headers.update(self.session.headers)

            resp = auth_session.get(
                KEYCLOAK_AUTH_URL,
                params=auth_params,
                allow_redirects=True,
                timeout=15,
            )

            if resp.status_code != 200:
                logger.error(f"Erro ao acessar login Keycloak: {resp.status_code}")
                return False

            # 2. Extrair form action do HTML de login
            html = resp.text
            action_match = re.search(r'action="([^"]+)"', html)
            if not action_match:
                logger.error("Não encontrou form action no HTML do Keycloak")
                return False

            login_url = action_match.group(1).replace("&amp;", "&")

            # 3. POST credenciais
            login_resp = auth_session.post(
                login_url,
                data={
                    "username": self.username,
                    "password": self.password,
                },
                allow_redirects=False,
                timeout=15,
            )

            # 4. Seguir redirects manualmente para capturar o code
            redirect_url = login_resp.headers.get("Location", "")

            if not redirect_url:
                # Pode ter retornado erro de login
                if "Invalid" in login_resp.text or "invalid" in login_resp.text:
                    logger.error("BBMNET: Credenciais inválidas")
                    return False
                logger.error(f"Sem redirect após login. Status: {login_resp.status_code}")
                return False

            # Pode haver múltiplos redirects
            max_redirects = 5
            for _ in range(max_redirects):
                if REDIRECT_URI.split("//")[1] in redirect_url:
                    break
                resp = auth_session.get(redirect_url, allow_redirects=False, timeout=15)
                redirect_url = resp.headers.get("Location", "")
                if not redirect_url:
                    break

            # 5. Extrair code da URL de redirect
            parsed = urlparse(redirect_url)
            params = parse_qs(parsed.query)
            code = params.get("code", [None])[0]

            if not code:
                logger.error(f"Não encontrou code na URL de redirect: {redirect_url[:200]}")
                return False

            # 6. Trocar code por token
            token_resp = self.session.post(KEYCLOAK_TOKEN_URL, data={
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "code_verifier": code_verifier,
            }, timeout=15)

            if token_resp.status_code != 200:
                logger.error(f"Erro ao trocar code por token: {token_resp.status_code} - {token_resp.text[:200]}")
                return False

            data = token_resp.json()
            self.access_token = data["access_token"]
            expires_in = data.get("expires_in", 300)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 30)
            logger.info(f"BBMNET: autenticado via Authorization Code (expira em {expires_in}s)")
            return True

        except Exception as e:
            logger.error(f"Erro no Authorization Code flow: {e}", exc_info=True)
            return False

    def _garantir_token(self):
        """Verifica se o token está válido e renova se necessário."""
        if not self.access_token or (self.token_expiry and datetime.now() >= self.token_expiry):
            logger.info("Token expirado, reautenticando...")
            if not self.autenticar():
                raise Exception("Falha ao reautenticar no BBMNET")

    def _headers_auth(self) -> dict:
        """Retorna headers com Bearer token."""
        self._garantir_token()
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://sistema.bbmnet.com.br",
            "Referer": "https://sistema.bbmnet.com.br/",
        }

    # ============================================================
    # BUSCA DE EDITAIS
    # ============================================================

    def buscar_editais(
        self,
        uf: Optional[str] = None,
        modalidade_id: Optional[int] = None,
        take: int = 50,
        skip: int = 0,
    ) -> dict:
        """
        Busca editais publicados no BBMNET.

        Args:
            uf: Sigla do estado (ex: "RJ", "MG")
            modalidade_id: ID da modalidade (3=Pregão Setor Público)
            take: Quantidade de registros por página
            skip: Offset para paginação

        Returns:
            dict com {editais: [...], count: int}
        """
        params = {
            "Take": take,
            "Skip": skip,
        }
        if uf:
            params["Uf"] = uf
        if modalidade_id:
            params["ModalidadeId"] = modalidade_id

        url = f"{API_EDITAIS_BASE}/Participantes"

        try:
            resp = self.session.get(
                url,
                params=params,
                headers=self._headers_auth(),
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Erro ao buscar editais BBMNET (UF={uf}): {e}")
            return {"editais": [], "count": 0}

    def buscar_detalhe_edital(self, unique_id: str) -> Optional[dict]:
        """
        Busca detalhes completos de um edital pelo uniqueId.
        """
        url = f"{API_EDITAIS_BASE}/{unique_id}"

        try:
            resp = self.session.get(
                url,
                headers=self._headers_auth(),
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Erro ao buscar detalhe edital {unique_id}: {e}")
            return None

    def buscar_todos_editais_uf(
        self,
        uf: str,
        modalidade_id: int = 3,
        max_resultados: int = 500,
        dias_recentes: int = 30,
    ) -> list:
        from datetime import datetime, timedelta
        hoje = datetime.now()
        editais_abertos = []
        skip = 0
        take = 50
        encerrados_seguidos = 0

        while skip < max_resultados:
            resultado = self.buscar_editais(uf=uf, modalidade_id=modalidade_id, take=take, skip=skip)
            editais = resultado.get('editais', [])
            if not editais:
                break
            for edital in editais:
                status = edital.get('editalStatus', {})
                status_name = status.get('name', '') if isinstance(status, dict) else ''
                manter = False
                if status_name.lower() in ['publicado', 'aberto', 'em andamento']:
                    manter = True
                    encerrados_seguidos = 0
                if not manter:
                    for campo in ['dataRealizacao', 'disputeStartDate', 'publishAt']:
                        ds = edital.get(campo, '')
                        if ds:
                            try:
                                dt = datetime.fromisoformat(ds.replace('Z','').split('+')[0])
                                if dt >= hoje:
                                    manter = True
                                    encerrados_seguidos = 0
                                    break
                            except (ValueError, TypeError):
                                pass
                if not manter:
                    pub_str = edital.get('publishAt') or edital.get('createdAt') or ''
                    if pub_str:
                        try:
                            pub_date = datetime.fromisoformat(pub_str.replace('Z','').split('+')[0])
                            if pub_date >= hoje - timedelta(days=dias_recentes):
                                manter = True
                                encerrados_seguidos = 0
                        except (ValueError, TypeError):
                            pass
                if manter:
                    editais_abertos.append(edital)
                else:
                    encerrados_seguidos += 1
            skip += take
            time.sleep(0.1)
            if encerrados_seguidos >= 20:
                logger.info(f'BBMNET UF={uf}: parando apos {encerrados_seguidos} encerrados (skip={skip})')
                break
            if len(editais) < take:
                break
        logger.info(f'BBMNET UF={uf}: {len(editais_abertos)} editais abertos (skip={skip})')
        return editais_abertos

    # ============================================================
    # CONVERSÃO PARA FORMATO SGL
    # ============================================================

    @staticmethod
    def converter_para_sgl(edital_bbmnet: dict, uf_busca: str = None) -> dict:
        """
        Converte um edital do BBMNET para o formato do SGL.
        """
        orgao = edital_bbmnet.get("orgaoPromotor", {})
        unidade = edital_bbmnet.get("unidadeCompradora", {})
        modalidade = edital_bbmnet.get("modalidade", {})
        criterio = edital_bbmnet.get("criterioJulgamento", {})
        finalidade = edital_bbmnet.get("finalidadeLicitacao", {})

        unique_id = edital_bbmnet.get("uniqueId", "")

        # Gerar hash único para deduplicação
        hash_str = f"bbmnet:{unique_id}"
        hash_scraper = hashlib.md5(hash_str.encode()).hexdigest()

        # Extrair endereço do órgão
        endereco = orgao.get("endereco", {}) if isinstance(orgao, dict) else {}
        uf = endereco.get("estado", "") if isinstance(endereco, dict) else ""
        municipio = endereco.get("cidade", "") if isinstance(endereco, dict) else ""

        # Se não tem UF no endereço, tentar pegar do edital ou do contexto de busca
        if not uf and isinstance(edital_bbmnet.get("uf"), str):
            uf = edital_bbmnet["uf"]
        if not uf and uf_busca:
            uf = uf_busca

        return {
            # Identificação
            "numero_controle_pncp": None,  # Não é do PNCP
            "hash_scraper": hash_scraper,
            "numero_pregao": edital_bbmnet.get("numeroEdital"),
            "numero_processo": edital_bbmnet.get("numeroProcesso"),

            # Órgão
            "orgao_cnpj": orgao.get("documento"),
            "orgao_razao_social": orgao.get("razaoSocial") or orgao.get("nomeFantasia"),
            "unidade_nome": unidade.get("razaoSocial") or unidade.get("nomeFantasia"),
            "uf": uf,
            "municipio": municipio,

            # Objeto
            "objeto_resumo": (edital_bbmnet.get("objeto") or "")[:500],
            "objeto_completo": edital_bbmnet.get("objeto"),

            # Modalidade
            "modalidade_nome": modalidade.get("name", ""),
            "srp": "registro de preço" in (finalidade.get("name", "") or "").lower(),

            # Datas
            "data_publicacao": edital_bbmnet.get("publishAt"),
            "data_abertura_proposta": edital_bbmnet.get("inicioRecebimentoPropostas"),
            "data_encerramento_proposta": edital_bbmnet.get("terminoRecebimentoPropostas"),
            "data_inicio_lances": edital_bbmnet.get("inicioLances"),

            # Critérios
            "criterio_julgamento": criterio.get("name"),
            "finalidade": finalidade.get("name"),

            # Plataforma
            "plataforma_origem": "bbmnet",
            "url_original": f"https://sistema.bbmnet.com.br/visaoeditais/editais/readonly/{unique_id}",
            "link_sistema_origem": f"https://sistema.bbmnet.com.br/visaoeditais/editais/readonly/{unique_id}",
            "id_externo": unique_id,

            # Status
            "situacao_pncp": edital_bbmnet.get("editalStatus", {}).get("name", "Publicado"),
            "status": "captado",
        }


# ============================================================
# FUNÇÃO PRINCIPAL DE CAPTAÇÃO
# ============================================================

def captar_editais_bbmnet(
    username: str,
    password: str,
    ufs: list = None,
    modalidade_id: int = 3,
    dias_recentes: int = 7,
) -> dict:
    """
    Função principal: captura editais do BBMNET para integração com SGL.

    Args:
        username: CPF de login no BBMNET
        password: Senha
        ufs: Lista de UFs (padrão: RJ, SP, MG, ES)
        modalidade_id: 3 = Pregão Setor Público
        dias_recentes: Buscar últimos N dias

    Returns:
        dict com estatísticas e lista de editais
    """
    if ufs is None:
        ufs = UFS_PADRAO

    scraper = BBMNETScraper(username, password)

    # Autenticar
    if not scraper.autenticar():
        return {
            "sucesso": False,
            "erro": "Falha na autenticação BBMNET",
            "editais": [],
            "stats": {},
        }

    # Buscar editais por UF
    todos_editais = []
    stats_por_uf = {}

    for uf in ufs:
        try:
            editais_raw = scraper.buscar_todos_editais_uf(
                uf=uf,
                modalidade_id=modalidade_id,
                dias_recentes=dias_recentes,
            )

            # Converter direto do resumo (sem buscar detalhe = muito mais rapido)
            editais_sgl = [
                BBMNETScraper.converter_para_sgl(e, uf_busca=uf)
                for e in editais_raw
            ]

            todos_editais.extend(editais_sgl)
            stats_por_uf[uf] = {
                "encontrados": len(editais_raw),
                "detalhados": len(editais_sgl),
                "convertidos": len(editais_sgl),
            }

            logger.info(f"BBMNET UF={uf}: {len(editais_sgl)} editais captados")

        except Exception as e:
            logger.error(f"Erro ao captar BBMNET UF={uf}: {e}")
            stats_por_uf[uf] = {"erro": str(e)}

    return {
        "sucesso": True,
        "plataforma": "bbmnet",
        "editais": todos_editais,
        "stats": {
            "total": len(todos_editais),
            "por_uf": stats_por_uf,
            "dias_recentes": dias_recentes,
            "modalidade": MODALIDADES_BBMNET.get(modalidade_id, str(modalidade_id)),
        },
    }


# ============================================================
# TESTE STANDALONE
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Credenciais BBMNET
    USERNAME = "07923334625"
    PASSWORD = "Gbraz24@"

    print("=" * 60)
    print("TESTE SCRAPER BBMNET")
    print("=" * 60)

    scraper = BBMNETScraper(USERNAME, PASSWORD)

    # 1. Autenticar
    print("\n1. Autenticando...")
    if scraper.autenticar():
        print("   ✓ Autenticado com sucesso!")
        print(f"   Token: {scraper.access_token[:50]}...")
    else:
        print("   ✗ Falha na autenticação!")
        exit(1)

    # 2. Buscar editais RJ
    print("\n2. Buscando editais RJ (Pregão, últimos 7 dias)...")
    resultado = scraper.buscar_editais(uf="RJ", modalidade_id=3, take=5)
    count = resultado.get("count", 0)
    editais = resultado.get("editais", [])
    print(f"   Total disponível: {count}")
    print(f"   Recebidos: {len(editais)}")

    if editais:
        print("\n   Primeiros editais:")
        for i, ed in enumerate(editais[:3]):
            uid = ed.get("uniqueId", "?")
            num = ed.get("numeroEdital", "?")
            proc = ed.get("numeroProcesso", "?")
            print(f"   [{i+1}] Edital {num} | Processo {proc} | ID: {uid[:20]}...")

    # 3. Buscar detalhe do primeiro
    if editais:
        uid = editais[0].get("uniqueId")
        print(f"\n3. Buscando detalhe do edital {uid[:20]}...")
        detalhe = scraper.buscar_detalhe_edital(uid)
        if detalhe:
            print(f"   Objeto: {(detalhe.get('objeto') or 'N/A')[:100]}...")
            print(f"   Órgão: {detalhe.get('orgaoPromotor', {}).get('razaoSocial', 'N/A')}")
            print(f"   Modalidade: {detalhe.get('modalidade', {}).get('name', 'N/A')}")
            print(f"   Status: {detalhe.get('editalStatus', {}).get('name', 'N/A')}")

            # Converter para SGL
            sgl = BBMNETScraper.converter_para_sgl(detalhe)
            print(f"\n   Convertido para SGL:")
            print(f"   Hash: {sgl['hash_scraper']}")
            print(f"   Órgão: {sgl['orgao_razao_social']}")
            print(f"   UF: {sgl['uf']}")
            print(f"   Objeto: {sgl['objeto_resumo'][:80]}...")

    print("\n" + "=" * 60)
    print("TESTE CONCLUÍDO")
    print("=" * 60)
