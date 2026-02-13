"""
SGL - Sistema de Gestão de Licitações
Aplicação principal Flask + Celery
"""
import os
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate

from .models.database import db
from .config.settings import config_map


def create_app(config_name=None):
    """Factory para criação da aplicação Flask."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_map.get(config_name, config_map['default']))

    # Extensões
    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    JWTManager(app)
    Migrate(app, db)

    # Integrar Celery com Flask
    _init_celery(app)

    # Registrar blueprints (rotas da API)
    from .api.routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    # Criar tabelas no primeiro request (dev only)
    @app.before_request
    def create_tables():
        app.before_request_funcs[None].remove(create_tables)
        db.create_all()

    @app.route('/health')
    def health():
        return {'status': 'ok', 'service': 'SGL - Sistema de Gestão de Licitações'}

    return app


def _init_celery(app):
    """Conecta o Celery ao contexto do Flask."""
    try:
        from .celery_app import celery

        celery.conf.update(app.config)

        class ContextTask(celery.Task):
            """Garante que tasks rodem dentro do contexto Flask."""
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask
        app.extensions['celery'] = celery

    except Exception as e:
        app.logger.warning(f"Celery não inicializado: {e}")
