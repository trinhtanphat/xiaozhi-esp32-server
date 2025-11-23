from abc import ABC, abstractmethod
from typing import Optional


class VADProviderBase(ABC):
    @abstractmethod
    def is_vad(self, conn, data) -> bool:
        """检测音频数据中的语音活动"""
        pass

    async def close(self):
        """资源清理方法 - 子类可以重写此方法进行特定的清理操作"""
        pass
