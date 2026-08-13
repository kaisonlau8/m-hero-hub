#!/usr/bin/env python3
"""猛士服务运营控制台黄页。"""

from __future__ import annotations

import argparse
import json
import os
import socket
import urllib.request
from pathlib import Path

from flask import Flask, jsonify, render_template

ROOT = Path(__file__).resolve().parent
app = Flask(__name__, template_folder=str(ROOT / "templates"))

# 默认只写本地入口；公网 URL 放在未入库的 config/services.local.json
_SERVICE_DEFS = [
    {
        "id": "accident",
        "name": "事故车提醒",
        "desc": "DMS 事故维修工单爬取、门店/区域报表与飞书告警",
        "local": "http://127.0.0.1:9000",
        "port": 9000,
        "accent": "orange",
    },
    {
        "id": "vip",
        "name": "VIP 保养提醒",
        "desc": "保养提醒任务匹配 VIP 清单，飞书卡片通知提醒人",
        "local": "http://127.0.0.1:9002",
        "port": 9002,
        "accent": "blue",
    },
    {
        "id": "district",
        "name": "区域报表自动化",
        "desc": "爬取 7 份 DMS 源表，生成区域各指标情况一览并推送飞书群",
        "local": "http://127.0.0.1:9003",
        "port": 9003,
        "accent": "green",
    },
    {
        "id": "cleaner",
        "name": "超时机器人统计",
        "desc": "从企微 SCRM 同步客户群，统计已拉超时提醒机器人与超时触发趋势",
        "local": "http://127.0.0.1:5001",
        "port": 5001,
        "accent": "red",
    },
]


def _load_public_urls() -> dict[str, str]:
    """Optional local overrides: { "accident": "https://…", … }."""
    path = ROOT / "config" / "services.local.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): str(v).rstrip("/") for k, v in data.items() if v}
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return {}


def _services() -> list[dict]:
    public = _load_public_urls()
    rows = []
    for svc in _SERVICE_DEFS:
        url = public.get(svc["id"]) or svc["local"]
        rows.append({**svc, "url": url})
    return rows


def _port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _http_ok(url: str, timeout: float = 1.2) -> bool:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= int(resp.status) < 500
    except Exception:
        return False


def probe_services() -> list[dict]:
    rows = []
    for svc in _services():
        local_up = _port_open(int(svc["port"]))
        healthy = local_up or _http_ok(svc["local"] + "/")
        rows.append({**svc, "online": bool(healthy), "local_up": bool(local_up)})
    return rows


@app.get("/")
def index():
    return render_template("index.html", services=probe_services())


@app.get("/api/status")
def api_status():
    return jsonify({"services": probe_services()})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.getenv("HUB_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("HUB_PORT", "9004")))
    args = parser.parse_args()
    print(f"猛士控制台黄页 http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
