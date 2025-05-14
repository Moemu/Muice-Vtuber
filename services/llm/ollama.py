from typing import AsyncGenerator, List, Literal, Optional, Union, overload

import ollama
import logging
from ollama import ResponseError

from ._types import BasicModel, Message, ModelConfig, function_call_handler
from .utils.images import get_image_base64

logger = logging.getLogger("Muice.Ollama")


class Ollama(BasicModel):
    """
    使用 Ollama 模型服务调用模型
    """

    def __init__(self, model_config: ModelConfig) -> None:
        super().__init__(model_config)
        self._require("model_name")
        self.model = self.config.model_name
        self.host = self.config.api_host if self.config.api_host else "http://localhost:11434"
        self.top_k = self.config.top_k
        self.top_p = self.config.top_p
        self.temperature = self.config.temperature
        self.repeat_penalty = self.config.repetition_penalty
        self.presence_penalty = self.config.presence_penalty
        self.frequency_penalty = self.config.frequency_penalty
        self.stream = self.config.stream

        self._tools: List[dict] = []

    def load(self) -> bool:
        try:
            self.client = ollama.AsyncClient(host=self.host)
            self.is_running = True
        except ResponseError as e:
            logger.error(f"加载 Ollama 加载器时发生错误： {e}")
        except ConnectionError as e:
            logger.error(f"加载 Ollama 加载器时发生错误： {e}")
        finally:
            return self.is_running

    def __build_image_message(self, prompt: str, image_paths: Optional[List[str]] = []) -> dict:
        images = []

        if image_paths:
            for image_path in image_paths:
                image_base64 = get_image_base64(local_path=image_path)
                images.append(image_base64)

        message = {"role": "user", "content": prompt, "images": images}

        return message

    def _build_messages(
        self, prompt: str, history: List[Message], image_paths: Optional[List[str]] = [], system: Optional[str] = None
    ) -> list:
        messages = []

        if system:
            messages.append({"role": "system", "content": system})

        for index, item in enumerate(history):
            messages.append(self.__build_image_message(item.danmu, image_paths))
            messages.append({"role": "assistant", "content": item.respond})

        message = self.__build_image_message(prompt, image_paths)

        messages.append(message)

        return messages

    async def _ask_sync(self, messages: list) -> str:
        try:
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                tools=self._tools,
                stream=False,
                options={
                    "temperature": self.temperature,
                    "top_k": self.top_k,
                    "top_p": self.top_p,
                    "repeat_penalty": self.repeat_penalty,
                    "presence_penalty": self.presence_penalty,
                    "frequency_penalty": self.frequency_penalty,
                },
            )

            tool_calls = response.message.tool_calls

            if not tool_calls:
                return response.message.content if response.message.content else "(警告：模型无返回)"

            for tool in tool_calls:
                function_name = tool.function.name
                function_args = tool.function.arguments

                logger.info(f"function call 请求 {function_name}, 参数: {function_args}")
                function_return = await function_call_handler(function_name, dict(function_args))
                logger.info(f"Function call 成功，返回: {function_return}")

                messages.append(response.message)
                messages.append({"role": "tool", "content": str(function_return), "name": tool.function.name})
                return await self._ask_sync(messages)

        except ollama.ResponseError as e:
            logger.error(f"模型调用错误: {e.error}")
            self.succeed = False
            return f"模型调用错误: {e.error}"

        self.succeed = False
        return "模型调用错误: 未知错误"

    async def _ask_stream(self, messages: list) -> AsyncGenerator[str, None]:
        try:
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                tools=self._tools,
                stream=True,
                options={
                    "temperature": self.temperature,
                    "top_k": self.top_k,
                    "top_p": self.top_p,
                    "repeat_penalty": self.repeat_penalty,
                    "presence_penalty": self.presence_penalty,
                    "frequency_penalty": self.frequency_penalty,
                },
            )

            async for chunk in response:
                logger.debug(chunk)

                tool_calls = chunk.message.tool_calls

                if chunk.message.content:
                    yield chunk.message.content
                    continue

                if not tool_calls:
                    continue

                for tool in tool_calls:  # type:ignore
                    function_name = tool.function.name
                    function_args = tool.function.arguments

                    logger.info(f"function call 请求 {function_name}, 参数: {function_args}")
                    function_return = await function_call_handler(function_name, dict(function_args))
                    logger.info(f"Function call 成功，返回: {function_return}")

                    messages.append(chunk.message)  # type:ignore
                    messages.append({"role": "tool", "content": str(function_return), "name": tool.function.name})

                    async for content in self._ask_stream(messages):
                        yield content

        except ollama.ResponseError as e:
            logger.error(f"模型调用错误: {e.error}")
            yield f"模型调用错误: {e.error}"
            self.succeed = False
            return

    @overload
    async def ask(
        self,
        prompt: str,
        history: List[Message],
        images: Optional[List[str]] = [],
        tools: Optional[List[dict]] = [],
        stream: Literal[False] = False,
        system: Optional[str] = None,
        **kwargs,
    ) -> str: ...

    @overload
    async def ask(
        self,
        prompt: str,
        history: List[Message],
        images: Optional[List[str]] = [],
        tools: Optional[List[dict]] = [],
        stream: Literal[True] = True,
        system: Optional[str] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]: ...

    async def ask(
        self,
        prompt: str,
        history: List[Message],
        images: Optional[List[str]] = [],
        tools: Optional[List[dict]] = [],
        stream: Optional[bool] = False,
        system: Optional[str] = None,
        **kwargs,
    ) -> Union[AsyncGenerator[str, None], str]:
        self.succeed = True
        self._tools = tools if tools else []
        messages = self._build_messages(prompt, history, images, system)

        if stream:
            return self._ask_stream(messages)

        return await self._ask_sync(messages)
