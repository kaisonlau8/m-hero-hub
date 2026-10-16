"""页面反馈：Spin 先于慢请求输出，提交入口与中文文案仍在最终 HTML 里。"""
import importlib.util
import io
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"


def load_app(monkeypatch, auth="off"):
    for key in list(os.environ):
        if key.startswith("MHERO_"):
            monkeypatch.delenv(key, raising=False)
    if auth == "on":
        monkeypatch.setenv("MHERO_AUTH", "on")
        monkeypatch.setenv("MHERO_AUTH_ISSUER", "http://127.0.0.1:1")
        monkeypatch.setenv("MHERO_AUTH_CLIENT_ID", "cid")
        monkeypatch.setenv("MHERO_AUTH_CLIENT_SECRET", "x")
        monkeypatch.setenv("MHERO_AUTH_BASE_URL", "http://hub.test")
        monkeypatch.setenv("MHERO_AUTH_SESSION_SECRET", "s" * 40)
        monkeypatch.setenv("MHERO_AUTH_ORG", "mhero")
    else:
        monkeypatch.setenv("MHERO_AUTH", "off")
    spec = importlib.util.spec_from_file_location(f"hub_feedback_{auth}_{time.time_ns()}", APP)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module._port_open = lambda *a, **k: True
    module.app.config["TESTING"] = True
    return module


def wsgi_iter(module, path="/", cookie=""):
    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "SERVER_NAME": "hub.test",
        "SERVER_PORT": "80",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "http",
        "wsgi.input": io.BytesIO(),
        "wsgi.errors": io.StringIO(),
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
        "HTTP_HOST": "hub.test",
    }
    if cookie:
        environ["HTTP_COOKIE"] = cookie

    def start_response(status, headers, exc_info=None):
        return None

    return module.app.wsgi_app(environ, start_response)


def test_index_spins_before_probe_and_keeps_cards(monkeypatch):
    module = load_app(monkeypatch)
    calls = []
    real = module.probe_services

    def wrapped():
        calls.append("probe")
        return real()

    module.probe_services = wrapped
    iterator = wsgi_iter(module)
    first = next(iterator)
    assert b"ant-page-spin" in first
    assert "正在加载服务状态".encode() in first
    assert b'data-id="nss"' not in first
    assert calls == []
    rest = b"".join(iterator)
    body = first + rest
    assert calls == ["probe"]
    assert "NSS 问卷提醒" in body.decode()
    assert "事故车提醒" in body.decode()
    assert b'id="hub-refresh"' in body
    assert "服务状态刷新失败，请稍后重试".encode() in body
    assert "服务状态已更新".encode() in body
    assert b"data-ant-upload" in body or b"ant-progress-bg" in body
    assert b"ant-message" in body


def test_account_page_has_password_submit_and_spin(monkeypatch):
    module = load_app(monkeypatch, auth="on")
    token = module._auth._sign({
        "app": "hub", "sub": "alice", "name": "alice", "dn": "爱丽丝", "em": "",
        "role": "admin", "exp": time.time() + 3600, "rv": time.time() + 3600,
        "ap": ["hub"], "ga": True, "iat": time.time(),
    })
    client = module.app.test_client()
    client.set_cookie("mh_hub", token, domain="hub.test")
    page = client.get("/account", base_url="http://hub.test")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "正在加载账号设置" in html
    assert 'id="pw-go"' in html
    assert "修改密码" in html
    assert "两次输入的新密码不一致" in html
    assert 'action="/account/password"' in html

    anon = module.app.test_client().get("/account", base_url="http://hub.test")
    assert anon.status_code == 302


def test_accounts_stream_snapshot_after_shell(monkeypatch):
    module = load_app(monkeypatch, auth="on")
    events = []

    class Svc:
        def snapshot(self):
            events.append("snapshot")
            return [{
                "name": "alice", "display": "爱丽丝", "level": "admin", "apps": [],
                "disabled": False, "need_update_password": False,
            }], []

        def recent_audit(self, n):
            events.append("audit")
            return []

    module.app.config["ACCOUNT_SERVICE"] = Svc()
    token = module._auth._sign({
        "app": "hub", "sub": "alice", "name": "alice", "dn": "爱丽丝", "em": "",
        "role": "admin", "exp": time.time() + 3600, "rv": time.time() + 3600,
        "ap": ["hub"], "ga": True, "iat": time.time(),
    })
    iterator = wsgi_iter(module, "/admin/accounts", cookie="mh_hub=" + token)
    first = next(iterator)
    assert "正在加载账号".encode() in first
    assert b'id="acct-table"' not in first
    assert events == []
    rest = b"".join(iterator)
    body = (first + rest).decode()
    assert events == ["snapshot", "audit"]
    assert 'id="acct-table"' in body
    assert "创建（下一步确认）" in body
    assert "操作已完成" in body
    assert "alice" in body


def test_accounts_unconfigured_copy(monkeypatch):
    module = load_app(monkeypatch, auth="on")
    module.app.config["ACCOUNT_SERVICE"] = None
    monkeypatch.delenv("MHERO_ADMIN_CRED_FILE", raising=False)
    token = module._auth._sign({
        "app": "hub", "sub": "alice", "name": "alice", "dn": "爱丽丝", "em": "",
        "role": "admin", "exp": time.time() + 3600, "rv": time.time() + 3600,
        "ap": ["hub"], "ga": True, "iat": time.time(),
    })
    client = module.app.test_client()
    client.set_cookie("mh_hub", token, domain="hub.test")
    page = client.get("/admin/accounts", base_url="http://hub.test")
    assert page.status_code == 200
    assert "账号服务未配置" in page.get_data(as_text=True)
    warned = client.get("/admin/accounts?err=请重新操作", base_url="http://hub.test")
    assert "请重新操作" in warned.get_data(as_text=True)
