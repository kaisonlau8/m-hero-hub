# 猛士服务运营 · 控制台黄页

汇总各功能控制台入口，探活本地端口；可选经 Cloudflare Tunnel 对外提供导航页。

> 工具集总览、文档地图与依赖关系：[m-hero](https://github.com/kaisonlau8/m-hero)

## 入口

| 项 | 值 |
|----|-----|
| 本地 | `http://127.0.0.1:9004` |
| Tunnel | `m-hero-hub` → `:9004`（hostname 仅写本机 cloudflared 配置） |

## 收录控制台（默认本地）

| 名称 | 本地 |
|------|------|
| 事故车提醒 | `:9000` |
| VIP 保养提醒 | `:9002` |
| 区域报表自动化 | `:9003` |
| 超时机器人统计 | `:5001` |
| NSS 问卷提醒 | `:9005` |
| 售后网点地图 | 无本地端口，默认 [https://storelocation-m-hero.41box.com](https://storelocation-m-hero.41box.com) |

助手 APP 安装看板已于 2026-09-30 下线（原 `:9006`），黄页不再收录。

门店管理（原 `:9014`）与一客一档（原 `:9011`）已于 2026-10-19 下线封存，黄页不再收录。

对外跳转 URL 写在**未入库**的 `config/services.local.json`（模板见 `config/services.local.json.example`）。未配置时黄页按钮指向上述本地地址。

售后网点地图是静态站点，本身不做 Casdoor 鉴权。黄页登录后所有账号都能看到这张卡片，不按「可访问系统」勾选过滤。在线状态探测的是实际打开的公网地址（默认 `https://storelocation-m-hero.41box.com`，可用 `store_map` 覆盖），不探测本机端口。

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config/services.local.json.example config/services.local.json   # 按需填写
./run.sh
```

## 部署

- launchd：`com.m-hero-hub.web`
- cloudflared：`com.cloudflare.cloudflared.m-hero-hub`
- 配置示例：`deploy/config-m-hero-hub.yml.example`（hostname 为占位符）

本服务无业务数据存储；仅聚合链接与端口探活。
