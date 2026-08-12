#!/usr/bin/env python3
"""猛士服务运营控制台黄页。"""

from __future__ import annotations

import argparse
import os
import socket
import urllib.request
from pathlib import Path

from flask import Flask, jsonify, render_template

ROOT = Path(__file__).resolve().parent
app = Flask(__name__, template_folder=str(ROOT / "templates"))

# 黄页收录的控制台（公网入口 + 本地探活）
SERVICES = [
    {
        "id": "accident",
        "name": "事故车提醒",
        "desc": "DMS 事故维修工单爬取、门店/区域报表与飞书告警",
        "url": "http://127.0.0.1:9000",
        "local": "http://127.0.0.1:9000",
        "port": 9000,
        "accent": "orange",
    },
    {
        "id": "vip",
        "name": "VIP 保养提醒",
        "desc": "保养提醒任务匹配 VIP 清单，飞书卡片通知提醒人",
        "url": "http://127.0.0.1:9002",
        "local": "http://127.0.0.1:9002",
        "port": 9002,
        "accent": "blue",
    },
    {
        "id": "district",
        "name": "区域报表自动化",
        "desc": "爬取 7 份 DMS 源表，生成区域各指标情况一览并推送飞书群",
        "url": "http://127.0.0.1:9003",
        "local": "http://127.0.0.1:9003",
        "port": 9003,
        "accent": "green",
    },
    {
        "id": "audit",
        "name": "门店超时审计",
        "desc": "门店清单与超时提醒登记比对，督导私聊与进度看板",
        "url": "http://127.0.0.1:3001",
        "local": "http://127.0.0.1:3001",
        "port": 3001,
        "accent": "purple",
    },
    {
        "id": "cleaner",
        "name": "超时机器人统计",
        "desc": "门店超时提醒机器人拉群/建群数据解析与统计控制台",
        "url": "http://127.0.0.1:5001",
        "local": "http://127.0.0.1:5001",
        "port": 5001,
        "accent": "red",
    },
]


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
    for svc in SERVICES:
        local_up = _port_open(int(svc["port"]))
        # Prefer lightweight local probe; fall back to public URL only if needed.
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
