"""
SGL - Sistema de Gestão de Licitações
Aplicação principal Flask + APScheduler
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

    # Celery (mantém compatibilidade, mas não é mais obrigatório)
    _init_celery(app)

    # APScheduler — captação automática sem Redis
    _init_scheduler(app)

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

    # ── SSO: Integração com SIG ───────────────────────────────────────────
    @app.route('/api/auth/sso-sig', methods=['POST', 'OPTIONS'])
    def auth_sso_sig():
        """Valida JWT do SIG e retorna tokens SGL."""
        import os, secrets
        from flask import request, jsonify
        from flask_jwt_extended import create_access_token, create_refresh_token

        # CORS preflight
        if request.method == 'OPTIONS':
            from flask import make_response
            resp = make_response('', 204)
            resp.headers['Access-Control-Allow-Origin']  = '*'
            resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return resp

        try:
            import jwt as pyjwt
        except ImportError:
            return jsonify({'ok': False, 'erro': 'PyJWT não instalado no servidor.'}), 500

        data      = request.get_json(silent=True) or {}
        sso_token = (data.get('sso_token') or '').strip()

        if not sso_token:
            return jsonify({'ok': False, 'erro': 'sso_token ausente.'}), 400

        jwt_secret = os.environ.get('SIG_JWT_SECRET', '').strip()
        if not jwt_secret:
            return jsonify({'ok': False, 'erro': 'SIG_JWT_SECRET não configurado.'}), 500

        # Validar JWT do SIG
        try:
            payload = pyjwt.decode(sso_token, jwt_secret, algorithms=['HS256'])
        except pyjwt.ExpiredSignatureError:
            return jsonify({'ok': False, 'erro': 'Token expirado. Recarregue a página no SIG.'}), 401
        except pyjwt.InvalidTokenError as e:
            return jsonify({'ok': False, 'erro': f'Token inválido: {e}'}), 401

        if payload.get('origem') != 'SIG':
            return jsonify({'ok': False, 'erro': 'Token não originado do SIG.'}), 401

        username = (payload.get('username') or '').strip()
        nome     = (payload.get('nome') or username).strip()
        email    = (payload.get('email') or '').strip()
        is_admin = bool(payload.get('is_admin', False))

        if not username:
            return jsonify({'ok': False, 'erro': 'Usuário inválido no token.'}), 400

        # Criar ou atualizar usuário
        try:
            from sqlalchemy import text
            with db.engine.begin() as conn:
                row = conn.execute(
                    text('SELECT id FROM users WHERE username = :u'),
                    {'u': username}
                ).fetchone()

                if row:
                    user_id = row[0]
                    conn.execute(
                        text('UPDATE users SET nome = :n, email = :e WHERE username = :u'),
                        {'n': nome, 'e': email, 'u': username}
                    )
                else:
                    from werkzeug.security import generate_password_hash
                    pw = generate_password_hash(secrets.token_hex(32))
                    result = conn.execute(text("""
                        INSERT INTO users (username, nome, email, password_hash, is_admin, is_active)
                        VALUES (:u, :n, :e, :p, :a, TRUE) RETURNING id
                    """), {'u': username, 'n': nome, 'e': email, 'p': pw, 'a': is_admin})
                    user_id = result.fetchone()[0]

        except Exception as e:
            app.logger.error(f'[SSO-SIG] Erro BD: {e}')
            return jsonify({'ok': False, 'erro': 'Erro interno ao autenticar usuário.'}), 500

        # Gerar tokens SGL
        identity      = str(user_id)
        access_token  = create_access_token(identity=identity)
        refresh_token = create_refresh_token(identity=identity)

        return jsonify({
            'ok':            True,
            'access_token':  access_token,
            'refresh_token': refresh_token,
            'user': {
                'id':       user_id,
                'username': username,
                'nome':     nome,
                'email':    email,
                'is_admin': is_admin,
            }
        }), 200
    # ─────────────────────────────────────────────────────────────────────

    return app


def _init_scheduler(app):
    """Inicializa APScheduler para captação automática."""
    try:
        from .scheduler import init_scheduler
        init_scheduler(app)
    except Exception as e:
        app.logger.warning(f"APScheduler não inicializado: {e}")


def _init_celery(app):
    """Conecta o Celery ao contexto do Flask (mantém compatibilidade)."""
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
