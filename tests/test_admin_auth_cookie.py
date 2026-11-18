from fastapi.testclient import TestClient
from normativa.api.main import app
from normativa.config import settings

client = TestClient(app)


def test_admin_auth_cookie_lifecycle():
    # 1. Sin autenticar, /api/admin/me devuelve 401
    res_me_anon = client.get("/api/admin/me")
    assert res_me_anon.status_code == 401

    # 2. Login inválido no establece cookie y devuelve 401
    res_bad = client.post("/api/admin/login", json={"admin_key": "clave_invalida"})
    assert res_bad.status_code == 401
    assert "admin_session" not in client.cookies

    # 3. Login válido establece cookie HttpOnly, Path=/, SameSite=lax
    res_ok = client.post("/api/admin/login", json={"admin_key": settings.ADMIN_API_KEY})
    assert res_ok.status_code == 200
    assert "admin_session" in client.cookies

    # Verificar encabezado Set-Cookie
    set_cookie_header = res_ok.headers.get("set-cookie", "")
    assert "admin_session=" in set_cookie_header
    assert "HttpOnly" in set_cookie_header or "httponly" in set_cookie_header.lower()
    assert "Path=/" in set_cookie_header or "path=/" in set_cookie_header.lower()

    # 4. Con la cookie de sesión, /api/admin/me devuelve authenticated=True
    res_me_auth = client.get("/api/admin/me")
    assert res_me_auth.status_code == 200
    assert res_me_auth.json() == {"authenticated": True, "role": "admin"}

    # 5. Logout invalida la cookie con Max-Age=0 y Path=/
    res_logout = client.post("/api/admin/logout")
    assert res_logout.status_code == 200

    logout_cookie = res_logout.headers.get("set-cookie", "")
    assert "Max-Age=0" in logout_cookie or "max-age=0" in logout_cookie.lower()

    # 6. Tras logout, /api/admin/me vuelve a responder 401
    res_me_after = client.get("/api/admin/me")
    assert res_me_after.status_code == 401
