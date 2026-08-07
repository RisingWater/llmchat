"""微信通知：视频生成完成后通过 NAS 微信网关发送消息（无鉴权，仅限内网）"""
import json

import requests

from backend.config import WECHAT_SEND_URL, WECHAT_WHO, WECHAT_WXNAME


def is_enabled() -> bool:
    """WECHAT_WHO 为空或网关地址为空时不发送"""
    return bool(WECHAT_SEND_URL and WECHAT_WHO)


def send_wechat(msg: str) -> bool:
    """发送文本消息到微信。成功返回 True，失败/未启用返回 False（不抛出异常）"""
    if not is_enabled():
        return False
    try:
        resp = requests.post(
            f"{WECHAT_SEND_URL.rstrip('/')}/api/wechat/send-text",
            json={"who": WECHAT_WHO, "msg": msg, "wxname": WECHAT_WXNAME},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            ok = data.get("code") == 200
            if not ok:
                print(f"[WECHAT] 接口返回失败: {data}", flush=True)
            return ok
        print(f"[WECHAT] 接口状态码异常: {resp.status_code} {resp.text[:200]}", flush=True)
        return False
    except Exception as e:
        print(f"[WECHAT] 发送失败: {e}", flush=True)
        return False


def notify_video_done(prompt: str, title: str = "") -> bool:
    """视频完成通知"""
    snippet = (prompt or "").strip().replace("\n", " ")
    if len(snippet) > 30:
        snippet = snippet[:30] + "..."
    head = f"「{title}」" if title else ""
    msg = f"🎬 视频已生成完成{head}\n提示词：{snippet or '（无）'}"
    return send_wechat(msg)