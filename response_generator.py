from typing import *
import inspect
from pathlib import Path
import json
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langchain_community.chat_models.openai import ChatOpenAI
from langchain_core.output_parsers import BaseOutputParser

from langchain_classic.output_parsers.fix import OutputFixingParser
# from langchain.output_parsers import OutputFixingParser
from langchain_core.tools import tool, StructuredTool
from src.chubb_gpt import ChatChubbGPT
from src.prompt_maker import make_prompt, pdf_to_image_filepath_list
from src.helper import extract_code_blocks, json_to_python_syntax


def __get_message_content(message: HumanMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    elif isinstance(content, dict):
        return content["text"]
    elif isinstance(content, list):
        return content[0]["text"]
    else:
        raise Exception(f"InvalidMessageContent: type -> {type(content)}")


def __update_message_content(message: HumanMessage, new_content: str) -> HumanMessage:
    content = message.content
    if isinstance(content, str):
        message.content = new_content
        return message
    elif isinstance(content, dict):
        content["text"] = new_content
        message.content = content
        return message
    elif isinstance(content, list):
        content[0]["text"] = new_content
        message.content = content
        return message
    else:
        raise Exception(f"InvalidMessageContent: type -> {type(content)}")


def __parse_response(resp_content, parser):
    try:
        parsed_response = parser.parse(resp_content)
    except ValueError:
        code_blocks = extract_code_blocks(resp_content)
        print(code_blocks)
        code_block = code_blocks[0]
        if code_block[1] == "json":
            json_string = code_block[0]
            return json_to_python_syntax(json_string)
        else:
            print("#" * 50, code_block[1], "#" * 50)
            raise Exception(f"CodeBlock is not in JSON: {code_block[1]}")
    except Exception as e:
        raise e
    else:
        if isinstance(parsed_response, BaseModel):
            return parsed_response.model_dump()
        else:
            return parsed_response


def __get_parsed_response(
    chat: ChatOpenAI,
    messages: List[BaseModel],
    output_parser: BaseOutputParser,
    chances: int = 5,
):
    for first_chance in range(chances):
        try:
            ai_response = chat.invoke(input=messages)
            ai_resp_content = ai_response.content
            if output_parser is None:
                return ai_resp_content
            else:
                try:
                    # parsed_response = output_parser.parse(ai_resp_content)
                    parsed_response = __parse_response(ai_resp_content, output_parser)
                except:
                    fixing_parser = OutputFixingParser.from_llm(
                        parser=output_parser, llm=chat
                    )
                    for second_chance in range(chances):
                        try:
                            # parsed_response = fixing_parser.parse(ai_resp_content)
                            parsed_response = __parse_response(
                                ai_resp_content, fixing_parser
                            )
                        except:
                            ai_resp_content += " "
                            continue
                        else:
                            return parsed_response
                else:
                    return parsed_response
        except:
            human_message = messages[-1]
            human_message_content = __get_message_content(human_message)
            human_message = __update_message_content(
                human_message, human_message_content + ((" ") * (first_chance + 1))
            )
            messages[-1] = human_message
            continue

    ai_response = chat.invoke(input=messages)
    ai_resp_content = ai_response.content

    if output_parser is None:
        return ai_resp_content
    else:
        parsed_response = __parse_response(ai_resp_content, output_parser)
        return parsed_response
        # return output_parser.parse(ai_resp_content).model_dump()


def get_parsed_response(
    user_prompt: str,
    system_prompt: str = None,
    tools: Optional[list] = None,
    pydantic_object: Optional[BaseModel] = None,
    source: Union[List[str], str] = None,
    page_range: Optional[tuple[int, int]] = None,
    strict: bool = True,
    chances: int = 5,
    output_dir: str = "temp",
    **kwargs,
):
    messages = []
    if system_prompt is not None:
        messages.append(SystemMessage(content=system_prompt))

    if isinstance(source, str):
        source = [source]

    if isinstance(source, list):
        temp_source = []
        for item in source:
            suffix = Path(item).suffix.lower()
            if suffix in [".png", ".jpeg", ".jpg"]:
                temp_source.append(item)
            elif suffix == ".pdf":
                curr_image_filepath_list = pdf_to_image_filepath_list(
                    pdf_filepath=item, page_range=page_range, output_dir=output_dir
                )
                temp_source.extend(curr_image_filepath_list)
            else:
                raise Exception(f"InvalidSource: {item}")
        source = temp_source

    chat = ChatChubbGPT()

    if isinstance(tools, list):
        res_tools = []
        for t in tools:
            if isinstance(t, StructuredTool):
                res_tools.append(t)
            elif inspect.isfunction(t):
                res_tools.append(tool(t))
            else:
                raise Exception(f"InvalidTool: {type(tool)}")

        chat = chat.bind_tools(
            res_tools, strict=True
        )  # this strict enforces tools and different from the input `strict` in this code that is used for output parsers

    message_dict = make_prompt(
        user_prompt, source, pydantic_object, strict=strict, **kwargs
    )

    human_message = message_dict["message"]
    output_parser = message_dict["output_parser"]

    messages.append(human_message)

    # ai_response = chat.invoke(input=messages)

    # ai_resp_content = ai_response.content

    # if output_parser is not None:
    #     try:
    #         parsed_response = output_parser.parse(ai_resp_content)
    #     except:
    #         fixing_parser = OutputFixingParser.from_llm(parser=output_parser, llm=chat)
    #         for _ in range(chances):
    #             try:
    #                 parsed_response = fixing_parser.parse(ai_resp_content)
    #             except:
    #                 continue
    #             else:
    #                 break
    #     return parsed_response.model_dump()
    # return ai_resp_content

    resp = __get_parsed_response(chat, messages, output_parser, chances)

    return resp
