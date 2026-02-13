"""
SGL - Sistema de Gestão de Licitações
Configurações do sistema
"""
import os
from datetime import timedelta


class Config:
    """Configuração base"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'sgl-dev-secret-key-change-in-production')
    
    # Banco de Dados
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        'postgresql://sgl_user:sgl_pass@localhost:5432/sgl_db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # PNCP API
    PNCP_API_BASE_URL = 'https://pncp.gov.br/api/consulta/v1'
    PNCP_API_TIMEOUT = 30  # segundos
    PNCP_API_PAGE_SIZE = 50
    PNCP_API_MAX_RETRIES = 3
    
    # Compras.gov.br API
    COMPRAS_GOV_API_BASE_URL = 'http://compras.dados.gov.br'
    
    # Claude API (Interpretação de Editais)
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
    CLAUDE_MODEL = 'claude-sonnet-4-5-20250929'
    CLAUDE_MAX_TOKENS = 8000
    
    # Cloudinary (Storage de documentos)
    CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME', '')
    CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY', '')
    CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET', '')
    
    # Celery (Filas de tarefas)
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    
    # Captação automática
    CAPTACAO_INTERVALO_MINUTOS = 30
    CAPTACAO_HORARIO_INICIO = 7   # 7h
    CAPTACAO_HORARIO_FIM = 20     # 20h
    
    # Scraping
    SCRAPING_RATE_LIMIT_SECONDS = 2  # intervalo mínimo entre requisições
    SCRAPING_USER_AGENT = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )
    
    # Notificações
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    
    # Paginação padrão
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100


class DevelopmentConfig(Config):
    """Configuração de desenvolvimento"""
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """Configuração de produção"""
    DEBUG = False
    SQLALCHEMY_ECHO = False


class TestingConfig(Config):
    """Configuração de testes"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://sgl_user:sgl_pass@localhost:5432/sgl_test_db'


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
