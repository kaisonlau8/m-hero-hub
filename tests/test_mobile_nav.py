"""移动端顶栏：账号入口由设计系统统一汉堡抽屉（antd-lite 4.7 + cards.js）承载。"""
import importlib.util
import time
from pathlib import Path

_helper_path = Path(__file__).with_name("test_feedback_ui.py")
_spec = importlib.util.spec_from_file_location("hub_feedback_helper", _helper_path)
_helper = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_helper)
load_app = _helper.load_app


def _sign(module, role="admin", ga=True, name="alice", display="爱丽丝"):
    return module._auth._sign({
        "app": "hub", "sub": name, "name": name, "dn": display, "em": "",
        "role": role, "exp": time.time() + 3600, "rv": time.time() + 3600,
        "ap": ["hub"], "ga": ga, "iat": time.time(),
    })


def _account_html(module, token):
    client = module.app.test_client()
    client.set_cookie("mh_hub", token, domain="hub.test")
    page = client.get("/account", base_url="http://hub.test")
    assert page.status_code == 200
    return page.get_data(as_text=True)


def test_admin_drawer_reaches_account_admin_logout(monkeypatch):
    module = load_app(monkeypatch, auth="on")
    html = _account_html(module, _sign(module))
    # 顶栏只有 .hub-user 一个账号按钮，不再有第二套自定义汉堡/抽屉
    assert '<div class="hub-user" data-mhero-userbar="1">' in html
    assert 'id="hub-burger"' not in html
    assert 'id="hub-drawer"' not in html
    assert "disarmAutoBurger" not in html
    assert '<header class="ant-header" data-no-auto-burger' not in html
    assert html.count('class="hub-user"') == 1
    # 账号入口（桌面下拉即移动抽屉内容，同一份 DOM）
    assert 'id="mhero-account-link" href="/account"' in html
    assert 'id="accounts-link" href="/admin/accounts"' in html
    assert 'id="mhero-logout-link" href="/_auth/logout"' in html
    assert "账号设置" in html
    assert "账号管理" in html
    assert "退出登录" in html
    # 设计系统内联注入：统一断点 860px、右滑抽屉、进出场过渡（页面不再自带旧断点）
    assert "@media (max-width: 860px)" in html
    assert ".hub-user.open .dd" in html
    assert "translateX(100%)" in html
    assert "cubic-bezier(.23, 1, .32, 1)" in html
    assert "rgba(0, 0, 0, .45)" in html
    assert "min(300px, 82vw)" in html
    assert "prefers-reduced-motion: reduce" in html
    assert "body:has(.hub-user.open) { overflow: hidden; }" in html
    # cards.js 负责开合 aria / Escape / 遮罩关闭，中文文案在设计系统里
    assert "打开菜单" in html
    assert "关闭菜单" in html
    assert "hub-drawer-who" in html  # 抽屉首行的姓名+角色由 cards.js 注入
    assert "hub-drawer {" not in html  # 页面不再自带旧抽屉样式
    assert "hub-burger" not in html


def test_supervisor_dropdown_hides_admin_link(monkeypatch):
    module = load_app(monkeypatch, auth="on")
    html = _account_html(module, _sign(module, role="supervisor", ga=False, name="bob", display="鲍勃"))
    assert 'id="mhero-account-link" href="/account"' in html
    assert 'id="mhero-logout-link" href="/_auth/logout"' in html
    assert "账号设置" in html
    assert "退出登录" in html
    assert 'id="accounts-link"' not in html
    assert "账号管理" not in html


def test_anonymous_page_has_no_hamburger(monkeypatch):
    module = load_app(monkeypatch, auth="off")
    client = module.app.test_client()
    page = client.get("/", base_url="http://hub.test")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert 'class="hub-user"' not in html
    assert 'data-mhero-userbar' not in html
    assert 'id="hub-burger"' not in html
    assert 'id="hub-drawer"' not in html
