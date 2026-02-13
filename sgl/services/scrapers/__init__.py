"""
SGL - Scrapers de Plataformas de Licitação
Plataformas suportadas: BLL, BNC, Licitanet
"""
from .base_scraper import BaseScraper, EditalScrapado
from .bll_scraper import BLLScraper
from .bnc_scraper import BNCScraper
from .licitanet_scraper import LicitanetScraper

# Registry de scrapers disponíveis
SCRAPERS = {
    'bll': BLLScraper,
    'bnc': BNCScraper,
    'licitanet': LicitanetScraper,
}

__all__ = [
    'BaseScraper', 'EditalScrapado',
    'BLLScraper', 'BNCScraper', 'LicitanetScraper',
    'SCRAPERS',
]
