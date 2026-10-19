#!/usr/bin/env python3
"""猛士服务运营控制台黄页。"""

from __future__ import annotations

import argparse
import json
import os
import socket
import urllib.parse
import urllib.request
from pathlib import Path

from flask import Flask, Response, g, jsonify, redirect, render_template, request, send_from_directory, stream_with_context

ROOT = Path(__file__).resolve().parent
app = Flask(__name__, template_folder=str(ROOT / "templates"))

# --- 设计系统（antd-lite.css / sprite.svg，design-system/sync.sh 同步到 ds/）---
_ds_cache: dict[str, str] = {}


def _ds(name: str) -> str:
    if name not in _ds_cache:
        _ds_cache[name] = (ROOT / "ds" / name).read_text(encoding="utf-8")
    return _ds_cache[name]


app.jinja_env.globals["ds_css"] = lambda: _ds("antd-lite.css")
app.jinja_env.globals["ds_sprite"] = lambda: _ds("sprite.svg")
app.jinja_env.globals["ds_cards"] = lambda: _ds("cards.js")
# hub 自有的 Ant Design 反馈层（不在 design-system 同步清单里）
app.jinja_env.globals["ds_feedback_css"] = lambda: _ds("feedback.css")
app.jinja_env.globals["ds_feedback_js"] = lambda: _ds("feedback.js")


# --- 品牌静态资源（logo / favicon，design-system/sync.sh 同步到 ds/brand/）---
@app.get("/ds/brand/<path:name>")
def ds_brand(name: str):
    return send_from_directory(str(ROOT / "ds" / "brand"), name)


@app.get("/favicon.ico")
def favicon_ico():
    """Browsers probe /favicon.ico even when the HTML link points at /ds/brand/... .
    Must stay public so it never triggers /_auth/login (that overwrites the OAuth state cookie)."""
    return send_from_directory(str(ROOT / "ds" / "brand"), "favicon.ico")


# --- m-hero SSO (Casdoor): inert unless MHERO_AUTH[_HUB]=audit|on is set (see docs/SSO_CASDOOR.md) ---
from mhero_auth.flask_adapter import init_app as _mhero_auth_init
_auth = _mhero_auth_init(app, "hub", default_mode="off", public_get_paths=["/healthz", "/ds/brand/*", "/favicon.ico"], admin_paths=["/admin/*"], supervisor_write_paths=["/account/password"], userbar=True, userbar_account_url="/account", userbar_accounts_url="/admin/accounts")   # top-right user bar: 账号设置 + 退出登录

# 默认只写本地入口；公网 URL 放在未入库的 config/services.local.json
_SERVICE_DEFS = [
    {
        "id": "accident",
        "icon": "car",
        "name": "事故车提醒",
        "desc": "DMS 事故维修工单爬取、门店/区域报表与飞书告警",
        "local": "http://127.0.0.1:9000",
        "port": 9000,
        "accent": "orange",
    },
    {
        "id": "vip",
        "icon": "safety",
        "name": "VIP 保养提醒",
        "desc": "保养提醒任务匹配 VIP 清单，飞书卡片通知提醒人",
        "local": "http://127.0.0.1:9002",
        "port": 9002,
        "accent": "blue",
    },
    {
        "id": "district",
        "icon": "cloud-download",
        "name": "DMS 爬取控制台",
        "desc": "爬取 7 份 DMS 源表、生成区域日报并推送飞书群，管理爬取任务与 DMS 会话",
        "local": "http://127.0.0.1:9003",
        "port": 9003,
        "accent": "green",
    },
    {
        "id": "report",
        "icon": "bar-chart",
        "name": "区域报表",
        "desc": "全国与各区域指标总览、分表明细、督导豁免申请与审批、日报导出",
        "local": "http://127.0.0.1:9013",
        "port": 9013,
        "accent": "green",
    },
    {
        "id": "cleaner",
        "icon": "robot",
        "name": "超时机器人统计",
        "desc": "从企微 SCRM 同步客户群，统计已拉超时提醒机器人与超时触发趋势",
        "local": "http://127.0.0.1:5001",
        "port": 5001,
        "accent": "red",
    },
    {
        "id": "nss",
        "icon": "form",
        "name": "NSS 问卷提醒",
        "desc": "交付 90 天后当天 09:00 私聊门店服务经理和对应督导",
        "local": "http://127.0.0.1:9005",
        "port": 9005,
        "accent": "blue",
    },
    # 2026-10-19：门店管理（stores, :9014）与一客一档（ykyd, :9011）已下线封存，入口移除
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


def _visible_ids() -> set[str] | None:
    """Which system cards the current account may see. None = all (auth off, or MHERO_AUTH_REQUIRE_APP not enabled).
    Hub only hides cards; each app still enforces 403 itself."""
    if not _auth.cfg.require_app or _auth.effective_mode() != "on":
        return None
    s = getattr(g, "mhero_session", None)
    if s is None or s.via != "session":
        return None if s is not None else set()
    if s.ga:
        return None
    return set(s.apps)


def probe_services() -> list[dict]:
    rows = []
    vis = _visible_ids()
    for svc in _services():
        if vis is not None and svc["id"] not in vis:
            continue
        local_up = _port_open(int(svc["port"]))
        if svc.get("health"):
            # 服务提供专用健康检查（svc["health"]）时以它为准，
            # 端口监听但依赖异常时仍应显示离线。
            healthy = _http_ok(svc["local"] + svc["health"])
        else:
            healthy = local_up or _http_ok(svc["local"] + "/")
        rows.append({**svc, "online": bool(healthy), "local_up": bool(local_up)})
    return rows


_STREAM = "<!--HUB_STREAM-->"


def _streamed_page(template: str, producer, status: int = 200, headers: dict | None = None, **ctx):
    """先吐出壳子（含全屏 Spin），再跑 producer() 把慢内容插在 <!--HUB_STREAM--> 处。

    direct_passthrough 避免 after_request 把整页缓冲完再下发，浏览器才能在探活 / 拉账号期间看到 Spin。
    """

    def _b(part: str) -> bytes:
        return part.encode("utf-8")

    @stream_with_context
    def generate():
        html = render_template(template, **ctx)
        if _STREAM not in html:
            yield _b(html)
            return
        pre, post = html.split(_STREAM, 1)
        yield _b(pre)
        try:
            extra = producer() or ""
        except Exception:
            app.logger.exception("stream producer failed")
            extra = (
                '<div class="ant-alert ant-alert-error" id="flash-err">'
                '<span class="ant-alert-icon"><svg class="ai" aria-hidden="true"><use href="#i-close-circle"/></svg></span>'
                '<div class="ant-alert-content">页面加载失败，请稍后重试</div></div>'
            )
        yield _b(extra)
        yield _b(post)

    resp = Response(generate(), status=status, mimetype="text/html")
    resp.direct_passthrough = True
    resp.headers["X-Accel-Buffering"] = "no"
    for key, value in (headers or {}).items():
        resp.headers[key] = value
    return resp


@app.get("/")
def index():
    def producer():
        try:
            return render_template("index_cards.html", services=probe_services())
        except Exception:
            app.logger.exception("probe services failed")
            return render_template("index_cards.html", services=[], load_err=True)

    return _streamed_page("index.html", producer)


# ---------------------------------------------------------------- 账号管理（仅管理员；经 Casdoor 管理 API，凭据只在服务端）
_ACTIONS = {"create": "新建账号", "reset_password": "重置密码（管理员设定新密码）", "set_level": "修改身份", "set_apps": "修改可访问系统", "set_disabled": "停用 / 启用账号"}
_account_svc = None


def get_account_service():
    global _account_svc
    if app.config.get("ACCOUNT_SERVICE") is not None:
        return app.config["ACCOUNT_SERVICE"]
    if _account_svc is None:
        from mhero_auth.accounts import AccountService
        from mhero_auth.casdoor_admin import CasdoorAdmin
        client = CasdoorAdmin.from_env()
        if client is None:
            return None
        import hashlib
        sec = hashlib.sha256(("hub-accounts|" + os.getenv("MHERO_AUTH_HUB_SESSION_SECRET", os.getenv("MHERO_AUTH_SESSION_SECRET", ""))).encode()).hexdigest()
        _account_svc = AccountService(client, audit_path=os.getenv("MHERO_ACCOUNTS_AUDIT_LOG", str(ROOT / "accounts-audit.log")),
                                      revoke_path=os.getenv("MHERO_AUTH_REVOKE_FILE", ""), secret=sec)
    return _account_svc


def _admin_actor():
    """Account pages need a REAL logged-in global admin (never the auth-off / token / loopback bypass)."""
    s = getattr(g, "mhero_session", None)
    if s is None or s.via != "session" or s.role != "admin" or not s.ga:
        return None
    return s


def _acct_render(msg="", err="", status=200, **extra):
    from mhero_auth.accounts import LEVELS
    from mhero_auth.core import APP_IDS, APP_LABEL
    svc = get_account_service()
    ctx = dict(configured=svc is not None, rows=[], audit=[], msg=msg, err=err, late_err="", levels=LEVELS, app_ids=APP_IDS, app_label=APP_LABEL,
               actor=_admin_actor().name, require_app=_auth.cfg.require_app, confirm=None)
    ctx.update(extra)

    def producer():
        if svc is not None:
            try:
                ctx["rows"], ctx["audit"] = svc.snapshot(), svc.recent_audit(30)
            except Exception as exc:                       # Casdoor down etc: show, do not 500
                if not ctx["err"]:
                    ctx["late_err"] = f"读取账号失败：{exc}"
        return render_template("accounts_data.html", **ctx)

    return _streamed_page("accounts.html", producer, status=status, headers={"Cache-Control": "no-store"}, **ctx)


@app.get("/admin/accounts")
def accounts_page():
    if not _admin_actor():
        return Response("403 需要以管理员身份登录", 403, mimetype="text/plain; charset=utf-8")
    return _acct_render(msg=request.args.get("msg", ""), err=request.args.get("err", ""))


def _form_params() -> tuple[str, dict]:
    f = request.form
    action = f.get("action", "")
    p = {"name": (f.get("name") or "").strip().lower(), "display": (f.get("display") or "").strip(), "password": f.get("password", ""),
         "level": f.get("level", ""), "apps": sorted(f.getlist("apps")), "disabled": f.get("disabled", "")}
    return action, p


@app.post("/admin/accounts/prepare")
def accounts_prepare():
    actor = _admin_actor()
    if not actor:
        return Response("403 需要以管理员身份登录", 403, mimetype="text/plain; charset=utf-8")
    svc = get_account_service()
    action, p = _form_params()
    if svc is None or action not in _ACTIONS or not p["name"]:
        return _acct_render(err="请求无效或账号服务未配置", status=400)
    from mhero_auth.accounts import AccountError, check_password
    try:
        if action in ("create", "reset_password"):
            check_password(p["name"], p["password"])
    except AccountError as exc:
        return _acct_render(err=str(exc), status=400)
    token = svc.make_token(actor.name, action, p)
    summary = {"create": f"新建账号 {p['name']}（{p['display'] or p['name']}），身份 {p['level']}，系统：{', '.join(p['apps']) or '无'}。初始密码由你设定，首次登录强制改密。",
               "reset_password": f"为 {p['name']} 设定新密码；对方旧登录立即作废，下次登录必须改密。",
               "set_level": f"把 {p['name']} 的身份改为 {p['level']}；对方需要重新登录。",
               "set_apps": f"把 {p['name']} 可访问的系统改为：{', '.join(p['apps']) or '无'}；对方需要重新登录。",
               "set_disabled": f"{'停用' if p['disabled'] == '1' else '启用'}账号 {p['name']}；{'对方登录立即作废。' if p['disabled'] == '1' else ''}"}[action]
    return _acct_render(confirm={"action": action, "title": _ACTIONS[action], "summary": summary, "params": p, "token": token})


@app.post("/admin/accounts/execute")
def accounts_execute():
    actor = _admin_actor()
    if not actor:
        return Response("403 需要以管理员身份登录", 403, mimetype="text/plain; charset=utf-8")
    svc = get_account_service()
    action, p = _form_params()
    if svc is None or action not in _ACTIONS or not svc.check_token(request.form.get("token", ""), actor.name, action, p):
        if svc is not None:
            svc.audit(actor.name, action or "?", p["name"], "DENIED: 确认已过期或被篡改", ok=False)
        return _acct_render(err="确认已过期或内容被改动，请重新操作", status=400)
    from mhero_auth.accounts import AccountError
    from mhero_auth.casdoor_admin import CasdoorError
    try:
        if action == "create":
            svc.create(actor.name, p["name"], p["display"], p["password"], p["level"], p["apps"])
        elif action == "reset_password":
            svc.reset_password(actor.name, p["name"], p["password"])
        elif action == "set_level":
            svc.set_level(actor.name, p["name"], p["level"])
        elif action == "set_apps":
            svc.set_apps(actor.name, p["name"], p["apps"])
        else:
            svc.set_disabled(actor.name, p["name"], p["disabled"] == "1")
    except AccountError as exc:
        return _acct_render(err=str(exc), status=exc.status if exc.status != 404 else 400)
    except CasdoorError as exc:
        svc.audit(actor.name, action, p["name"], f"FAILED: {exc}", ok=False)
        return _acct_render(err=f"Casdoor 操作失败：{exc}", status=502)
    return redirect("/admin/accounts?msg=" + urllib.parse.quote(f"已完成：{_ACTIONS[action]} {p['name']}"))


def _self_session():
    s = getattr(g, "mhero_session", None)
    if s is None or s.via != "session":
        return None
    return s


def _account_render(msg="", err="", status=200):
    s = _self_session()
    resp = Response(render_template("account.html", display=s.display or s.name, name=s.name, msg=msg, err=err), status=status, mimetype="text/html")
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.get("/account")
def account_page():
    if not _self_session():
        return Response("403 请先登录", 403, mimetype="text/plain; charset=utf-8")
    return _account_render(msg=request.args.get("msg", ""))


def _verify_password(name: str, pw: str) -> bool:
    """Check the current password against Casdoor (same call the login page makes; issues a throwaway code, nothing is stored)."""
    cfg = _auth.cfg
    q = urllib.parse.urlencode({"clientId": cfg.client_id, "responseType": "code", "redirectUri": cfg.base_url + "/_auth/callback",
                                "scope": "openid", "state": "pwcheck", "nonce": "pwcheck"})
    body = json.dumps({"application": "mhero-sso", "organization": cfg.org, "username": name, "password": pw, "type": "code"}).encode()
    req = urllib.request.Request(_auth._issuer_back() + "/api/login?" + q, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode()).get("status") == "ok"
    except Exception:
        return False


@app.post("/account/password")
def account_password():
    s = _self_session()
    if not s:
        return Response("403 请先登录", 403, mimetype="text/plain; charset=utf-8")
    old, new, new2 = request.form.get("old", ""), request.form.get("new", ""), request.form.get("new2", "")
    if new != new2:
        return _account_render(err="两次输入的新密码不一致", status=400)
    if new == old:
        return _account_render(err="新密码不能与当前密码相同", status=400)
    from mhero_auth.accounts import AccountError, check_password
    try:
        check_password(s.name, new)
    except AccountError as exc:
        return _account_render(err=str(exc), status=400)
    svc = get_account_service()
    if svc is None:
        return _account_render(err="账号服务未配置，暂时无法修改密码，请联系管理员", status=503)
    if not _verify_password(s.name, old):
        svc.audit(s.name, "self_password", s.name, "FAILED: wrong current password", ok=False)
        return _account_render(err="当前密码不正确", status=400)
    try:
        svc.c.set_password(s.name, new, need_update_password=False)
    except Exception as exc:
        svc.audit(s.name, "self_password", s.name, f"FAILED: {exc}", ok=False)
        return _account_render(err="修改失败：" + str(exc)[:120], status=502)
    svc.audit(s.name, "self_password", s.name, "")
    return redirect("/account?msg=" + urllib.parse.quote("密码已修改，下次登录请使用新密码"))


@app.get("/healthz")
def healthz():
    return "ok"


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
