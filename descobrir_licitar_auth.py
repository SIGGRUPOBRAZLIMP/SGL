"""
Descobrir fluxo OAuth2 do Licitar Digital para automatizar login.
Simula o browser: segue redirects, posta credenciais, captura code, troca por token.
"""
import re
import requests
from urllib.parse import urlparse, parse_qs, urlencode

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
})

CPF = "07923334625"
SENHA = "Gbraz24@"

print("=" * 60)
print("DESCOBRINDO FLUXO OAuth2 LICITAR DIGITAL")
print("=" * 60)

# ============================================================
# PASSO 1: Acessar página de login e seguir redirects
# ============================================================
print("\n[1] Acessando página de login...")
urls_tentativa = [
    "https://app2.licitardigital.com.br/login",
    "https://app2.licitardigital.com.br/auth",
    "https://app2.licitardigital.com.br/",
    "https://licitardigital.com.br/login",
]

login_page_url = None
login_page_html = None

for url in urls_tentativa:
    try:
        resp = session.get(url, allow_redirects=True, timeout=15)
        print(f"  {url}")
        print(f"    Status: {resp.status_code}")
        print(f"    Final URL: {resp.url}")
        print(f"    Redirects: {[r.url for r in resp.history]}")
        
        # Procurar form de login ou redirect para OAuth
        if resp.status_code == 200:
            html = resp.text[:5000]
            
            # Procurar action de form
            forms = re.findall(r'<form[^>]*action=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if forms:
                print(f"    Forms encontrados: {forms}")
            
            # Procurar URLs de auth/keycloak/OAuth
            auth_urls = re.findall(r'https?://[^\s"\'<>]+(?:auth|keycloak|oauth|realms|login)[^\s"\'<>]*', html, re.IGNORECASE)
            if auth_urls:
                print(f"    Auth URLs: {auth_urls[:5]}")
            
            # Procurar client_id
            client_ids = re.findall(r'client_id=([^&"\']+)', html)
            if client_ids:
                print(f"    Client IDs: {client_ids}")
            
            # Procurar redirect_uri
            redirect_uris = re.findall(r'redirect_uri=([^&"\']+)', html)
            if redirect_uris:
                print(f"    Redirect URIs: {redirect_uris}")
            
            login_page_url = resp.url
            login_page_html = resp.text
            
    except Exception as e:
        print(f"  {url} -> ERRO: {e}")

# ============================================================
# PASSO 2: Tentar endpoints de login direto na API
# ============================================================
print("\n[2] Tentando endpoints de login direto na API...")

api_endpoints = [
    ("POST", "https://manager-api.licitardigital.com.br/auth/login", {"cpf": CPF, "password": SENHA}),
    ("POST", "https://manager-api.licitardigital.com.br/auth/login", {"login": CPF, "password": SENHA}),
    ("POST", "https://manager-api.licitardigital.com.br/auth/login", {"username": CPF, "password": SENHA}),
    ("POST", "https://manager-api.licitardigital.com.br/auth/login", {"document": CPF, "password": SENHA}),
    ("POST", "https://manager-api.licitardigital.com.br/auth/authenticate", {"cpf": CPF, "password": SENHA}),
    ("POST", "https://manager-api.licitardigital.com.br/auth/authenticate", {"login": CPF, "password": SENHA}),
    ("POST", "https://manager-api.licitardigital.com.br/auth/signin", {"cpf": CPF, "password": SENHA}),
    ("POST", "https://manager-api.licitardigital.com.br/auth/signin", {"login": CPF, "password": SENHA}),
    ("POST", "https://manager-api.licitardigital.com.br/user/login", {"cpf": CPF, "password": SENHA}),
    ("POST", "https://manager-api.licitardigital.com.br/user/authenticate", {"cpf": CPF, "password": SENHA}),
    ("POST", "https://manager-api.licitardigital.com.br/login", {"cpf": CPF, "password": SENHA}),
    ("POST", "https://manager-api.licitardigital.com.br/auth/getTokenByCredentials", {"cpf": CPF, "password": SENHA, "clientId": "php-manager"}),
    ("POST", "https://manager-api.licitardigital.com.br/auth/getTokenByCredentials", {"login": CPF, "password": SENHA, "clientId": "php-manager"}),
    ("POST", "https://manager-api.licitardigital.com.br/auth/token", {"cpf": CPF, "password": SENHA, "clientId": "php-manager"}),
    ("POST", "https://manager-api.licitardigital.com.br/auth/token", {"grant_type": "password", "username": CPF, "password": SENHA, "client_id": "php-manager"}),
    # Keycloak-style
    ("POST", "https://manager-api.licitardigital.com.br/auth/realms/licitardigital/protocol/openid-connect/token", 
     {"grant_type": "password", "username": CPF, "password": SENHA, "client_id": "php-manager"}),
]

for method, url, payload in api_endpoints:
    try:
        headers = {"Content-Type": "application/json", "Origin": "https://app2.licitardigital.com.br"}
        resp = session.post(url, json=payload, headers=headers, timeout=10)
        
        status = resp.status_code
        body = resp.text[:300]
        
        if status in [200, 201]:
            print(f"  ✅ {url}")
            print(f"     Keys: {list(payload.keys())}")
            print(f"     Status: {status}")
            print(f"     Response: {body}")
            
            # Tentar extrair token
            try:
                data = resp.json()
                token = (
                    data.get("token") or data.get("access_token") or data.get("accessToken") or
                    (data.get("data", {}) or {}).get("token") or 
                    (data.get("data", {}) or {}).get("accessToken") or
                    (data.get("data", {}) or {}).get("access_token")
                )
                if token:
                    print(f"     🎉 TOKEN ENCONTRADO: {token[:50]}...")
            except:
                pass
        elif status not in [404, 405]:
            print(f"  ❌ {url} [{status}] keys={list(payload.keys())} -> {body[:100]}")
            
    except Exception as e:
        print(f"  ❌ {url} -> ERRO: {e}")

# ============================================================
# PASSO 3: Explorar se há Keycloak por trás
# ============================================================
print("\n[3] Procurando Keycloak ou outro IdP...")

keycloak_urls = [
    "https://auth.licitardigital.com.br",
    "https://sso.licitardigital.com.br",
    "https://login.licitardigital.com.br",
    "https://keycloak.licitardigital.com.br",
    "https://id.licitardigital.com.br",
    "https://accounts.licitardigital.com.br",
    "https://manager-api.licitardigital.com.br/auth/.well-known/openid-configuration",
    "https://manager-api.licitardigital.com.br/.well-known/openid-configuration",
]

for url in keycloak_urls:
    try:
        resp = session.get(url, allow_redirects=True, timeout=8)
        if resp.status_code == 200:
            print(f"  ✅ {url}")
            print(f"     Final URL: {resp.url}")
            print(f"     Body: {resp.text[:200]}")
        elif resp.status_code not in [404, 403, 502, 503]:
            print(f"  {url} -> {resp.status_code}")
    except Exception as e:
        pass

# ============================================================
# PASSO 4: Analisar o HTML da página de login
# ============================================================
if login_page_html:
    print("\n[4] Analisando HTML da página de login...")
    
    # Procurar iframes (SSO embedding)
    iframes = re.findall(r'<iframe[^>]*src=["\']([^"\']+)["\']', login_page_html, re.IGNORECASE)
    if iframes:
        print(f"  Iframes: {iframes}")
    
    # Procurar scripts com URLs de auth
    scripts = re.findall(r'<script[^>]*src=["\']([^"\']*(?:auth|login|keycloak)[^"\']*)["\']', login_page_html, re.IGNORECASE)
    if scripts:
        print(f"  Scripts auth: {scripts}")
    
    # Procurar qualquer menção a keycloak, cognito, auth0, etc
    for provider in ['keycloak', 'cognito', 'auth0', 'firebase', 'okta', 'azure']:
        if provider.lower() in login_page_html.lower():
            print(f"  🔍 Referência a '{provider}' encontrada no HTML!")
            # Encontrar contexto
            idx = login_page_html.lower().find(provider.lower())
            context = login_page_html[max(0,idx-100):idx+200]
            print(f"     Contexto: ...{context}...")

    # Procurar authorization URL
    auth_pattern = re.findall(r'(https?://[^\s"\']+/(?:authorize|auth|login)\?[^\s"\']+)', login_page_html)
    if auth_pattern:
        print(f"  Authorization URLs: {auth_pattern}")

print("\n" + "=" * 60)
print("DESCOBERTA CONCLUÍDA")
print("=" * 60)
