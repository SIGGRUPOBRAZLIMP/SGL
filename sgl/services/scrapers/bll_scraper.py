"""
SGL - Scraper BLL Compras
Bolsa de Licitações e Leilões do Brasil
URL: https://bllcompras.com
Busca pública: https://bllcompras.com/Process/ProcessSearchPublic
"""
import logging
import re
from datetime import datetime
from typing import Optional
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, EditalScrapado

logger = logging.getLogger(__name__)


class BLLScraper(BaseScraper):
    """Scraper para BLL Compras (bllcompras.com)."""

    PLATAFORMA = 'bll'
    BASE_URL = 'https://bllcompras.com'

    # Mapeamento de status
    STATUS_MAP = {
        'aberto': 'aberto_propostas',
        'em andamento': 'em_disputa',
        'encerrado': 'encerrado',
        'suspenso': 'suspenso',
        'revogado': 'revogado',
        'deserto': 'deserto',
        'fracassado': 'fracassado',
        'homologado': 'homologado',
        'aguardando': 'aguardando',
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Headers específicos para BLL
        self.session.headers.update({
            'Referer': 'https://bllcompras.com/',
            'Origin': 'https://bllcompras.com',
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
        """
        Busca editais no BLL Compras.
        Tenta API interna primeiro, fallback para HTML.
        """
        # Tentar API interna (JSON)
        try:
            return self._buscar_via_api(termo, uf, data_inicial, data_final, pagina)
        except Exception as e:
            logger.info(f"BLL API interna falhou ({e}), tentando HTML...")

        # Fallback: scraping HTML
        try:
            return self._buscar_via_html(termo, uf, pagina)
        except Exception as e:
            logger.error(f"BLL HTML scraping falhou: {e}")
            return []

    def _buscar_via_api(self, termo, uf, data_inicial, data_final, pagina) -> list[EditalScrapado]:
        """Tenta endpoints de API interna do BLL."""
        # Endpoint comum em plataformas .NET MVC
        endpoints = [
            '/Process/GetPublicProcessList',
            '/api/Process/Search',
            '/Process/SearchPublicProcess',
        ]

        params = {
            'page': pagina,
            'pageSize': 50,
        }
        if termo:
            params['searchText'] = termo
        if uf:
            params['uf'] = uf

        for endpoint in endpoints:
            try:
                url = f"{self.BASE_URL}{endpoint}"
                resp = self._get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    return self._parse_api_response(data)
            except Exception:
                continue

        raise Exception("Nenhum endpoint de API encontrado")

    def _buscar_via_html(self, termo, uf, pagina) -> list[EditalScrapado]:
        """Scraping da página pública de busca."""
        # param1=1 = processos em andamento, param1=0 = todos
        url = f"{self.BASE_URL}/Process/ProcessSearchPublic"
        params = {'param1': 1}

        resp = self._get(url, params=params)
        soup = BeautifulSoup(resp.text, 'html.parser')

        editais = []

        # Buscar tabelas ou cards com dados de processos
        # Pattern 1: Tabela com rows
        rows = soup.select('table tbody tr, .process-item, .card-process, [class*=process], [class*=Process]')

        for row in rows:
            try:
                edital = self._parse_html_row(row)
                if edital:
                    # Aplicar filtros
                    if termo and termo.lower() not in (edital.objeto or '').lower():
                        continue
                    if uf and uf.upper() != (edital.uf or '').upper():
                        continue
                    editais.append(edital)
            except Exception as e:
                logger.debug(f"BLL: Erro ao parsear row: {e}")
                continue

        # Pattern 2: Se não encontrou via tabela, buscar links de processos
        if not editais:
            links = soup.select('a[href*="/Process/"], a[href*="process"]')
            for link in links[:50]:  # Limitar
                try:
                    edital = self._parse_link_element(link)
                    if edital:
                        editais.append(edital)
                except Exception:
                    continue

        return editais

    def _parse_api_response(self, data) -> list[EditalScrapado]:
        """Parse de resposta JSON da API interna."""
        editais = []

        # Tentar diferentes estruturas de resposta
        items = data if isinstance(data, list) else data.get('data', data.get('items', data.get('processes', [])))

        for item in items:
            try:
                edital = EditalScrapado(
                    numero_processo=item.get('processNumber', item.get('numero', '')),
                    objeto=item.get('object', item.get('objeto', item.get('description', ''))),
                    orgao=item.get('organName', item.get('orgao', item.get('buyer', ''))),
                    uf=item.get('uf', item.get('state', '')),
                    municipio=item.get('city', item.get('municipio', '')),
                    modalidade=item.get('modality', item.get('modalidade', 'Pregão Eletrônico')),
                    valor_estimado=self._parse_valor(item.get('estimatedValue', item.get('valor'))),
                    data_abertura=self._parse_data(item.get('openingDate', item.get('dataAbertura'))),
                    data_publicacao=self._parse_data(item.get('publicationDate', item.get('dataPublicacao'))),
                    url_plataforma=self._montar_url_processo(item),
                    plataforma='bll',
                    status=self._mapear_status(item.get('status', '')),
                    srp='registro' in (item.get('object', '') or '').lower(),
                    dados_extras={'id_plataforma': item.get('id', item.get('processId'))},
                )
                editais.append(edital)
            except Exception as e:
                logger.debug(f"BLL: Erro ao parsear item API: {e}")

        return editais

    def _parse_html_row(self, row) -> Optional[EditalScrapado]:
        """Parse de uma linha HTML de processo."""
        cells = row.find_all(['td', 'div', 'span'])
        text = row.get_text(separator='|', strip=True)

        if not text or len(text) < 20:
            return None

        # Tentar extrair dados do texto
        link = row.find('a')
        url = ''
        if link and link.get('href'):
            href = link['href']
            url = href if href.startswith('http') else f"{self.BASE_URL}{href}"

        # Extrair número do processo
        num_match = re.search(r'(?:PE|PP|CC|TP|DL|IN)\s*[Nn]?[ºo°]?\s*\d+[/\-]\d+', text)
        numero = num_match.group(0) if num_match else ''

        # Extrair UF
        uf_match = re.search(r'\b([A-Z]{2})\b', text)
        uf = uf_match.group(1) if uf_match else ''

        # Extrair valor
        valor_match = re.search(r'R\$\s*([\d.,]+)', text)
        valor = self._parse_valor(valor_match.group(1)) if valor_match else None

        return EditalScrapado(
            numero_processo=numero,
            objeto=text[:500],
            uf=uf,
            url_plataforma=url,
            valor_estimado=valor,
            plataforma='bll',
            modalidade='Pregão Eletrônico',
        )

    def _parse_link_element(self, link) -> Optional[EditalScrapado]:
        """Parse de um elemento <a> de processo."""
        href = link.get('href', '')
        text = link.get_text(strip=True)

        if not text or len(text) < 10:
            return None

        url = href if href.startswith('http') else f"{self.BASE_URL}{href}"

        return EditalScrapado(
            numero_processo=text[:100],
            objeto=text,
            url_plataforma=url,
            plataforma='bll',
        )

    def _montar_url_processo(self, item) -> str:
        """Monta URL do processo a partir dos dados da API."""
        pid = item.get('id', item.get('processId', ''))
        if pid:
            return f"{self.BASE_URL}/Process/ProcessView/{pid}"
        return self.BASE_URL

    def _mapear_status(self, status_raw: str) -> str:
        """Mapeia status do BLL para status padronizado."""
        status_lower = (status_raw or '').lower()
        for key, val in self.STATUS_MAP.items():
            if key in status_lower:
                return val
        return status_raw or 'desconhecido'

    @staticmethod
    def _parse_valor(valor) -> Optional[float]:
        """Parse de valor monetário."""
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
        """Parse de data em vários formatos."""
        if not data_str:
            return None
        if isinstance(data_str, datetime):
            return data_str

        formatos = [
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%SZ',
            '%d/%m/%Y %H:%M',
            '%d/%m/%Y %H:%M:%S',
            '%d/%m/%Y',
            '%Y-%m-%d',
        ]
        for fmt in formatos:
            try:
                return datetime.strptime(str(data_str)[:26], fmt)
            except ValueError:
                continue
        return None
