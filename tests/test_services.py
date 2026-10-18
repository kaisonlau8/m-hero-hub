"""黄页服务登记：门店管理入口与专用 /healthz 探活。"""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_helper_path = Path(__file__).with_name("test_feedback_ui.py")
_spec = importlib.util.spec_from_file_location("hub_feedback_helper_services", _helper_path)
_helper = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_helper)
load_app = _helper.load_app


def _stores(module):
    return next(s for s in module._SERVICE_DEFS if s["id"] == "stores")


def test_stores_entry_registered(monkeypatch):
    module = load_app(monkeypatch)
    stores = _stores(module)
    assert stores["icon"] == "shop"
    assert stores["name"] == "门店管理"
    assert stores["desc"] == "门店主数据：销售/售后门店关系、新增门店、退网结转"
    assert stores["local"] == "http://127.0.0.1:9014"
    assert stores["port"] == 9014
    assert stores["accent"] == "blue"
    assert stores["health"] == "/healthz"
    assert 'id="i-shop"' in module._ds("sprite.svg")


def test_stores_probe_uses_healthz(monkeypatch):
    module = load_app(monkeypatch)
    calls = []
    module._port_open = lambda *a, **k: True

    def fake_http(url, timeout=1.2):
        calls.append(url)
        return True

    module._http_ok = fake_http
    rows = module.probe_services()
    stores = next(r for r in rows if r["id"] == "stores")
    assert stores["online"] is True
    # 有专用健康检查时不因端口监听而短路，必须探 /healthz
    assert calls == ["http://127.0.0.1:9014/healthz"]


def test_api_status_keeps_legacy_probe_paths(monkeypatch):
    module = load_app(monkeypatch)
    calls = []
    module._port_open = lambda *a, **k: False
    module._http_ok = lambda url, timeout=1.2: calls.append(url) or True

    payload = module.app.test_client().get("/api/status").get_json()
    stores = next(s for s in payload["services"] if s["id"] == "stores")
    assert stores["online"] is True
    assert "http://127.0.0.1:9014/healthz" in calls
    assert "http://127.0.0.1:9000/" in calls
    assert all(url.endswith("/") for url in calls if ":9014" not in url)


def test_example_config_documents_stores_hostname():
    text = (ROOT / "config" / "services.local.json.example").read_text(encoding="utf-8")
    assert '"stores": "https://<your-hostname>"' in text
    assert json.loads(text)["stores"] == "https://<your-hostname>"
