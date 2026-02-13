"""
SGL - Scraper BNC Compras
Bolsa Nacional de Compras
URL: https://bnccompras.com
Busca pública: https://bnccompras.com/Process/ProcessSearchPublic
"""
import logging
import re
from datetime import datetime
from typing import Optional
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, EditalScrapado

logger = logging.getLogger(__name__)


class BNCScraper(BaseScraper):
    """Scraper para BNC Compras (bnccompras.com)."""

    PLATAFORMA = 'bnc'
    BASE_URL = 'https://bnccompras.com'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session.headers.update({
            'Referer': 'https://bnccompras.com/',
            'Origin': 'https://bnccompras.com',
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
        """Busca editais no BNC Compras."""

        # Tentar API interna primeiro
        try:
            return self._buscar_via_api(termo, uf, data_inicial, data_final, pagina)
        except Exception as e:
            logger.info(f"BNC API interna falhou ({e}), tentando HTML...")

        # Fallback: HTML
        try:
            return self._buscar_via_html(termo, uf, pagina)
        except Exception as e:
            logger.error(f"BNC HTML scraping falhou: {e}")
            return []

    def _buscar_via_api(self, termo, uf, data_inicial, data_final, pagina) -> list[EditalScrapado]:
        """Tenta endpoints de API interna do BNC."""
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
        url = f"{self.BASE_URL}/Process/ProcessSearchPublic"
        params = {'param1': 1}

        resp = self._get(url, params=params)
        soup = BeautifulSoup(resp.text, 'html.parser')

        editais = []

        # Buscar elementos de processo
        rows = soup.select('table tbody tr, .process-item, .card-process, [class*=process], [class*=Process]')

        for row in rows:
            try:
                edital = self._parse_html_row(row)
                if edital:
                    if termo and termo.lower() not in (edital.objeto or '').lower():
                        continue
                    if uf and uf.upper() != (edital.uf or '').upper():
                        continue
                    editais.append(edital)
            except Exception as e:
                logger.debug(f"BNC: Erro ao parsear row: {e}")

        # Fallback: links
        if not editais:
            links = soup.select('a[href*="/Process/"], a[href*="process"]')
            for link in links[:50]:
                try:
                    text = link.get_text(strip=True)
                    href = link.get('href', '')
                    if text and len(text) > 10:
                        url_proc = href if href.startswith('http') else f"{self.BASE_URL}{href}"
                        editais.append(EditalScrapado(
                            numero_processo=text[:100],
                            objeto=text,
                            url_plataforma=url_proc,
                            plataforma='bnc',
                        ))
                except Exception:
                    continue

        return editais

    def _parse_api_response(self, data) -> list[EditalScrapado]:
        """Parse de resposta JSON."""
        editais = []
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
                    url_plataforma=self._montar_url(item),
                    plataforma='bnc',
                    status=item.get('status', 'desconhecido'),
                    srp='registro' in (item.get('object', '') or '').lower(),
                    dados_extras={'id_plataforma': item.get('id', item.get('processId'))},
                )
                editais.append(edital)
            except Exception as e:
                logger.debug(f"BNC: Erro ao parsear item: {e}")

        return editais

    def _parse_html_row(self, row) -> Optional[EditalScrapado]:
        """Parse de linha HTML."""
        text = row.get_text(separator='|', strip=True)
        if not text or len(text) < 20:
            return None

        link = row.find('a')
        url = ''
        if link and link.get('href'):
            href = link['href']
            url = href if href.startswith('http') else f"{self.BASE_URL}{href}"

        num_match = re.search(r'(?:PE|PP|CC|TP|DL|IN)\s*[Nn]?[ºo°]?\s*\d+[/\-]\d+', text)
        numero = num_match.group(0) if num_match else ''

        uf_match = re.search(r'\b([A-Z]{2})\b', text)
        uf = uf_match.group(1) if uf_match else ''

        valor_match = re.search(r'R\$\s*([\d.,]+)', text)
        valor = self._parse_valor(valor_match.group(1)) if valor_match else None

        return EditalScrapado(
            numero_processo=numero,
            objeto=text[:500],
            uf=uf,
            url_plataforma=url,
            valor_estimado=valor,
            plataforma='bnc',
            modalidade='Pregão Eletrônico',
        )

    def _montar_url(self, item) -> str:
        pid = item.get('id', item.get('processId', ''))
        if pid:
            return f"{self.BASE_URL}/Process/ProcessView/{pid}"
        return self.BASE_URL

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
