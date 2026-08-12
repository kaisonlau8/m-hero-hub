# 猛士服务运营 · 控制台黄页

汇总各功能控制台入口，探活本地端口，经 Cloudflare Tunnel 对外提供导航页。

> 工具集总览、文档地图与依赖关系：[m-hero](https://github.com/kaisonlau8/m-hero)

## 入口

| 项 | 值 |
|----|-----|
| 本地 | `http://127.0.0.1:9004` |
| 公网 | http://127.0.0.1:9004 |
| Tunnel | `m-hero-hub` → `:9004` |

## 收录控制台

| 名称 | 公网 | 本地 |
|------|------|------|
| 事故车提醒 | http://127.0.0.1:9000 | `:9000` |
| VIP 保养提醒 | http://127.0.0.1:9002 | `:9002` |
| 区域报表自动化 | http://127.0.0.1:9003 | `:9003` |
| 门店超时审计 | http://127.0.0.1:3001 | `:3001` |
| 超时机器人统计 | http://127.0.0.1:5001 | `:5001` |

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run.sh
# 或: python app.py
```

## 部署

- launchd：`com.m-hero-hub.web`
- cloudflared：`com.cloudflare.cloudflared.m-hero-hub`
- 配置示例：`deploy/config-m-hero-hub.yml.example`

本服务无业务数据存储；仅聚合链接与端口探活。
