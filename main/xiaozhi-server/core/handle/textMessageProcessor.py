import json
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from core.utils.log_sanitizer import redact_transcript_for_log

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from core.handle.textMessageHandlerRegistry import TextMessageHandlerRegistry

TAG = __name__


class IncomingTextMessage(BaseModel):
    """Minimal schema guard for device JSON messages."""

    model_config = ConfigDict(extra="allow")

    type: str = Field(min_length=1, max_length=32)


class TextMessageProcessor:
    """消息处理器主类"""

    def __init__(self, registry: TextMessageHandlerRegistry):
        self.registry = registry

    async def process_message(self, conn: "ConnectionHandler", message: str) -> None:
        """处理消息的主入口"""
        try:
            # 解析JSON消息
            msg_json = json.loads(message)

            # 处理JSON消息
            if isinstance(msg_json, dict):
                try:
                    msg_json = IncomingTextMessage.model_validate(msg_json).model_dump()
                except ValidationError as e:
                    conn.logger.bind(tag=TAG).warning(
                        f"JSON消息校验失败：{redact_transcript_for_log(message)}, error_count={len(e.errors())}"
                    )
                    await conn.websocket.close(code=1008, reason="invalid message schema")
                    return

                message_type = msg_json.get("type")

                # 记录日志
                conn.logger.bind(tag=TAG).info(
                    f"收到{message_type}消息：{redact_transcript_for_log(message)}"
                )

                # 获取并执行处理器
                handler = self.registry.get_handler(message_type)
                if handler:
                    await handler.handle(conn, msg_json)
                else:
                    conn.logger.bind(tag=TAG).error(
                        f"收到未知类型消息：type={message_type}, payload={redact_transcript_for_log(message)}"
                    )
            # 处理纯数字消息
            elif isinstance(msg_json, int):
                conn.logger.bind(tag=TAG).info("收到数字消息")
                await conn.websocket.send(message)

        except json.JSONDecodeError:
            # 非JSON消息直接转发
            conn.logger.bind(tag=TAG).error(
                f"解析到错误的消息：{redact_transcript_for_log(message)}"
            )
            await conn.websocket.send(message)
