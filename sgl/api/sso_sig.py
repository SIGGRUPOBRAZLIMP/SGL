"""
SGL — Endpoint de SSO via JWT do SIG
Arquivo: sgl/api/sso_sig.py

Fluxo:
  1. SIG abre iframe com URL: https://sgl.../  ?sso_token=<JWT>
  2. React detecta ?sso_token= na URL e chama POST /api/auth/sso-sig
  3. Este endpoint valida o JWT, cria/encontra o usuário e retorna tokens SGL
  4. React armazena os tokens e prossegue normalmente
"""
import os
import secrets
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token

try:
    import jwt as pyjwt
except ImportError:
    raise ImportError("PyJWT não instalado. Adicione 'PyJWT>=2.0.0' ao requirements.txt")

sso_bp = Blueprint("sso", __name__)


def _get_secret() -> str:
    s = os.environ.get("SIG_JWT_SECRET", "").strip()
    if not s:
        raise ValueError("SIG_JWT_SECRET não configurado nas variáveis de ambiente.")
    return s


@sso_bp.route("/auth/sso-sig", methods=["POST"])
def sso_sig():
    """
    Valida token JWT do SIG e retorna tokens de acesso SGL.

    Body: { "sso_token": "<JWT gerado pelo SIG>" }

    Retorno sucesso:
    {
        "ok": true,
        "access_token": "...",
        "refresh_token": "...",
        "user": { "id": 1, "username": "...", "nome": "...", "is_admin": false }
    }
    """
    from .models.database import db
    from sqlalchemy import text

    data      = request.get_json(silent=True) or {}
    sso_token = (data.get("sso_token") or "").strip()

    if not sso_token:
        return jsonify({"ok": False, "erro": "sso_token ausente."}), 400

    # ── 1. Validar JWT do SIG ──────────────────────────────────────
    try:
        secret  = _get_secret()
        payload = pyjwt.decode(sso_token, secret, algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        return jsonify({"ok": False, "erro": "Token expirado. Recarregue a página no SIG."}), 401
    except pyjwt.InvalidTokenError as e:
        return jsonify({"ok": False, "erro": f"Token inválido: {e}"}), 401
    except ValueError as e:
        return jsonify({"ok": False, "erro": str(e)}), 500

    if payload.get("origem") != "SIG":
        return jsonify({"ok": False, "erro": "Token não originado do SIG."}), 401

    username = (payload.get("username") or "").strip()
    nome     = (payload.get("nome") or username).strip()
    email    = (payload.get("email") or "").strip()
    is_admin = bool(payload.get("is_admin", False))

    if not username:
        return jsonify({"ok": False, "erro": "Usuário inválido no token."}), 400

    # ── 2. Criar ou atualizar usuário no SGL ──────────────────────
    try:
        with db.engine.begin() as conn:
            row = conn.execute(
                text("SELECT id, username, is_admin FROM users WHERE username = :u"),
                {"u": username}
            ).fetchone()

            if row:
                user_id = row[0]
                # Atualiza nome/email caso tenham mudado no SIG
                conn.execute(text("""
                    UPDATE users
                    SET nome = :n, email = :e, is_active = TRUE
                    WHERE username = :u
                """), {"n": nome, "e": email, "u": username})
            else:
                # Cria usuário — senha aleatória (login só via SSO do SIG)
                from werkzeug.security import generate_password_hash
                senha_hash = generate_password_hash(secrets.token_hex(32))
                result = conn.execute(text("""
                    INSERT INTO users (username, nome, email, password_hash, is_admin, is_active)
                    VALUES (:u, :n, :e, :p, :a, TRUE)
                    RETURNING id
                """), {
                    "u": username, "n": nome, "e": email,
                    "p": senha_hash, "a": is_admin
                })
                user_id = result.fetchone()[0]

    except Exception as e:
        import traceback
        print(f"[SSO-SIG] Erro BD: {e}\n{traceback.format_exc()}")
        return jsonify({"ok": False, "erro": "Erro interno ao autenticar usuário."}), 500

    # ── 3. Gerar tokens SGL (flask_jwt_extended) ───────────────────
    identity      = str(user_id)
    access_token  = create_access_token(identity=identity)
    refresh_token = create_refresh_token(identity=identity)

    return jsonify({
        "ok":            True,
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "user": {
            "id":       user_id,
            "username": username,
            "nome":     nome,
            "email":    email,
            "is_admin": is_admin,
        }
    }), 200
