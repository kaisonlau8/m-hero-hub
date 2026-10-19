"""黄页服务登记：门店管理 / 一客一档已下线封存（2026-10-19），专用 /healthz 探活机制保留。"""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_helper_path = Path(__file__).with_name("test_feedback_ui.py")
_spec = importlib.util.spec_from_file_location("hub_feedback_helper_services", _helper_path)
_helper = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_helper)
load_app = _helper.load_app


def test_archived_entries_removed(monkeypatch):
    module = load_app(monkeypatch)
    ids = {s["id"] for s in module._SERVICE_DEFS}
    assert "stores" not in ids
    assert "ykyd" not in ids
    names = {s["name"] for s in module._SERVICE_DEFS}
    assert "门店管理" not in names and "一客一档" not in names
    rows = module.probe_services()
    assert all(r["id"] not in ("stores", "ykyd") for r in rows)


def test_health_probe_still_supported(monkeypatch):
    module = load_app(monkeypatch)
    calls = []
    module._port_open = lambda *a, **k: True
    module._http_ok = lambda url, timeout=1.2: calls.append(url) or True
    module._SERVICE_DEFS = module._SERVICE_DEFS + [{"id": "x", "icon": "shop", "name": "x", "desc": "", "local": "http://127.0.0.1:9999", "port": 9999, "accent": "blue", "health": "/healthz"}]
    row = next(r for r in module.probe_services() if r["id"] == "x")
    assert row["online"] is True
    assert "http://127.0.0.1:9999/healthz" in calls
    assert "http://127.0.0.1:9999/" not in calls


def test_api_status_legacy_probe_paths(monkeypatch):
    module = load_app(monkeypatch)
    calls = []
    module._port_open = lambda *a, **k: False
    module._http_ok = lambda url, timeout=1.2: calls.append(url) or True
    payload = module.app.test_client().get("/api/status").get_json()
    assert all(s["id"] not in ("stores", "ykyd") for s in payload["services"])
    assert "http://127.0.0.1:9000/" in calls
    assert not any(":9014" in u or ":9011" in u for u in calls)


def test_example_config_has_no_archived_hosts():
    data = json.loads((ROOT / "config" / "services.local.json.example").read_text(encoding="utf-8"))
    assert "stores" not in data and "ykyd" not in data
