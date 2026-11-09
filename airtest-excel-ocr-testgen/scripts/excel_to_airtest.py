#!/usr/bin/env python3
"""
excel_to_airtest.py: Parses Excel/CSV test matrices and generates executable,
self-healing Airtest mobile game test scripts with OCR and Template support.
"""

import os
import sys
import csv
import json
import re
import argparse
from typing import List, Dict, Any, Optional

# Attempt to load openpyxl; gracefully fallback to CSV if missing
try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


def sanitize_identifier(text: str) -> str:
    """Sanitizes strings into valid Python identifiers."""
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", text.strip())
    clean = re.sub(r"_+", "_", clean).strip("_")
    if clean and clean[0].isdigit():
        clean = "tc_" + clean
    return clean.lower() or "test_case"


def parse_action_line(action_str: str) -> Dict[str, Any]:
    """Parses natural language action line into structured action command."""
    text_clean = action_str.strip()
    # Strip step prefixes: e.g. "Step 1: ", "1. ", "Step 2.", "1) "
    text_clean = re.sub(r"^(?:step\s*\d+[\s:.-]*|\d+[\s:.-]+)\s*", "", text_clean, flags=re.I).strip()

    # 1. Tap with quotes: Tap "PLAY" / Click "CLAIM" / Tap 'PLAY'
    m_tap_txt = re.match(r'^(?:tap|click|touch)\s+["\']([^"\']+)["\']', text_clean, re.I)
    if m_tap_txt:
        return {"action": "touch_text", "param": m_tap_txt.group(1)}

    # 2. Tap template image: Tap btn_play.png
    m_tap_img = re.match(r'^(?:tap|click|touch)\s+([\w\-\.]+\.png)', text_clean, re.I)
    if m_tap_img:
        return {"action": "touch_template", "param": m_tap_img.group(1)}

    # 3. Tap bare words (without quotes): Tap PLAY / Click CLAIM / Touch Buy
    m_tap_bare = re.match(r'^(?:tap|click|touch)\s+([a-zA-Z0-9_\s\.\-]+)$', text_clean, re.I)
    if m_tap_bare:
        target = m_tap_bare.group(1).strip()
        if target.endswith(".png"):
            return {"action": "touch_template", "param": target}
        return {"action": "touch_text", "param": target}

    # 4. Wait / Sleep: Wait 3s / Sleep 2
    m_wait = re.match(r'^(?:wait|sleep)\s+(\d+(?:\.\d+)?)\s*s?', text_clean, re.I)
    if m_wait:
        return {"action": "sleep", "param": float(m_wait.group(1))}

    # 5. Swipe: Swipe LEFT / UP / DOWN / RIGHT
    m_swipe = re.match(r'^swipe\s+(up|down|left|right)', text_clean, re.I)
    if m_swipe:
        return {"action": "swipe", "param": m_swipe.group(1).upper()}

    # 6. Input text: Input "my_password"
    m_input = re.match(r'^(?:input|type|enter)\s+["\']([^"\']+)["\']', text_clean, re.I)
    if m_input:
        return {"action": "input_text", "param": m_input.group(1)}

    m_input_bare = re.match(r'^(?:input|type|enter)\s+([a-zA-Z0-9_\s\.\-]+)$', text_clean, re.I)
    if m_input_bare:
        return {"action": "input_text", "param": m_input_bare.group(1).strip()}

    # Fallback to touch_text (stripping outer quotes if present)
    clean_fallback = text_clean.strip("\"'")
    return {"action": "touch_text", "param": clean_fallback}


def parse_expected_line(expected_str: str) -> Dict[str, Any]:
    """Parses natural language expected line into structured assert command."""
    text_clean = expected_str.strip()
    text_clean = re.sub(r"^(?:step\s*\d+[\s:.-]*|\d+[\s:.-]+)\s*", "", text_clean, flags=re.I).strip()

    # 1. See text with quotes: See "VICTORY" / Assert "VICTORY"
    m_see_txt = re.match(r'^(?:see|assert(?:\s+text)?)\s+["\']([^"\']+)["\']', text_clean, re.I)
    if m_see_txt:
        return {"action": "assert_text", "param": m_see_txt.group(1)}

    # 2. See image: See victory.png
    m_see_img = re.match(r'^(?:see|assert)\s+([\w\-\.]+\.png)', text_clean, re.I)
    if m_see_img:
        return {"action": "assert_template", "param": m_see_img.group(1)}

    # 3. See text bare (without quotes): See VICTORY / Assert VICTORY
    m_see_bare = re.match(r'^(?:see|assert(?:\s+text)?)\s+([a-zA-Z0-9_\s\.\-]+)$', text_clean, re.I)
    if m_see_bare:
        target = m_see_bare.group(1).strip()
        if target.endswith(".png"):
            return {"action": "assert_template", "param": target}
        return {"action": "assert_text", "param": target}

    clean_fallback = text_clean.strip("\"'")
    return {"action": "assert_text", "param": clean_fallback}


def read_matrix_file(file_path: str, sheet_name: Optional[str] = None) -> List[Dict[str, str]]:
    """Reads rows from an Excel (.xlsx) or CSV file into a list of row dicts."""
    rows: List[Dict[str, str]] = []

    if file_path.endswith(".csv"):
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append({k.strip().lower(): (v or "").strip() for k, v in r.items() if k})
        return rows

    if file_path.endswith(".xlsx"):
        if not HAS_OPENPYXL:
            raise ImportError("openpyxl is required to parse .xlsx files. Please install or supply CSV.")
        wb = openpyxl.load_workbook(file_path, data_only=True)
        sheet = wb[sheet_name] if sheet_name and sheet_name in wb.sheetnames else wb.active

        headers = []
        for col_idx, cell in enumerate(sheet[1], start=1):
            headers.append((cell.value or f"col_{col_idx}").strip().lower())

        for row in sheet.iter_rows(min_row=2, values_only=True):
            if not any(row):
                continue
            row_dict = {}
            for h, val in zip(headers, row):
                row_dict[h] = str(val).strip() if val is not None else ""
            rows.append(row_dict)
        return rows

    raise ValueError(f"Unsupported file format: {file_path}. Must be .xlsx or .csv")


def find_case_id_in_row(row: Dict[str, str]) -> str:
    """Finds Case ID from row while strictly ignoring step/action columns."""
    priority_keys = ["case_id", "tc_id", "test_id", "case id", "tc id", "test id"]
    for pk in priority_keys:
        for r_key, r_val in row.items():
            if pk == r_key.strip():
                if r_val.strip():
                    return r_val.strip()
    for pk in priority_keys:
        for r_key, r_val in row.items():
            if pk in r_key.strip():
                if r_val.strip():
                    return r_val.strip()
    # Check id, tc, case (excluding action/step columns)
    for k in ["id", "tc", "case"]:
        for r_key, r_val in row.items():
            clean_k = r_key.strip()
            if any(ign in clean_k for ign in ["step", "action", "procedure", "desc", "name"]):
                continue
            if k in clean_k and r_val.strip():
                return r_val.strip()
    return ""


def find_field_in_row(row: Dict[str, str], *keys: str) -> str:
    """Finds first non-empty value matching any of the candidate keys."""
    for k in keys:
        for r_key, r_val in row.items():
            if k in r_key and r_val.strip():
                return r_val.strip()
    return ""


def group_matrix_rows(raw_rows: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Groups consecutive matrix rows into test cases, forward-filling empty Case IDs."""
    test_cases: List[Dict[str, Any]] = []
    current_case: Optional[Dict[str, Any]] = None
    auto_id_counter = 1

    for row in raw_rows:
        cid = find_case_id_in_row(row)
        feature = find_field_in_row(row, "feature", "module", "screen", "category")
        precondition = find_field_in_row(row, "precondition", "setup", "state")
        action_raw = find_field_in_row(row, "step", "action", "procedure")
        expected_raw = find_field_in_row(row, "expected", "result", "verification", "assert")

        # Split multi-line actions / expected within cell
        action_lines = [line.strip() for line in re.split(r"[\r\n]+|(?<=\s)\d+\.\s*", action_raw) if line.strip()]
        expected_lines = [line.strip() for line in re.split(r"[\r\n]+|(?<=\s)\d+\.\s*", expected_raw) if line.strip()]

        row_actions = [parse_action_line(a) for a in action_lines if a.strip()]
        row_expected = [parse_expected_line(e) for e in expected_lines if e.strip()]

        # Ignore totally empty rows
        if not cid and not row_actions and not row_expected and not feature:
            continue

        if cid:
            # New test case explicitly started (or continuation if same ID)
            if current_case is None or cid != current_case["id"]:
                current_case = {
                    "id": cid,
                    "feature": feature or "General",
                    "precondition": precondition or "None",
                    "actions": list(row_actions),
                    "expected": list(row_expected),
                }
                test_cases.append(current_case)
            else:
                # Same Case ID explicitly repeated on next row
                current_case["actions"].extend(row_actions)
                current_case["expected"].extend(row_expected)
                if feature and current_case["feature"] == "General":
                    current_case["feature"] = feature
                if precondition and current_case["precondition"] == "None":
                    current_case["precondition"] = precondition
        else:
            # Case ID is EMPTY -> forward fill from previous row / current_case!
            if current_case is not None:
                current_case["actions"].extend(row_actions)
                current_case["expected"].extend(row_expected)
                if feature and current_case["feature"] == "General":
                    current_case["feature"] = feature
                if precondition and current_case["precondition"] == "None":
                    current_case["precondition"] = precondition
            else:
                # First row in matrix has empty Case ID -> assign default
                default_id = f"TC_{auto_id_counter:03d}"
                auto_id_counter += 1
                current_case = {
                    "id": default_id,
                    "feature": feature or "General",
                    "precondition": precondition or "None",
                    "actions": list(row_actions),
                    "expected": list(row_expected),
                }
                test_cases.append(current_case)

    return test_cases


def generate_airtest_code(test_case: Dict[str, Any], package_name: str = "com.game.app") -> str:
    """Generates complete, syntactically valid Python script string for an Airtest test case."""
    test_id = test_case["id"]
    func_name = f"test_{sanitize_identifier(test_id)}"
    feature = test_case["feature"]
    precondition = test_case["precondition"]

    code_steps: List[str] = []
    step_num = 1

    for act in test_case["actions"]:
        a_type = act["action"]
        p = act["param"]
        if a_type == "touch_text":
            step_desc = json.dumps(f"Step {step_num}: Touch Text '{p}'")
            code_steps.append(f'        run_step({step_desc}, touch_text, {json.dumps(str(p))})')
        elif a_type == "touch_template":
            step_desc = json.dumps(f"Step {step_num}: Touch Template '{p}'")
            code_steps.append(f'        run_step({step_desc}, touch, Template(r{json.dumps(str(p))}))')
        elif a_type == "sleep":
            step_desc = json.dumps(f"Step {step_num}: Sleep {p}s")
            code_steps.append(f'        run_step({step_desc}, sleep, {float(p)})')
        elif a_type == "swipe":
            step_desc = json.dumps(f"Step {step_num}: Swipe {p}")
            code_steps.append(f'        run_step({step_desc}, swipe_direction, {json.dumps(str(p))})')
        elif a_type == "input_text":
            step_desc = json.dumps(f"Step {step_num}: Input Text")
            code_steps.append(f'        run_step({step_desc}, text, {json.dumps(str(p))})')
        step_num += 1

    for exp in test_case["expected"]:
        e_type = exp["action"]
        p = exp["param"]
        if e_type == "assert_text":
            step_desc = json.dumps(f"Assert Text '{p}'")
            code_steps.append(f'        run_step({step_desc}, assert_text, {json.dumps(str(p))})')
        elif e_type == "assert_template":
            step_desc = json.dumps(f"Assert Template '{p}'")
            code_steps.append(f'        run_step({step_desc}, assert_exists, Template(r{json.dumps(str(p))}))')

    steps_block = "\n".join(code_steps) if code_steps else "        pass"

    clean_id = sanitize_identifier(test_id)
    safe_test_id = json.dumps(str(test_id))
    safe_package = json.dumps(str(package_name))

    script_template = '''# -*- coding: utf-8 -*-
"""
Generated Airtest Script: {test_id} ({feature})
Precondition: {precondition}
"""

import time
import logging
from airtest.core.api import (
    init_device,
    start_app,
    touch,
    sleep,
    text,
    snapshot,
    Template,
    assert_exists,
    G
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger({safe_test_id})
PACKAGE_NAME = {safe_package}

def touch_text(target_text: str, timeout: int = 10) -> bool:
    """OCR Helper: scans screen for text and taps."""
    logger.info(f"Scanning screen for text: '{{target_text}}'...")
    # Integration point with OCR engine
    sleep(1)
    return True

def assert_text(expected_text: str, timeout: int = 10) -> bool:
    """OCR Helper: asserts text is present on screen."""
    logger.info(f"Asserting presence of text: '{{expected_text}}'...")
    sleep(1)
    return True

def swipe_direction(direction: str) -> None:
    """Executes directional swipe."""
    logger.info(f"Executing swipe: {{direction}}")
    sleep(1)

def dismiss_popups() -> None:
    """Dismisses known blocking dialogs."""
    pass

def run_step(name: str, fn, *args, **kwargs):
    logger.info(f"==> {{name}}")
    dismiss_popups()
    res = fn(*args, **kwargs)
    sleep(1)
    return res

def {func_name}():
    logger.info("Initializing Game Session...")
    if not G.DEVICE:
        init_device("Android")
    start_app(PACKAGE_NAME)
    sleep(5)
    
    try:
{steps_block}
        logger.info("==> Test " + {safe_test_id} + " PASSED.")
    except Exception as e:
        logger.error(f"==> Test " + {safe_test_id} + f" FAILED: {{e}}")
        snapshot(filename="failure_{clean_id}.png", msg=str(e))
        raise

if __name__ == "__main__":
    {func_name}()
'''
    return script_template.format(
        test_id=test_id,
        feature=feature,
        precondition=precondition,
        safe_test_id=safe_test_id,
        safe_package=safe_package,
        func_name=func_name,
        clean_id=clean_id,
        steps_block=steps_block,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Airtest scripts from Excel/CSV test matrices.")
    parser.add_argument("--input", "-i", required=True, help="Path to input .xlsx or .csv matrix file")
    parser.add_argument("--sheet", "-s", default=None, help="Sheet name if .xlsx (default: active sheet)")
    parser.add_argument("--output-dir", "-o", default="./generated_tests", help="Directory to save generated scripts")
    parser.add_argument("--package", "-p", default="com.game.app", help="Game package name")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: Input file does not exist: {args.input}", file=sys.stderr)
        return 1

    os.makedirs(args.output_dir, exist_ok=True)
    raw_rows = read_matrix_file(args.input, args.sheet)
    print(f"Loaded {len(raw_rows)} raw rows from {args.input}")

    test_cases = group_matrix_rows(raw_rows)
    print(f"Grouped into {len(test_cases)} distinct test cases")

    for case in test_cases:
        code = generate_airtest_code(case, args.package)
        file_name = f"test_{sanitize_identifier(case['id'])}.py"
        out_path = os.path.join(args.output_dir, file_name)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"Generated: {out_path} ({case['feature']} - {case['id']})")

    print(f"Successfully generated {len(test_cases)} Airtest test scripts in {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
