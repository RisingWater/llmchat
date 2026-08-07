"""
ComfyUI 图片生成器 — 输入 prompt 字符串，输出本地图片路径。

用法:
    from comfyui_gen import ComfyUIImageGenerator

    gen = ComfyUIImageGenerator(
        workflow="image_z_image_turbo.json",
        base_url="http://192.168.1.181:8188",
    )
    path = gen.generate("a cat wearing sunglasses")
    print(path)  # → D:/wangxu/ai/llmchat/output/0001.png
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Optional

import requests


class ComfyUIImageGenerator:
    """封装 ComfyUI API，输入 prompt → 输出图片路径"""

    def __init__(
        self,
        workflow: str = "image_z_image_turbo.json",
        base_url: str = "http://192.168.1.181:8188",
        output_dir: str = "output",
        timeout: int = 120,
        poll_interval: float = 1.0,
    ):
        """
        workflow      — 工作流 JSON 文件路径
        base_url      — ComfyUI 地址
        output_dir    — 输出图片保存目录
        timeout       — 最大等待秒数
        poll_interval — 轮询间隔（秒）
        """
        self.base_url = base_url.rstrip("/")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.poll_interval = poll_interval

        # 加载工作流
        wf_path = Path(workflow)
        if not wf_path.exists():
            raise FileNotFoundError(f"工作流文件不存在: {workflow}")
        self.workflow = self._load_json(wf_path)
        self._client_id = str(uuid.uuid4())
        self._counter = 0  # 生成计数，用于文件名

        # 探测关键节点
        self._positive_node = self._find_first("CLIPTextEncode", index=0)
        self._negative_node = self._find_first("CLIPTextEncode", index=1)
        self._sampler_node = (
            self._find_first("KSampler")
            or self._find_first("KSamplerAdvanced")
            or self._find_first("BNK_TiledKSampler")
        )

    # ============================================================
    # 公开接口
    # ============================================================
    def generate(
        self,
        prompt: str,
        *,
        negative: str = "",
        seed: Optional[int] = None,
        steps: Optional[int] = None,
        cfg: Optional[float] = None,
        denoise: Optional[float] = None,
    ) -> str:
        """
        输入 prompt，返回生成的图片路径。

        参数:
            prompt   — 正向提示词
            negative — 反向提示词
            seed     — 随机种子（None=用工作流默认值）
            steps    — 采样步数
            cfg      — CFG scale
            denoise  — 降噪强度
        """
        wf = self._copy_workflow()
        self._counter += 1

        # 修改参数
        if self._positive_node:
            self._set_input(wf, self._positive_node, "text", prompt)
        if negative and self._negative_node:
            self._set_input(wf, self._negative_node, "text", negative)
        if self._sampler_node:
            if seed is not None:
                self._set_input(wf, self._sampler_node, "seed", seed)
            if steps is not None:
                self._set_input(wf, self._sampler_node, "steps", steps)
            if cfg is not None:
                self._set_input(wf, self._sampler_node, "cfg", cfg)
            if denoise is not None:
                self._set_input(wf, self._sampler_node, "denoise", denoise)

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
            json={"prompt": prompt, "client_id": self._client_id},
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
        images = []
        prompt_data = history.get(prompt_id, history)
        for node_output in prompt_data.get("outputs", {}).values():
            for img in node_output.get("images", []):
                images.append(img)

        if not images:
            raise RuntimeError("工作流没有输出图片，请检查工作流是否正确")

        # 只取第一张
        img = images[0]
        params = {
            "filename": img["filename"],
            "subfolder": img.get("subfolder", ""),
            "type": img.get("type", "output"),
        }
        resp = requests.get(f"{self.base_url}/view", params=params)
        resp.raise_for_status()

        out_path = self.output_dir / f"{self._counter:04d}.png"
        out_path.write_bytes(resp.content)
        return str(out_path.resolve())

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

    @staticmethod
    def _set_input(workflow: dict, node_id: str, field: str, value):
        node = workflow.get(node_id, {})
        inputs = node.get("inputs", {})
        if field in inputs:
            inputs[field] = value


# ============================================================
# 命令行入口
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ComfyUI 图片生成器")
    parser.add_argument("--prompt", "-p", required=True, help="正向提示词")
    parser.add_argument("--negative", "-n", default="", help="反向提示词")
    parser.add_argument("--seed", "-s", type=int)
    parser.add_argument("--steps", type=int)
    parser.add_argument("--cfg", type=float)
    parser.add_argument("--denoise", type=float)
    parser.add_argument("--workflow", default="image_z_image_turbo.json")
    parser.add_argument("--base-url", default="http://192.168.1.181:8188")
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()

    gen = ComfyUIImageGenerator(
        workflow=args.workflow,
        base_url=args.base_url,
        output_dir=args.output_dir,
    )
    path = gen.generate(
        args.prompt,
        negative=args.negative,
        seed=args.seed,
        steps=args.steps,
        cfg=args.cfg,
        denoise=args.denoise,
    )
    print(path)
