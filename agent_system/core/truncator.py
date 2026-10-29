"""Structural and UTF-8 safe payload truncator for context management."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Union


def _json_bytes(obj: Any) -> int:
    """Compute UTF-8 byte length of a JSON-serialized object."""
    return len(json.dumps(obj, ensure_ascii=False).encode("utf-8"))


class StructuralTruncator:
    """Safe truncator ensuring UTF-8 integrity and JSON validity within byte limits."""

    DEFAULT_MAX_BYTES = 3072  # 3KB context limit

    @classmethod
    def truncate_text(
        cls,
        text: str,
        max_bytes: int = DEFAULT_MAX_BYTES,
        suffix: str = "\n...[TRUNCATED]",
    ) -> str:
        """Truncate text safely preserving multi-byte UTF-8 character boundaries.

        Prefers breaking at line boundaries when feasible.
        """
        encoded = text.encode("utf-8")
        if len(encoded) <= max_bytes:
            return text

        suffix_bytes = suffix.encode("utf-8")
        if len(suffix_bytes) >= max_bytes:
            truncated = suffix_bytes[:max_bytes].decode("utf-8", errors="ignore")
            while len(truncated.encode("utf-8")) > max_bytes and truncated:
                truncated = truncated[:-1]
            return truncated

        target_bytes = max_bytes - len(suffix_bytes)
        truncated_raw = encoded[:target_bytes].decode("utf-8", errors="ignore")

        # Try clean newline break if reasonably close to the end
        last_newline = truncated_raw.rfind("\n")
        if last_newline != -1 and last_newline >= len(truncated_raw) * 0.7:
            truncated_raw = truncated_raw[:last_newline]

        # Preserve markdown code block syntax: if unclosed code fence is detected, close it
        if truncated_raw.count("```") % 2 == 1:
            close_fence = "\n```"
            adjusted_target = target_bytes - len(close_fence.encode("utf-8"))
            if adjusted_target > 0:
                truncated_raw = encoded[:adjusted_target].decode("utf-8", errors="ignore")
                last_nl = truncated_raw.rfind("\n")
                if last_nl != -1 and last_nl >= len(truncated_raw) * 0.7:
                    truncated_raw = truncated_raw[:last_nl]
                truncated_raw += close_fence
            else:
                truncated_raw = ""

        result = truncated_raw + suffix
        # Ensure strict compliance
        while len(result.encode("utf-8")) > max_bytes and len(truncated_raw) > 0:
            truncated_raw = truncated_raw[:-1]
            if truncated_raw.count("```") % 2 == 1:
                candidate = truncated_raw + "\n```" + suffix
                if len(candidate.encode("utf-8")) <= max_bytes:
                    result = candidate
                    break
            result = truncated_raw + suffix
        return result

    @classmethod
    def truncate_json(
        cls,
        data: Union[Dict[str, Any], List[Any], Any],
        max_bytes: int = DEFAULT_MAX_BYTES,
    ) -> Union[Dict[str, Any], List[Any], Any]:
        """Truncate JSON data structurally so the output remains valid, parseable JSON within max_bytes."""
        if _json_bytes(data) <= max_bytes:
            return data

        if isinstance(data, list):
            trimmed_list: List[Any] = []
            for item in data:
                candidate = trimmed_list + [item, {"_truncated": f"{len(data) - len(trimmed_list)} omitted"}]
                if _json_bytes(candidate) > max_bytes:
                    break
                trimmed_list.append(item)
            if len(trimmed_list) < len(data):
                indicator = {"_truncated": f"{len(data) - len(trimmed_list)} omitted"}
                while trimmed_list and _json_bytes(trimmed_list + [indicator]) > max_bytes:
                    trimmed_list.pop()
                if _json_bytes(trimmed_list + [indicator]) <= max_bytes:
                    trimmed_list.append(indicator)
            if _json_bytes(trimmed_list) > max_bytes:
                return []
            return trimmed_list

        if isinstance(data, dict):
            trimmed_dict: Dict[str, Any] = {}
            keys = list(data.keys())
            for k in keys:
                v = data[k]
                candidate = dict(trimmed_dict)
                candidate[k] = v
                if _json_bytes(candidate) > max_bytes:
                    if isinstance(v, (dict, list)):
                        budget = max_bytes - _json_bytes(trimmed_dict) - 32
                        if budget > 64:
                            sub = cls.truncate_json(v, max_bytes=budget)
                            candidate[k] = sub
                            if _json_bytes(candidate) <= max_bytes:
                                trimmed_dict[k] = sub
                                continue
                    break
                trimmed_dict[k] = v

            omitted = len(keys) - len(trimmed_dict)
            if omitted > 0:
                trimmed_dict["_omitted"] = f"{omitted} keys"
                # If adding indicator exceeds budget, pop items until it fits
                while _json_bytes(trimmed_dict) > max_bytes and len(trimmed_dict) > 1:
                    keys_to_remove = [k for k in trimmed_dict if k != "_omitted"]
                    if not keys_to_remove:
                        break
                    del trimmed_dict[keys_to_remove[-1]]

            # Final safety check: if still exceeding, degrade to minimal dict
            if _json_bytes(trimmed_dict) > max_bytes:
                for cand in [{"_truncated": True}, {}]:
                    if _json_bytes(cand) <= max_bytes:
                        return cand
                return {}

            return trimmed_dict

        # Fallback for scalar types
        return cls.truncate_text(str(data), max_bytes=max_bytes)

    @classmethod
    def truncate_payload(cls, raw: str, max_bytes: int = DEFAULT_MAX_BYTES) -> str:
        """Autodetect JSON vs plain text and safely truncate within byte limit."""
        if len(raw.encode("utf-8")) <= max_bytes:
            return raw

        try:
            parsed = json.loads(raw)
            is_json = True
        except (json.JSONDecodeError, TypeError):
            is_json = False
            parsed = None

        if is_json:
            truncated_obj = cls.truncate_json(parsed, max_bytes=max_bytes)
            res = json.dumps(truncated_obj, ensure_ascii=False)
            if len(res.encode("utf-8")) <= max_bytes:
                return res

            # Ensure valid minimal JSON fallback under tight byte budgets
            if isinstance(parsed, dict):
                fallbacks = ['{"_truncated":true}', '{}']
            elif isinstance(parsed, list):
                fallbacks = ['[{"_truncated":true}]', '[]']
            elif isinstance(parsed, str):
                fallbacks = ['""']
            else:
                fallbacks = ['null', '0', '{}']

            for cand in fallbacks:
                if len(cand.encode("utf-8")) <= max_bytes:
                    return cand

            if max_bytes >= 2:
                return "{}" if isinstance(parsed, dict) else "[]"
            return ""

        return cls.truncate_text(raw, max_bytes=max_bytes)
