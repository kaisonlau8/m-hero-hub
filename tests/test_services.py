"""黄页服务登记：门店管理 / 一客一档已下线封存（2026-10-19），专用 /healthz 探活机制保留。"""
import importlib.util
import json
import time
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


STORE_MAP_URL = "https://storelocation-m-hero.41box.com"


def _limited_session(module, apps):
    return module._auth._sign({
        "app": "hub", "sub": "bob", "name": "bob", "dn": "鲍勃", "em": "",
        "role": "user", "exp": time.time() + 3600, "rv": time.time() + 3600,
        "ap": list(apps), "ga": False, "gr": False, "iat": time.time(),
    })


def test_store_map_card_defaults_to_public_site(monkeypatch):
    module = load_app(monkeypatch)
    svc = next(s for s in module._SERVICE_DEFS if s["id"] == "store_map")
    assert svc["name"] == "售后网点地图"
    assert "一网" in svc["desc"] and "二网" in svc["desc"]
    assert svc.get("always_visible") is True
    assert not svc.get("port")
    assert svc["local"].rstrip("/") == STORE_MAP_URL
    sprite = (ROOT / "ds" / "sprite.svg").read_text(encoding="utf-8")
    assert f'id="i-{svc["icon"]}"' in sprite


def test_store_map_visible_to_logged_in_user_without_app_grant(monkeypatch):
    module = load_app(monkeypatch, auth="on")
    module._auth.cfg.require_app = True
    module._port_open = lambda *a, **k: False
    module._http_ok = lambda url, timeout=1.2: True
    client = module.app.test_client()
    client.set_cookie("mh_hub", _limited_session(module, ["nss"]), domain="hub.test")
    payload = client.get("/api/status", base_url="http://hub.test").get_json()
    ids = {s["id"] for s in payload["services"]}
    assert "store_map" in ids
    assert "nss" in ids
    assert "accident" not in ids


def test_store_map_visible_when_auth_off(monkeypatch):
    module = load_app(monkeypatch)
    module._port_open = lambda *a, **k: False
    module._http_ok = lambda url, timeout=1.2: False
    ids = {s["id"] for s in module.probe_services()}
    assert "store_map" in ids
    assert "nss" in ids


def test_store_map_health_probes_resolved_url_not_a_local_port(monkeypatch):
    module = load_app(monkeypatch)
    module._load_public_urls = lambda: {}
    ports = []
    urls = []
    module._port_open = lambda port, *a, **k: ports.append(port) or False
    module._http_ok = lambda url, timeout=1.2: urls.append(url) or True
    row = next(r for r in module.probe_services() if r["id"] == "store_map")
    assert row["online"] is True
    assert row["local_up"] is False
    assert row["url"].rstrip("/") == STORE_MAP_URL
    assert STORE_MAP_URL + "/" in urls
    assert ports == [s["port"] for s in module._SERVICE_DEFS if s.get("port")]

    module._load_public_urls = lambda: {"store_map": "https://maps.example.test"}
    urls.clear()
    module._http_ok = lambda url, timeout=1.2: urls.append(url) or False
    row = next(r for r in module.probe_services() if r["id"] == "store_map")
    assert row["url"] == "https://maps.example.test"
    assert row["online"] is False
    assert "https://maps.example.test/" in urls


def test_example_config_documents_store_map():
    data = json.loads((ROOT / "config" / "services.local.json.example").read_text(encoding="utf-8"))
    assert data["store_map"].rstrip("/") == STORE_MAP_URL
