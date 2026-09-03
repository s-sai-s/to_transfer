from __future__ import annotations
import os
import requests
import warnings
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    retry_if_exception_message,
)

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Type,
    Union,
)

import tiktoken
from dotenv import load_dotenv
from langchain_core.callbacks import (
    CallbackManagerForLLMRun,
)
from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import (
    BaseMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import BaseModel
from langchain_core.runnables import Runnable

from langchain_community.adapters.openai import (
    convert_dict_to_message,
)

from langchain_community.chat_models.openai import ChatOpenAI

warnings.filterwarnings("ignore")

load_dotenv()

MODEL_NAME = "GPT-4o"
TEMPERATURE = 0.2
MAX_TOKENS = 16000

get_num_tokens = lambda text: len(tiktoken.get_encoding("cl100k_base").encode(text))


class PerformGPTCall:
    def __init__(
        self,
        #  model_name='gpt-4o',
        temperature=0.2,
        max_tokens=4096,
    ):
        # self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens

        self.__url = (
            "https://studiogateway.chubb.com/enterprise.operations.authorization"
        )
        # self.__url = os.getenv("CHUBBGPT_AUTH_URL")
        self.__query_params = {"Identity": "AAD"}
        self.__headers = {
            "App_ID": os.getenv("CHUBBGPT_APP_ID"),
            "App_Key": os.getenv("CHUBBGPT_APP_KEY"),
            "Resource": os.getenv("CHUBBGPT_RESOURCE_ID"),
            "apiVersion": "1",
        }
        self.__api_url = "https://studiogateway.chubb.com/enterprise.data.nonuiglobalaimlopschubbgpt/openai/experimental?cloud=Azure&model=api_openai_gpt_4o_g&conversation=true&service=OpenAI&region=e-us2"

        # self.__api_url = os.getenv('CHUBBGPT_URL')
        self.__auth_headers = self.get_auth_headers()
        self.__chat_openai = ChatOpenAI()

    @retry(
        retry=(
            retry_if_exception(requests.exceptions.HTTPError)
            and (retry_if_exception_message("ChubbGPT Capacity 429 Exception."))
        ),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, max=5),
    )
    def get_auth_headers(self):
        response = requests.post(
            self.__url, headers=self.__headers, params=self.__query_params
        )
        self.access_token = response.json().get("access_token")
        # Headers for subsequent calls
        self.__auth_headers = {
            "Authorization": "Bearer " + self.access_token,
            "Content-Type": "application/json",
            "apiVersion": "1",
        }
        return self.__auth_headers

    def __messages_to_payload(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ):
        message_dicts = self.__chat_openai._create_message_dicts(messages, stop)
        messages = [
            {
                "role": msg["role"],
                "content": (
                    ""
                    if "content" not in msg or msg["content"] is None
                    else msg["content"]
                ),
                **{k: v for k, v in msg.items() if k not in ["role", "content"]},
            }
            for msg in message_dicts[0]
        ]
        payload = {
            "username": "TEST",
            "session_id": "1",
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        return payload

    def __get_api_response(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ):
        payload = self.__messages_to_payload(messages, stop, **kwargs)
        try:
            api_response = requests.post(
                self.__api_url, headers=self.__auth_headers, json=payload
            )
        except:
            try:
                self.__auth_headers = self.get_auth_headers()
                api_response = requests.post(
                    self.__api_url, headers=self.__auth_headers, json=payload
                )
            except Exception as e:
                raise e
        return api_response

    def __process_api_response(self, api_response):
        status_code = api_response.status_code
        if status_code != 200:
            if status_code == 500:
                message_to_user = (
                    "Inapproprite content. Please verify your message and try again."
                )
                response_json = {
                    "id": "chatcmpl-A0mC2TUClSvjaN6l8Z3UDLG7TmHcI",
                    "choices": [
                        {
                            "finish_reason": "length",
                            "index": 0,
                            "logprobs": None,
                            "message": {
                                "content": message_to_user,
                                "refusal": None,
                                "role": "assistant",
                                "function_call": None,
                                "tool_calls": None,
                            },
                            "content_filter_results": {
                                "hate": {"filtered": False, "severity": "safe"},
                                "protected_material_code": {
                                    "filtered": False,
                                    "detected": False,
                                },
                                "protected_material_text": {
                                    "filtered": False,
                                    "detected": False,
                                },
                                "self_harm": {"filtered": False, "severity": "safe"},
                                "sexual": {"filtered": False, "severity": "safe"},
                                "violence": {"filtered": False, "severity": "safe"},
                            },
                        }
                    ],
                    "created": 1724748618,
                    "model": "gpt-4o-2024-05-13",
                    "object": "chat.completion",
                    "service_tier": None,
                    "system_fingerprint": "fp_80a1bad4c7",
                    "usage": {
                        "completion_tokens": 512,
                        "prompt_tokens": 91,
                        "total_tokens": 603,
                    },
                    "prompt_filter_results": [
                        {
                            "prompt_index": 0,
                            "content_filter_results": {
                                "hate": {"filtered": False, "severity": "safe"},
                                "jailbreak": {"filtered": False, "detected": False},
                                "self_harm": {"filtered": False, "severity": "safe"},
                                "sexual": {"filtered": False, "severity": "safe"},
                                "violence": {"filtered": False, "severity": "safe"},
                            },
                        }
                    ],
                }

                # Delete the Message From Conversation
                message_dicts = tuple(
                    [message_dicts[0][0:-1]] + [idx for idx in message_dicts[1:]]
                )
            else:
                raise Exception(
                    {
                        "status_code": status_code,
                        "detail": f"Error in GPT-4 response: {api_response.text}",
                    }
                )
        else:
            response_json = api_response.json()
        chat_resonpse = self.__chat_openai._create_chat_result(response_json)
        return chat_resonpse

    @retry(
        retry=(
            retry_if_exception(requests.exceptions.HTTPError)
            and (retry_if_exception_message("ChubbGPT Capacity 429 Exception."))
        ),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, max=5),
    )
    def get_response(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ):
        api_response = self.__get_api_response(messages, stop, **kwargs)
        chat_response = self.__process_api_response(api_response)
        return chat_response

    def __call__(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ):
        return self.get_response(messages, stop, **kwargs)


perform_gpt_call = PerformGPTCall(temperature=TEMPERATURE, max_tokens=MAX_TOKENS)


class ChatChubbGPT(ChatOpenAI):
    """`OpenAI` Chat large language models API.

    To use, you should have the ``openai`` python package installed, and the
    environment variable ``OPENAI_API_KEY`` set with your API key.

    Any parameters that are valid to be passed to the openai.create call can be passed
    in, even if not explicitly saved on this class.

    Example:
        .. code-block:: python

            from langchain_community.chat_models import ChatOpenAI
            openai = ChatOpenAI(model="gpt-3.5-turbo")
    """

    model_name: str = MODEL_NAME
    temperature: float = TEMPERATURE
    max_tokens: int = MAX_TOKENS
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    top_p: int = 1
    chances: int = 5
    n: int = 1

    def get_num_tokens_from_messages(self, buffer):
        return get_num_tokens(str(buffer))

    def _create_chat_result(self, response: Union[dict, BaseModel]) -> ChatResult:
        generations = []
        if not isinstance(response, dict):
            response = response.dict()
        for res in response["choices"]:
            message = convert_dict_to_message(res["message"])
            generation_info = dict(finish_reason=res.get("finish_reason"))
            if "logprobs" in res:
                generation_info["logprobs"] = res["logprobs"]
            gen = ChatGeneration(
                message=message,
                generation_info=generation_info,
            )
            generations.append(gen)
        token_usage = response.get("usage", {})
        llm_output = {
            "token_usage": token_usage,
            "model_name": self.model_name,
            "system_fingerprint": response.get("system_fingerprint", ""),
        }
        return ChatResult(generations=generations, llm_output=llm_output)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        stream: Optional[bool] = None,
        **kwargs: Any,
    ) -> ChatResult:
        perform_gpt_call = PerformGPTCall(
            temperature=TEMPERATURE, max_tokens=MAX_TOKENS
        )
        try:
            chat_response = perform_gpt_call(messages, stop, **kwargs)
        except:
            # perform_gpt_call = PerformGPTCall(temperature=TEMPERATURE, max_tokens=MAX_TOKENS)
            perform_gpt_call.get_auth_headers()
            chat_response = perform_gpt_call(messages, stop, **kwargs)
        return chat_response

    @property
    def _llm_type(self) -> str:
        """Return type of chat model."""
        return "ChubbGPT"

    def bind_tools(
        self,
        tools: Sequence[Union[Dict[str, Any], Type[BaseModel], Callable]],
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, BaseMessage]:
        """Bind functions (and other objects) to this chat model.

        Args:
            functions: A list of function definitions to bind to this chat model.
                Can be  a dictionary, pydantic model, or callable. Pydantic
                models and callables will be automatically converted to
                their schema dictionary representation.
            function_call: Which function to require the model to call.
                Must be the name of the single provided function or
                "auto" to automatically determine which function to call
                (if any).
            kwargs: Any additional parameters to pass to the
                :class:`~langchain.runnable.Runnable` constructor.
        """
        # from langchain.chains.openai_functions.base import convert_to_openai_function
        from langchain_core.utils.function_calling import convert_to_openai_function

        formatted_functions = [convert_to_openai_function(fn) for fn in tools]
        formatted_functions = [
            {"type": "function", "function": fn} for fn in formatted_functions
        ]

        if tool_choice is not None:
            if len(formatted_functions) < 1:
                raise ValueError(
                    "When specifying `tool_choice`, you must at least provide one "
                    "tool."
                )
            if tool_choice != "auto":
                raise ValueError(f"tool_choice must always be auto.")
            kwargs = {**kwargs, "tool_choice": tool_choice}
        return super().bind(
            tools=formatted_functions,
            **kwargs,
        )
