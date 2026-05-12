import asyncio
import json
import logging
import aiofiles
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("qwen2api.db")

class AsyncJsonDB:
    """带异步读写锁的 JSON 文件存储，防止并发损坏"""
    def __init__(self, path: str | Path, default_data: Any = None):
        self.path = Path(path)
        self.default_data = default_data if default_data is not None else []
        self._lock = asyncio.Lock()
        self._data: Any = None
        self._init_file()

    def _init_file(self):
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.default_data, indent=2, ensure_ascii=False), encoding="utf-8")

    async def load(self) -> Any:
        async with self._lock:
            if not self.path.exists():
                self._data = self.default_data
                return self._data
            try:
                # 使用 aiofiles 进行非阻塞读写
                async with aiofiles.open(self.path, mode='r', encoding='utf-8') as f:
                    content = await f.read()
                self._data = json.loads(content)
            except Exception as e:
                log.error(f"Failed to load JSON from {self.path}: {e}")
                self._data = self.default_data
            return self._data

    async def save(self, data: Any):
        async with self._lock:
            self._data = data
            try:
                # 使用 aiofiles 进行非阻塞读写
                content = json.dumps(self._data, indent=2, ensure_ascii=False)
                async with aiofiles.open(self.path, mode='w', encoding='utf-8') as f:
                    await f.write(content)
            except Exception as e:
                log.error(f"Failed to save JSON to {self.path}: {e}")

    async def get(self) -> Any:
        if self._data is None:
            return await self.load()
        return self._data
