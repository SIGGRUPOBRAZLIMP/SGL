"""
SGL - Serviço de Scraping
Orquestra os scrapers BLL, BNC e Licitanet.
Converte editais scrapados para o modelo do banco.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from ..models.database import db, Edital, Triagem
from .scrapers import SCRAPERS, EditalScrapado

logger = logging.getLogger(__name__)


class ScraperService:
    """
    Serviço que orquestra os scrapers e persiste os resultados.
    """

    def __init__(self, plataformas: list[str] = None):
        """
        Args:
            plataformas: Lista de plataformas para usar. Default: todas.
                         Opções: 'bll', 'bnc', 'licitanet'
        """
        self.plataformas = plataformas or list(SCRAPERS.keys())
        self.scrapers = {}

        for nome in self.plataformas:
            if nome in SCRAPERS:
                self.scrapers[nome] = SCRAPERS[nome](
                    timeout=30,
                    max_retries=3,
                    delay_entre_requests=1.5,  # Respeitar rate limits
                )
            else:
                logger.warning(f"Scraper '{nome}' não encontrado. Disponíveis: {list(SCRAPERS.keys())}")

    def executar_scraping(
        self,
        termo: Optional[str] = None,
        uf: Optional[str] = None,
        data_inicial: Optional[str] = None,
        data_final: Optional[str] = None,
        max_paginas: int = 3,
        plataformas: Optional[list[str]] = None,
    ) -> dict:
        """
        Executa scraping em todas as plataformas configuradas.

        Returns:
            dict com estatísticas por plataforma
        """
        stats = {
            'total_encontrados': 0,
            'novos_salvos': 0,
            'duplicados': 0,
            'erros': 0,
            'por_plataforma': {},
        }

        scrapers_usar = plataformas or list(self.scrapers.keys())

        for nome in scrapers_usar:
            scraper = self.scrapers.get(nome)
            if not scraper:
                logger.warning(f"Scraper '{nome}' não inicializado")
                continue

            plat_stats = {
                'encontrados': 0,
                'novos': 0,
                'duplicados': 0,
                'erros': 0,
            }

            try:
                logger.info(f"=== Scraping {nome.upper()} ===")

                editais = scraper.buscar_todos(
                    termo=termo,
                    uf=uf,
                    data_inicial=data_inicial,
                    data_final=data_final,
                    max_paginas=max_paginas,
                )

                plat_stats['encontrados'] = len(editais)

                for edital_scrapado in editais:
                    try:
                        resultado = self._salvar_edital(edital_scrapado)
                        plat_stats[resultado] += 1
                    except Exception as e:
                        logger.error(f"{nome}: Erro ao salvar edital: {e}")
                        plat_stats['erros'] += 1

                logger.info(f"{nome.upper()}: {plat_stats}")

            except Exception as e:
                logger.error(f"Erro no scraper {nome}: {e}")
                plat_stats['erros'] += 1

            stats['por_plataforma'][nome] = plat_stats
            stats['total_encontrados'] += plat_stats['encontrados']
            stats['novos_salvos'] += plat_stats['novos']
            stats['duplicados'] += plat_stats['duplicados']
            stats['erros'] += plat_stats['erros']

        logger.info(f"=== Scraping total: {stats} ===")
        return stats

    def _salvar_edital(self, edital_scrapado: EditalScrapado) -> str:
        """
        Salva um edital scrapado no banco.

        Returns:
            'novos', 'duplicados', ou 'erros'
        """
        try:
            # Verificar duplicata por hash
            hash_val = edital_scrapado.hash_unico
            existente = Edital.query.filter_by(hash_scraper=hash_val).first()
            if existente:
                return 'duplicados'

            # Verificar duplicata por número de processo + órgão
            if edital_scrapado.numero_processo:
                existente2 = Edital.query.filter(
                    Edital.numero_processo == edital_scrapado.numero_processo,
                    Edital.orgao_razao_social == edital_scrapado.orgao,
                ).first()
                if existente2:
                    return 'duplicados'

            # Criar edital no banco
            edital = Edital(
                numero_processo=edital_scrapado.numero_processo or None,
                objeto_resumo=(edital_scrapado.objeto or '')[:500],
                objeto_completo=edital_scrapado.objeto,
                orgao_razao_social=edital_scrapado.orgao or None,
                uf=edital_scrapado.uf or None,
                municipio=edital_scrapado.municipio or None,
                modalidade_nome=edital_scrapado.modalidade or 'Pregão Eletrônico',
                valor_estimado=edital_scrapado.valor_estimado,
                data_abertura_proposta=edital_scrapado.data_abertura,
                data_publicacao=edital_scrapado.data_publicacao,
                url_original=edital_scrapado.url_plataforma,
                plataforma_origem=edital_scrapado.plataforma,
                status='captado',
                srp=edital_scrapado.srp,
                hash_scraper=hash_val,
                numero_controle_pncp=edital_scrapado.numero_pncp or None,
            )

            db.session.add(edital)
            db.session.flush()

            # Criar triagem pendente
            triagem = Triagem(
                edital_id=edital.id,
                decisao='pendente',
                prioridade=self._calcular_prioridade(edital_scrapado),
            )
            db.session.add(triagem)
            db.session.commit()

            logger.info(
                f"Novo ({edital_scrapado.plataforma}): "
                f"{edital_scrapado.numero_processo} | {(edital_scrapado.objeto or '')[:60]}"
            )
            return 'novos'

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao salvar edital scrapado: {e}")
            return 'erros'

    @staticmethod
    def _calcular_prioridade(edital: EditalScrapado) -> str:
        """Calcula prioridade com base no valor e prazo."""
        if edital.valor_estimado and edital.valor_estimado > 500000:
            return 'alta'
        if edital.data_abertura:
            try:
                now = datetime.now(timezone.utc)
                if edital.data_abertura.tzinfo is None:
                    from datetime import timezone as tz
                    data = edital.data_abertura.replace(tzinfo=tz.utc)
                else:
                    data = edital.data_abertura
                dias = (data - now).days
                if dias <= 5:
                    return 'alta'
                elif dias <= 10:
                    return 'media'
            except Exception:
                pass
        return 'media'
