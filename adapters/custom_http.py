
import aiohttp, json, re
from typing import Dict, List, Tuple
from astrbot.api import logger
from .base import ImageProviderAdapter

class OpenAIImagesAdapter(ImageProviderAdapter):
    async def generate_image(
        self, *, base_url: str, api_key: str, model: str, prompt: str,
        negative_prompt: str | None = None, image_size: str | None = None,
        batch_size: int | None = None, seed: int | None = None,
        num_inference_steps: int | None = None, guidance_scale: float | None = None,
        cfg: float | None = None, image: str | None = None,
        image2: str | None = None, image3: str | None = None,
        extra_headers: Dict[str, str] | None = None,
    ):
        # 允许：/images/generations 完整端点；或 /v1 / 根域名，自动补齐
        b = (base_url or "").rstrip("/")
        if not b:
            b = "https://api.example.com/v1"  # 留给上层或子类覆盖默认
        if b.endswith("/images/generations"):
            url = b
        else:
            if not re.search(r"/v\d+$", b):
                b = b + "/v1"
            url = b + "/images/generations"
        logger.info(f"[imgtool] POST {url}")

        # 模型族，决定可发送字段
        m = (model or "").lower()
        if "kolors" in m:
            family = "kolors"
        elif "image-edit" in m:
            family = "qwen_edit"
        elif "qwen-image" in m:
            family = "qwen_image"
        else:
            family = "generic"
        logger.info(f"[imgtool] model_family={family}")

        payload: Dict = {"model": model, "prompt": prompt}
        if negative_prompt: payload["negative_prompt"] = negative_prompt
        if seed is not None: payload["seed"] = int(seed)
        if num_inference_steps: payload["num_inference_steps"] = int(num_inference_steps)

        if family == "kolors":
            if image_size: payload["image_size"] = image_size
            if batch_size: payload["batch_size"] = max(1, min(4, int(batch_size)))
            if guidance_scale is not None: payload["guidance_scale"] = float(guidance_scale)
            if image: payload["image"] = image
        elif family == "qwen_image":
            if image_size: payload["image_size"] = image_size
            if cfg is not None: payload["cfg"] = float(cfg)
            if image: payload["image"] = image
        elif family == "qwen_edit":
            if image: payload["image"] = image
            if "2509" in m:
                if image2: payload["image2"] = image2
                if image3: payload["image3"] = image3
        else:
            if image_size: payload["image_size"] = image_size
            if cfg is not None: payload["cfg"] = float(cfg)
            if image: payload["image"] = image

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        if extra_headers: headers.update(extra_headers)
        timeout = aiohttp.ClientTimeout(total=180)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.post(url, headers=headers, json=payload) as resp:
                txt = await resp.text()
                status = resp.status
        if status >= 400:
            # 尽量把服务端返回的错误信息提取出来，方便定位
            detail = txt
            try:
                err = json.loads(txt)
                if isinstance(err, dict):
                    e = err.get("error")
                    if isinstance(e, dict):
                        detail = e.get("message") or e.get("code") or txt
                    elif isinstance(e, str):
                        detail = e
                    elif err.get("message"):
                        detail = err["message"]
            except Exception:
                pass
            raise RuntimeError(f"HTTP {status} when POST {url}: {detail[:800]}")

        try:
            data = json.loads(txt)
        except Exception:
            raise RuntimeError(
                f"接口 {url} 返回的不是 JSON（前 300 字符）：{txt[:300]}"
            )
        if not isinstance(data, dict):
            raise RuntimeError(f"接口 {url} 返回格式不是对象：{str(data)[:300]}")

        urls: List[str] = []
        items = data.get("images")
        if items is None:
            items = data.get("data")
        if isinstance(items, dict):
            items = [items]
        if isinstance(items, list):
            for item in items:
                if isinstance(item, str) and item:
                    urls.append(item)
                    continue
                if not isinstance(item, dict):
                    continue
                u = item.get("url") or item.get("image_url")
                if isinstance(u, str) and u:
                    urls.append(u)
                    continue
                urls.extend(_b64_to_data_url(item))
        # 少数接口把单张图直接放在顶层
        if not urls:
            urls.extend(_b64_to_data_url(data))
            top_url = data.get("url")
            if isinstance(top_url, str) and top_url:
                urls.append(top_url)

        if not urls:
            # 200 但没解析到图片，把返回内容回显出来，避免只提示「已生成 0 张图」
            err = data.get("error") or data.get("message") or txt
            raise RuntimeError(f"接口 {url} 未返回图片（返回内容）：{str(err)[:500]}")
        return urls, data


def _b64_to_data_url(item: Dict) -> List[str]:
    """把 b64_json / base64 / image 等字段统一转成 data URL。"""
    out: List[str] = []
    for key in ("b64_json", "base64", "image_base64", "image"):
        v = item.get(key)
        if not isinstance(v, str) or not v:
            continue
        if v.startswith("data:image/"):
            out.append(v)
            continue
        if key == "b64_json" or len(v) > 256:
            out.append(f"data:image/png;base64,{v}")
            break
    return out
