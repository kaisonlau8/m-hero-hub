"""移动端顶栏：汉堡抽屉承载账号入口；桌面样式断点写在页面里。"""
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
    assert 'id="hub-burger"' in html
    assert '<header class="ant-header" data-no-auto-burger>' in html
    assert '.ant-header:has(#hub-burger) > .in > .burger' in html
    assert 'disarmAutoBurger' in html
    assert 'aria-controls="hub-drawer"' in html
    assert 'aria-label="打开导航菜单"' in html
    assert 'id="hub-drawer"' in html
    assert 'id="hub-drawer-account" href="/account"' in html
    assert 'id="hub-drawer-accounts" href="/admin/accounts"' in html
    assert 'id="hub-drawer-logout" href="/_auth/logout"' in html
    assert "账号设置" in html
    assert "账号管理" in html
    assert "退出登录" in html
    assert "关闭导航菜单" in html
    # 桌面下拉仍在，避免桌面入口被挪走
    assert 'id="mhero-account-link" href="/account"' in html
    assert 'id="accounts-link" href="/admin/accounts"' in html
    assert 'id="mhero-logout-link" href="/_auth/logout"' in html
    # 断点与进出场动画（CSS transition，关闭时 visibility 延迟等于动画时长）
    assert "@media (max-width: 768px)" in html
    assert "@media (min-width: 769px)" in html
    assert "translateX(100%)" in html
    assert "cubic-bezier(0.23, 1, 0.32, 1)" in html
    assert "transition: visibility 0s linear .3s" in html
    assert "prefers-reduced-motion: reduce" in html


def test_supervisor_drawer_hides_admin_link(monkeypatch):
    module = load_app(monkeypatch, auth="on")
    html = _account_html(module, _sign(module, role="supervisor", ga=False, name="bob", display="鲍勃"))
    assert 'id="hub-drawer-account" href="/account"' in html
    assert 'id="hub-drawer-logout" href="/_auth/logout"' in html
    assert "账号设置" in html
    assert "退出登录" in html
    assert "hub-drawer-accounts" not in html
    assert "账号管理" not in html
    assert 'id="accounts-link"' not in html


def test_anonymous_page_has_no_hamburger(monkeypatch):
    module = load_app(monkeypatch, auth="off")
    client = module.app.test_client()
    page = client.get("/", base_url="http://hub.test")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert 'id="hub-burger"' not in html
    assert 'id="hub-drawer"' not in html
    assert '<header class="ant-header" data-no-auto-burger>' not in html
