from typing import AsyncGenerator, List, Literal, Optional, Union, overload

from google import genai
from google.genai import errors
from google.genai.types import (
    Content,
    ContentOrDict,
    GenerateContentConfig,
    GoogleSearch,
    Part,
    Tool,
)

import logging

from ._types import BasicModel, Message, ModelConfig, function_call_handler
from .utils.images import get_image_base64

logger = logging.getLogger("Muice.Gemini")

class Gemini(BasicModel):
    def __init__(self, model_config: ModelConfig) -> None:
        super().__init__(model_config)
        self._require("model_name", "api_key")

        self.model_name = self.config.model_name
        self.api_key = self.config.api_key
        self.enable_search = self.config.online_search

        self.client = genai.Client(api_key=self.api_key)
        self.gemini_config = GenerateContentConfig(
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            top_k=self.config.top_k,
            max_output_tokens=self.config.max_tokens,
            presence_penalty=self.config.presence_penalty,
            frequency_penalty=self.config.frequency_penalty,
        )

        self.model = self.client.chats.create(model=self.model_name, config=self.gemini_config)

    def __build_user_parts(self, prompt: str, image_paths: Optional[List[str]] = []) -> list[Part]:
        user_parts: list[Part] = [Part.from_text(text=prompt)]

        if not image_paths:
            return user_parts

        for url in image_paths:
            user_parts.append(Part.from_bytes(data=get_image_base64(url), mime_type="image/jpeg"))  # type:ignore

        return user_parts

    def __build_tools_list(self, tools: Optional[List] = []):
        format_tools = []

        for tool in tools if tools else []:
            tool = tool["function"]
            required_parameters = tool["required"]
            del tool["required"]
            tool["parameters"]["required"] = required_parameters
            format_tools.append(tool)

        function_tools = Tool(function_declarations=format_tools)  # type:ignore

        if self.enable_search:
            function_tools.google_search = GoogleSearch()

        if tools or self.enable_search:
            self.gemini_config.tools = [function_tools]

    def _build_messages(
        self, prompt: str, history: List[Message], image_paths: Optional[List[str]] = [], system: Optional[str] = None
    ) -> list[ContentOrDict]:
        messages: List[ContentOrDict] = []

        if history:
            for index, item in enumerate(history):
                messages.append(Content(role="user", parts=self.__build_user_parts(item.danmu, [])))
                messages.append(Content(role="model", parts=[Part.from_text(text=item.respond)]))

        messages.append(Content(role="user", parts=self.__build_user_parts(prompt, image_paths)))

        return messages

    async def _ask_sync(self, messages: list[ContentOrDict], **kwargs) -> str:
        try:
            chat = self.client.aio.chats.create(model=self.model_name, config=self.gemini_config, history=messages[:-1])
            message = messages[-1].parts  # type:ignore
            response = await chat.send_message(message=message)  # type:ignore

            if response.text:
                return response.text

            if response.function_calls:
                function_call = response.function_calls[0]
                function_name = function_call.name
                function_args = function_call.args

                logger.info(f"function call 请求 {function_name}, 参数: {function_args}")
                function_return = await function_call_handler(function_name, function_args)  # type:ignore
                logger.info(f"Function call 成功，返回: {function_return}")

                function_response_part = Part.from_function_response(
                    name=function_name,  # type:ignore
                    response={"result": function_return},
                )

                messages.append(Content(role="model", parts=[Part(function_call=function_call)]))
                messages.append(Content(role="user", parts=[function_response_part]))

                return await self._ask_sync(messages)

            return "（警告：模型无输出！）"

        except errors.APIError as e:
            error_message = f"API 状态异常: {e.code}({e.response})"
            logger.error(error_message)
            logger.error(e.message)
            self.succeed = False
            return error_message

    async def _ask_stream(self, messages: list, **kwargs) -> AsyncGenerator[str, None]:
        try:
            async for chunk in await self.client.aio.models.generate_content_stream(
                model=self.model_name, contents=messages, config=self.gemini_config
            ):  # type:ignore
                if chunk.text:
                    yield chunk.text

                if chunk.function_calls:
                    function_call = chunk.function_calls[0]
                    function_name = function_call.name
                    function_args = function_call.args

                    logger.info(f"function call 请求 {function_name}, 参数: {function_args}")
                    function_return = await function_call_handler(function_name, function_args)  # type:ignore
                    logger.info(f"Function call 成功，返回: {function_return}")

                    function_response_part = Part.from_function_response(
                        name=function_name,  # type:ignore
                        response={"result": function_return},
                    )

                    messages.append(Content(role="model", parts=[Part(function_call=function_call)]))
                    messages.append(Content(role="user", parts=[function_response_part]))

                    async for chunk in self._ask_stream(messages):
                        yield chunk

        except errors.APIError as e:
            error_message = f"API 状态异常: {e.code}({e.response})"
            logger.error(error_message)
            logger.error(e.message)
            self.succeed = False
            yield error_message
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
        self.__build_tools_list(tools)
        self.gemini_config.system_instruction = system

        messages = self._build_messages(prompt, history, images, system)

        if stream:
            return self._ask_stream(messages)

        return await self._ask_sync(messages)  # type:ignore
