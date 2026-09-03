# IMAGE INPUT
import os
from pathlib import Path
from typing import Union, Optional, Literal, List, Dict, Set
from base64 import b64encode
from mimetypes import guess_type
import fitz
from langchain_core.prompts import (
    PromptTemplate,
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    AIMessagePromptTemplate,
)
from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

get_full_path = lambda path: os.path.normpath(Path(path).absolute()).replace("\\", "/")


def local_image_to_data_url(image_path):
    # Guess the MIME type of the image based on the file extension
    mime_type, _ = guess_type(image_path)
    if mime_type is None:
        if image_path.endswith("webp"):
            mime_type = "image/webp"
        else:
            mime_type = "application/octet-stream"  # Default MIME type if none is found

    # Read and encode the image file
    with open(image_path, "rb") as image_file:
        base64_encoded_data = b64encode(image_file.read()).decode("utf-8")

    # Construct the data URL
    return f"data:{mime_type};base64,{base64_encoded_data}"


def image_path_to_prompt(image_path):
    return {
        "type": "image_url",
        "image_url": {"url": local_image_to_data_url(image_path)},
    }


def image_to_prompt(image_source: Optional[Union[str, list[str]]] = None):
    if image_source is None:
        return []
    elif isinstance(image_source, str):
        return [image_path_to_prompt(image_path=image_source)]
    else:
        return [
            image_path_to_prompt(image_path=image_path) for image_path in image_source
        ]


def pdf_to_images(pdf_filepath, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # print(pdf_filepath)
    pdf_name = os.path.splitext(os.path.basename(pdf_filepath))[0]
    pdf_output_dir = os.path.join(output_dir, pdf_name)
    os.makedirs(pdf_output_dir, exist_ok=True)

    pdf_document = fitz.open(pdf_filepath)
    image_paths = []

    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        pix = page.get_pixmap()
        max_num_chars = len(str(len(pdf_document)))
        page_num_str = str(page_num + 1)
        page_num_str = (max_num_chars - len(page_num_str)) * "0" + page_num_str
        image_filename = f"{pdf_name}_page_{page_num_str}.png"
        pdf_output_dir = get_full_path(pdf_output_dir)
        # image_path = os.path.normpath(os.path.join(pdf_output_dir, image_filename))
        image_path = str(Path(pdf_output_dir) / image_filename).replace("\\", "/")
        pix.save(image_path)
        image_paths.append(image_path)

    pdf_document.close()
    return image_paths


def pdf_to_image_filepath_list(
    pdf_filepath: Optional[str] = None,
    page_range: Optional[tuple[int, int]] = None,
    output_dir: str = "../output",
):
    if pdf_filepath is None:
        return None
    image_paths = pdf_to_images(pdf_filepath, output_dir)
    if page_range:
        start_page_num, end_page_num = page_range
        image_paths = image_paths[start_page_num - 1 : end_page_num]
    return tuple(image_paths)


def make_prompt(prompt, image_source=None, pydantic_object=None, strict=True, **kwargs):

    if image_source is None:
        image_data = []
    else:
        image_data = image_to_prompt(image_source)

    mapped_kwargs = {}
    prompt_template = PromptTemplate(template=prompt)
    input_variables = prompt_template.input_variables

    # Defining output parser
    if pydantic_object is None:
        output_parser = None
        format_instructions = ""
    else:
        if strict:
            output_parser = PydanticOutputParser(pydantic_object=pydantic_object)
        else:
            output_parser = JsonOutputParser(pydantic_object=pydantic_object)
        if "format_instructions" not in input_variables:
            prompt += "\n\n{format_instructions}"
            prompt_template = PromptTemplate(template=prompt)
            input_variables = prompt_template.input_variables

        format_instructions = output_parser.get_format_instructions()

    for var in input_variables:
        if var == "format_instructions":
            if output_parser:
                format_instructions = output_parser.get_format_instructions()
                # print(format_instructions)
                mapped_kwargs[var] = format_instructions
            else:
                mapped_kwargs[var] = ""
        elif var in kwargs:
            mapped_kwargs[var] = kwargs[var]
        else:
            raise Exception(f"InvalidKwargsInput: '{var}' not in kwargs")

    formatted_prompt = prompt_template.format(**mapped_kwargs)

    content = [{"type": "text", "text": formatted_prompt}] + image_data

    human_message = HumanMessage(content=content)

    message_dict = {
        "message": human_message,
        "messages": [human_message],
        "output_parser": output_parser,
    }
    return message_dict
