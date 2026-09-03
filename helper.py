import os
import re
import json
from typing import List, Tuple, Union
from pathlib import Path
import pandas as pd
from pygments import highlight
from pygments.lexers import CypherLexer, JsonLexer
from pygments.formatters import TerminalFormatter

select_keys = lambda dct, keys: {k: v for k, v in dct.items() if k in keys}

deselect_keys = lambda dct, keys: {k: v for k, v in dct.items() if k not in keys}

return_unique = lambda lst: list(dict.fromkeys(lst))

def colorize(query):
    return highlight(query, CypherLexer(), TerminalFormatter())

def print_cypher_query(query):
    print(highlight(query, CypherLexer(), TerminalFormatter()))

def colorize_json(data):
    formatted_json = json.dumps(data, indent=4)
    return highlight(formatted_json, JsonLexer(), TerminalFormatter())

def print_json(data):
    formatted_json = json.dumps(data, indent=4)
    print(highlight(formatted_json, JsonLexer(), TerminalFormatter()))

def read_excel_as_dict(filepath):
    filename = Path(filepath).name
    sheet_names = pd.ExcelFile(filepath, engine="openpyxl").sheet_names
    res_dict = {}
    for sheet_name in sheet_names:
        curr_df = pd.read_excel(filepath, sheet_name=sheet_name)
        res_dict[sheet_name] = curr_df
    print(f"Filename: \"{filename}\"  | Sheets: \"{', '.join(sheet_names)}\"")
    return res_dict


def save_df_dict_to_excel(df_dict, output_filepath):
    with pd.ExcelWriter(output_filepath, engine="openpyxl") as writer:
        for sheet_name, df in df_dict.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    return output_filepath


def get_filepath_list(directory):
    path = Path(directory)
    return [str(file) for file in path.rglob("*") if file.is_file()]


def load_json(filepath):
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def dump_json(py_data, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(json.dumps(py_data, indent=4))
    return filepath


def update_dict(dct, k, v):
    if k not in dct:
        dct[k] = [v]
    else:
        dct[k].append(v)
    return dct


def cluster_keys_with_same_values(d):
    dct = {}
    for comp, group_id in d.items():
        dct = update_dict(dct, group_id, comp)
    return dct


def extract_code_blocks(markdown):
    blocks = []
    CODEBLOCK_RE = re.compile(
        r"```(?:\s*)([^\s`]+)?[^\n]*\r?\n(.*?)\r?\n?```", re.DOTALL
    )
    for m in CODEBLOCK_RE.finditer(markdown):
        lang = (m.group(1) or "").strip()
        code = m.group(2)
        blocks.append((code, lang))
    return blocks


def json_to_python_syntax(json_string: str) -> Union[list, dict]:
    json_string = re.sub(r"\btrue\b", "True", json_string)
    json_string = re.sub(r"\bfalse\b", "False", json_string)
    json_string = re.sub(r"\bnull\b", "None", json_string)
    return eval(json_string)
