"""
ComfyUI 视频生成器（MiniMax H3 图生视频）— 输入 prompt + base64 首帧图，输出本地视频路径。

用法:
    from comfyui_video_gen import ComfyUIVideoGenerator

    gen = ComfyUIVideoGenerator(
        workflow="minimax_h3_i2v_workflow.json",
        base_url="http://127.0.0.1:8188",
    )
    path = gen.generate("a cat jumping", image_b64)
    print(path)  # → D:/wangxu/ai/llmchat/output/0001.mp4
"""

from __future__ import annotations

import base64
import json
import time
import uuid
from pathlib import Path
from typing import Optional

import requests


class ComfyUIVideoGenerator:
    """封装 ComfyUI API，输入 prompt + 首帧图（base64）→ 输出视频路径"""

    def __init__(
        self,
        workflow: str = "minimax_h3_i2v_workflow.json",
        base_url: str = "http://127.0.0.1:8188",
        output_dir: str = "output",
        timeout: int = 5400,
        poll_interval: float = 2.0,
        delete_base: Optional[str] = None,
    ):
        """
        workflow      — 工作流 JSON 文件路径
        base_url      — ComfyUI 地址
        output_dir    — 输出视频保存目录
        timeout       — 最大等待秒数（视频生成较慢，默认 1.5 小时）
        poll_interval — 轮询间隔（秒）
        delete_base   — 视频文件删除服务地址（None=下载后不删除远端文件）
        """
        self.base_url = base_url.rstrip("/")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.delete_base = delete_base.rstrip("/") if delete_base else None

        # 加载工作流
        wf_path = Path(workflow)
        if not wf_path.exists():
            raise FileNotFoundError(f"工作流文件不存在: {workflow}")
        self.workflow = self._load_json(wf_path)
        self._client_id = str(uuid.uuid4())
        self._counter = 0  # 生成计数，用于文件名

        # 探测关键节点
        self._prompt_node = self._find_first("MiniMaxH3ImageToVideo")
        self._image_node = self._find_first("ETN_LoadImageBase64")
        self._seed_node = self._find_first("RandomNoise")
        self._resolution_node = self._find_first("ResolutionSelector")
        self._scheduler_node = self._find_first("BasicScheduler")
        self._duration_node = self._find_duration_node()

    # ============================================================
    # 公开接口
    # ============================================================
    def generate(
        self,
        prompt: str,
        image_b64: str,
        *,
        seed: Optional[int] = None,
        aspect_ratio: Optional[str] = None,
        megapixels: Optional[float] = None,
        steps: Optional[int] = None,
        duration: Optional[float] = None,
    ) -> str:
        """
        输入 prompt + base64 首帧图，返回生成的视频路径。

        参数:
            prompt       — 动作/内容提示词（MiniMax H3 图生视频）
            image_b64    — 首帧图片的 base64 编码字符串（不带 data URI 前缀）
            seed         — 随机种子（None=用工作流默认值）
            aspect_ratio — 输出画面比例（None=按图片方向自动选择）
            megapixels   — 目标总像素（百万像素，None=用工作流默认值）
            steps        — 采样步数（None=用工作流默认值）
            duration     — 视频时长（秒，None=用工作流默认值）
        """
        wf = self._copy_workflow()
        self._counter += 1

        # 首帧图（原始 base64）直接写入 ETN_LoadImageBase64 节点
        # 注意：该节点内部 base64.b64decode(image)，传入 data URI 会报 Incorrect padding
        if self._image_node:
            self._set_input(wf, self._image_node, "image", image_b64)
        # 提示词写入 MiniMaxH3ImageToVideo 节点
        if self._prompt_node:
            self._set_input(wf, self._prompt_node, "prompt", prompt)
        # 种子写入 RandomNoise 节点
        if seed is not None and self._seed_node:
            self._set_input(wf, self._seed_node, "noise_seed", seed)
        # 输出比例：未指定则按图片方向选择（竖=9:16，横=16:9，方=1:1）
        if self._resolution_node:
            ratio = aspect_ratio or self._detect_aspect_ratio(image_b64)
            if ratio:
                self._set_input(wf, self._resolution_node, "aspect_ratio", ratio)
            if megapixels is not None:
                self._set_input(wf, self._resolution_node, "megapixels", megapixels)
        # 采样步数
        if steps is not None and self._scheduler_node:
            self._set_input(wf, self._scheduler_node, "steps", steps)
        # 视频时长（秒）
        if duration is not None and self._duration_node:
            self._set_input(wf, self._duration_node, "value", duration)

        # 提交 → 等待 → 下载
        prompt_id = self._queue(wf)
        history = self._wait(prompt_id)
        return self._download(history, prompt_id)

    # ============================================================
    # 内部 — ComfyUI HTTP API
    # ============================================================
    def _queue(self, prompt: dict) -> str:
        resp = requests.post(
            f"{self.base_url}/prompt",
            # preview_method=no_preview：跳过 latent 预览解码/编码（无人接收时纯浪费）
            json={
                "prompt": prompt,
                "client_id": self._client_id,
                "extra_data": {"preview_method": "no_preview"},
            },
        )
        resp.raise_for_status()
        return resp.json()["prompt_id"]

    def _wait(self, prompt_id: str) -> dict:
        start = time.time()
        while time.time() - start < self.timeout:
            resp = requests.get(f"{self.base_url}/history/{prompt_id}")
            if resp.status_code == 200:
                data = resp.json().get(prompt_id)
                if data is not None:
                    return data
            time.sleep(self.poll_interval)
        raise TimeoutError(f"生成超时 ({self.timeout}s)，prompt_id={prompt_id}")

    def _download(self, history: dict, prompt_id: str) -> str:
        # SaveVideo 的输出在历史记录里可能是 videos / gifs / images，兼容三种
        files = []
        prompt_data = history.get(prompt_id, history)
        for node_output in prompt_data.get("outputs", {}).values():
            for key in ("videos", "gifs", "images"):
                for item in node_output.get(key, []):
                    files.append(item)

        if not files:
            raise RuntimeError("工作流没有输出视频，请检查工作流是否正确")

        # 只取第一个
        video = files[0]
        params = {
            "filename": video["filename"],
            "subfolder": video.get("subfolder", ""),
            "type": video.get("type", "output"),
        }
        resp = requests.get(f"{self.base_url}/view", params=params)
        resp.raise_for_status()

        suffix = Path(video["filename"]).suffix or ".mp4"
        out_path = self.output_dir / f"{self._counter:04d}{suffix}"
        out_path.write_bytes(resp.content)
        self._delete_remote(video)
        return str(out_path.resolve())

    def _delete_remote(self, video: dict) -> None:
        """下载完成后删除 ComfyUI 机器上的原文件（腾磁盘空间，尽力而为）"""
        if not self.delete_base:
            return
        try:
            resp = requests.delete(
                f"{self.delete_base}/delete",
                params={"name": video["filename"]},
                timeout=10,
            )
            if resp.status_code != 200:
                print(f"[VIDEO] 远端删除失败: {resp.status_code} {resp.text[:200]}", flush=True)
        except Exception as e:
            print(f"[VIDEO] 远端删除异常: {e}", flush=True)

    # ============================================================
    # 内部 — 工作流操作
    # ============================================================
    @staticmethod
    def _load_json(path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _copy_workflow(self) -> dict:
        """深拷贝工作流，避免修改原始对象"""
        return json.loads(json.dumps(self.workflow))

    def _find_first(self, class_type: str, index: int = 0) -> Optional[str]:
        """找第 index 个 class_type 类型的节点 ID"""
        matches = [
            nid for nid, node in self.workflow.items()
            if isinstance(node, dict) and node.get("class_type") == class_type
        ]
        return matches[index] if len(matches) > index else None

    def _find_duration_node(self) -> Optional[str]:
        """找视频时长节点：优先 _meta.title 含 duration 的 PrimitiveFloat，否则第一个 PrimitiveFloat"""
        for nid, node in self.workflow.items():
            if isinstance(node, dict) and node.get("class_type") == "PrimitiveFloat":
                title = (node.get("_meta") or {}).get("title", "")
                if "duration" in str(title).lower():
                    return nid
        return self._find_first("PrimitiveFloat")

    @staticmethod
    def _set_input(workflow: dict, node_id: str, field: str, value):
        node = workflow.get(node_id, {})
        inputs = node.get("inputs", {})
        if field in inputs:
            inputs[field] = value

    @staticmethod
    def _detect_aspect_ratio(image_b64: str) -> Optional[str]:
        """按图片宽高方向返回 ResolutionSelector 的 aspect_ratio 值"""

        def image_size(data: bytes) -> Optional[tuple[int, int]]:
            # PNG（IHDR：偏移 16 起 big-endian 宽高）
            if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
                return (
                    int.from_bytes(data[16:20], "big"),
                    int.from_bytes(data[20:24], "big"),
                )
            # JPEG（扫描 SOF0/SOF1/SOF2 等标记读宽高）
            if data[:2] == b"\xff\xd8":
                i, n = 2, len(data)
                sof = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
                while i + 9 < n:
                    if data[i] != 0xFF:
                        i += 1
                        continue
                    marker = data[i + 1]
                    if marker in sof:
                        return (
                            int.from_bytes(data[i + 7:i + 9], "big"),
                            int.from_bytes(data[i + 5:i + 7], "big"),
                        )
                    if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                        i += 2
                    else:
                        i += 2 + int.from_bytes(data[i + 2:i + 4], "big")
            return None

        try:
            size = image_size(base64.b64decode(image_b64))
        except Exception:
            size = None
        if not size:
            return None
        w, h = size
        if h > w:
            return "9:16 (Portrait Widescreen)"
        if w > h:
            return "16:9 (Widescreen)"
        return "1:1 (Square)"


# ============================================================
# 命令行入口
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ComfyUI 视频生成器（MiniMax H3 图生视频）")
    parser.add_argument("--prompt", "-p", required=True, help="动作/内容提示词")
    parser.add_argument("--image", "-i", required=True, help="首帧图片路径")
    parser.add_argument("--seed", "-s", type=int)
    parser.add_argument("--workflow", default="minimax_h3_i2v_workflow.json")
    parser.add_argument("--base-url", default="http://127.0.0.1:8188")
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()

    image_b64 = base64.b64encode(Path(args.image).read_bytes()).decode("ascii")
    gen = ComfyUIVideoGenerator(
        workflow=args.workflow,
        base_url=args.base_url,
        output_dir=args.output_dir,
    )
    path = gen.generate(args.prompt, image_b64, seed=args.seed)
    print(path)
