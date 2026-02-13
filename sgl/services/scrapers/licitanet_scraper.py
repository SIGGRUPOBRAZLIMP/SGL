"""
SGL - Scraper Licitanet
Licitanet - Licitações Online
URL: https://licitanet.com.br
Busca pública: https://licitanet.com.br/processos
"""
import logging
import re
from datetime import datetime
from typing import Optional
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, EditalScrapado

logger = logging.getLogger(__name__)


class LicitanetScraper(BaseScraper):
    """Scraper para Licitanet (licitanet.com.br)."""

    PLATAFORMA = 'licitanet'
    BASE_URL = 'https://licitanet.com.br'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session.headers.update({
            'Referer': 'https://licitanet.com.br/',
            'Origin': 'https://licitanet.com.br',
        })

    def buscar_editais(
        self,
        termo: Optional[str] = None,
        uf: Optional[str] = None,
        data_inicial: Optional[str] = None,
        data_final: Optional[str] = None,
        pagina: int = 1,
        **kwargs
    ) -> list[EditalScrapado]:
        """Busca editais no Licitanet."""

        # Tentar API interna
        try:
            return self._buscar_via_api(termo, uf, data_inicial, data_final, pagina)
        except Exception as e:
            logger.info(f"Licitanet API falhou ({e}), tentando HTML...")

        # Fallback: HTML
        try:
            return self._buscar_via_html(termo, uf, pagina)
        except Exception as e:
            logger.error(f"Licitanet HTML falhou: {e}")
            return []

    def _buscar_via_api(self, termo, uf, data_inicial, data_final, pagina) -> list[EditalScrapado]:
        """Tenta API interna do Licitanet."""
        endpoints = [
            '/api/processos',
            '/api/editais',
            '/api/v1/processos',
            '/processos/buscar',
            '/api/Process/Search',
        ]

        params = {
            'page': pagina,
            'per_page': 50,
        }
        if termo:
            params['q'] = termo
        if uf:
            params['uf'] = uf
        if data_inicial:
            params['data_inicio'] = data_inicial
        if data_final:
            params['data_fim'] = data_final

        for endpoint in endpoints:
            try:
                url = f"{self.BASE_URL}{endpoint}"
                resp = self._get(url, params=params)
                if resp.status_code == 200:
                    content_type = resp.headers.get('content-type', '')
                    if 'json' in content_type:
                        data = resp.json()
                        return self._parse_api_response(data)
            except Exception:
                continue

        raise Exception("Nenhum endpoint de API encontrado")

    def _buscar_via_html(self, termo, uf, pagina) -> list[EditalScrapado]:
        """Scraping da página pública de processos."""
        url = f"{self.BASE_URL}/processos"
        params = {}
        if pagina > 1:
            params['page'] = pagina

        resp = self._get(url, params=params)
        soup = BeautifulSoup(resp.text, 'html.parser')

        editais = []

        # Licitanet usa cards/tabelas para listar processos
        # Buscar por padrões comuns
        containers = soup.select(
            'table tbody tr, '
            '.process-card, .processo-card, .card, '
            '[class*=processo], [class*=licitacao], '
            '.list-group-item, .resultado-item'
        )

        for container in containers:
            try:
                edital = self._parse_container(container)
                if edital:
                    if termo and termo.lower() not in (edital.objeto or '').lower():
                        continue
                    if uf and uf.upper() != (edital.uf or '').upper():
                        continue
                    editais.append(edital)
            except Exception as e:
                logger.debug(f"Licitanet: Erro ao parsear container: {e}")

        # Fallback: buscar todos os links de processo
        if not editais:
            links = soup.select('a[href*="processo"], a[href*="edital"], a[href*="pregao"]')
            for link in links[:50]:
                try:
                    edital = self._parse_link(link)
                    if edital:
                        editais.append(edital)
                except Exception:
                    continue

        return editais

    def _parse_api_response(self, data) -> list[EditalScrapado]:
        """Parse de resposta JSON."""
        editais = []
        items = data if isinstance(data, list) else data.get('data', data.get('processos', data.get('editais', [])))

        for item in items:
            try:
                edital = EditalScrapado(
                    numero_processo=item.get('numero', item.get('processNumber', '')),
                    objeto=item.get('objeto', item.get('object', item.get('description', ''))),
                    orgao=item.get('orgao', item.get('entidade', item.get('organ', ''))),
                    uf=item.get('uf', item.get('estado', '')),
                    municipio=item.get('municipio', item.get('cidade', '')),
                    modalidade=item.get('modalidade', item.get('modality', 'Pregão Eletrônico')),
                    valor_estimado=self._parse_valor(item.get('valor', item.get('valorEstimado'))),
                    data_abertura=self._parse_data(item.get('dataAbertura', item.get('dataSessao'))),
                    data_publicacao=self._parse_data(item.get('dataPublicacao', item.get('dataCriacao'))),
                    url_plataforma=self._montar_url(item),
                    plataforma='licitanet',
                    status=item.get('status', item.get('situacao', 'desconhecido')),
                    srp='registro' in (item.get('objeto', '') or '').lower(),
                    dados_extras={'id_plataforma': item.get('id')},
                )
                editais.append(edital)
            except Exception as e:
                logger.debug(f"Licitanet: Erro ao parsear item: {e}")

        return editais

    def _parse_container(self, container) -> Optional[EditalScrapado]:
        """Parse de um container HTML de processo."""
        text = container.get_text(separator=' | ', strip=True)
        if not text or len(text) < 20:
            return None

        link = container.find('a')
        url = ''
        if link and link.get('href'):
            href = link['href']
            url = href if href.startswith('http') else f"{self.BASE_URL}{href}"

        # Extrair número do processo
        num_match = re.search(
            r'(?:Pregão|PE|PP|CC|TP|Concorrência|Dispensa)\s*(?:Eletrônico|Presencial)?\s*[Nn]?[ºo°]?\s*\d+[/\-]\d+',
            text, re.IGNORECASE
        )
        numero = num_match.group(0) if num_match else ''

        # Extrair UF
        uf_match = re.search(r'\b([A-Z]{2})\s*[-–]\s*\w', text)
        if not uf_match:
            uf_match = re.search(r'/([A-Z]{2})\b', text)
        uf = uf_match.group(1) if uf_match else ''

        # Extrair valor
        valor_match = re.search(r'R\$\s*([\d.,]+)', text)
        valor = self._parse_valor(valor_match.group(1)) if valor_match else None

        # Extrair data
        data_match = re.search(r'(\d{2}/\d{2}/\d{4}\s*\d{2}:\d{2})', text)
        data = self._parse_data(data_match.group(1)) if data_match else None

        # Extrair órgão (geralmente antes do número do processo ou UF)
        orgao = ''
        orgao_match = re.search(r'(?:Prefeitura|Câmara|Secretaria|Governo|Fundação|Autarquia|Instituto)\s+[^|]+', text, re.IGNORECASE)
        if orgao_match:
            orgao = orgao_match.group(0).strip()[:200]

        return EditalScrapado(
            numero_processo=numero,
            objeto=text[:500],
            orgao=orgao,
            uf=uf,
            url_plataforma=url,
            valor_estimado=valor,
            data_abertura=data,
            plataforma='licitanet',
            modalidade='Pregão Eletrônico',
        )

    def _parse_link(self, link) -> Optional[EditalScrapado]:
        """Parse de um link de processo."""
        text = link.get_text(strip=True)
        href = link.get('href', '')
        if not text or len(text) < 10:
            return None

        url = href if href.startswith('http') else f"{self.BASE_URL}{href}"
        return EditalScrapado(
            numero_processo=text[:100],
            objeto=text,
            url_plataforma=url,
            plataforma='licitanet',
        )

    def _montar_url(self, item) -> str:
        pid = item.get('id', '')
        if pid:
            return f"{self.BASE_URL}/processos/{pid}"
        return f"{self.BASE_URL}/processos"

    @staticmethod
    def _parse_valor(valor) -> Optional[float]:
        if valor is None:
            return None
        if isinstance(valor, (int, float)):
            return float(valor)
        try:
            val_str = str(valor).replace('R$', '').replace(' ', '').strip()
            val_str = val_str.replace('.', '').replace(',', '.')
            return float(val_str) if val_str else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_data(data_str) -> Optional[datetime]:
        if not data_str:
            return None
        if isinstance(data_str, datetime):
            return data_str
        formatos = [
            '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%SZ',
            '%d/%m/%Y %H:%M', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y', '%Y-%m-%d',
        ]
        for fmt in formatos:
            try:
                return datetime.strptime(str(data_str)[:26], fmt)
            except ValueError:
                continue
        return None
