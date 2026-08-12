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
| 门店超时审计 | `:3001` |
| 超时机器人统计 | `:5001` |

对外跳转 URL 写在**未入库**的 `config/services.local.json`（模板见 `config/services.local.json.example`）。未配置时黄页按钮指向上述本地地址。

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
