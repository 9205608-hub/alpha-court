#!/usr/bin/env python3
"""Commander-side receipt extract + validate for the dispatch bridge.

CLI:
  python3 scripts/dispatch_receipt.py <raw_envelope.json> <schema.json> \\
      <receipt_out.json>

Extracts the worker receipt from a grok JSON envelope (structuredOutput, with
text concat-decode fallback), validates it against receipt.schema.json using a
stdlib-only structural checker, and on success writes a pretty-printed receipt.

Exit codes:
  0 — valid receipt written
  3 — receipt found but fails schema validation
  4 — no structured receipt found in the envelope
  2 — usage / I/O error

Dependency-free: stdlib json only (no jsonschema, no pip).
"""

from __future__ import annotations

import json
import sys
from typing import Any

# Schema keywords we understand at any level. Anything else is a hard error
# so we never silently pass on an unhandled construct.
_META_KEYS = frozenset({"$schema", "title", "description"})
_IMPLEMENTED_KEYS = frozenset(
    {
        "type",
        "required",
        "properties",
        "additionalProperties",
        "enum",
        "items",
    }
)


class ReceiptValidationError(Exception):
    """Raised with a path-named message on the first schema violation."""


def extract_receipt(envelope: dict[str, Any]) -> dict[str, Any] | None:
    """Pull the receipt dict from a worker JSON envelope.

    Prefer envelope['structuredOutput'] when it is a dict; otherwise fall back
    to successive json.raw_decode on envelope['text'], keeping the last dict.
    Returns None if no dict receipt is found.
    """
    receipt = envelope.get("structuredOutput")
    if isinstance(receipt, dict):
        return receipt

    # The text field is a concatenation of per-turn objects; only a fallback.
    decoder = json.JSONDecoder()
    text, idx, last = envelope.get("text", "") or "", 0, None
    while idx < len(text):
        try:
            obj, end = decoder.raw_decode(text, idx)
        except json.JSONDecodeError:
            break
        last, idx = obj, end
    if isinstance(last, dict):
        return last
    return None


def _check_unknown_constructs(schema: dict[str, Any], path: str) -> None:
    for key in schema:
        if key in _META_KEYS or key in _IMPLEMENTED_KEYS:
            continue
        raise ReceiptValidationError(
            f"receipt invalid: schema construct {key!r} at {path} "
            f"is not implemented by the commander-side checker"
        )


def _type_ok(value: Any, type_name: str) -> bool:
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "integer":
        # bool is a subclass of int in Python; reject it.
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return (isinstance(value, (int, float)) and not isinstance(value, bool))
    if type_name == "array":
        return isinstance(value, list)
    if type_name == "object":
        return isinstance(value, dict)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "null":
        return value is None
    raise ReceiptValidationError(
        f"receipt invalid: unsupported schema type {type_name!r}"
    )


def _validate(instance: Any, schema: dict[str, Any], path: str) -> None:
    """Validate instance against a JSON-schema fragment; raise on first failure."""
    _check_unknown_constructs(schema, path)

    if "type" in schema:
        expected = schema["type"]
        if isinstance(expected, list):
            if not any(_type_ok(instance, t) for t in expected):
                raise ReceiptValidationError(
                    f"receipt invalid: {path} has type "
                    f"{type(instance).__name__}, expected one of {expected}"
                )
        elif not _type_ok(instance, expected):
            raise ReceiptValidationError(
                f"receipt invalid: {path} has type "
                f"{type(instance).__name__}, expected {expected}"
            )

    if "enum" in schema:
        allowed = schema["enum"]
        if instance not in allowed:
            raise ReceiptValidationError(
                f"receipt invalid: {path} {instance!r} not in {allowed}"
            )

    if schema.get("type") == "object" or (
        "properties" in schema or "required" in schema or "additionalProperties" in schema
    ):
        if not isinstance(instance, dict):
            # type check above should have caught this when type is set;
            # if only object keywords are present, still require a dict.
            if "type" not in schema:
                raise ReceiptValidationError(
                    f"receipt invalid: {path} has type "
                    f"{type(instance).__name__}, expected object"
                )
        else:
            required = schema.get("required") or []
            for key in required:
                if key not in instance:
                    raise ReceiptValidationError(
                        f"receipt invalid: {path}.{key} is required but missing"
                        if path != "$"
                        else f"receipt invalid: {key} is required but missing"
                    )

            properties = schema.get("properties") or {}
            additional = schema.get("additionalProperties", True)

            for key, value in instance.items():
                child_path = f"{path}.{key}" if path != "$" else key
                if key in properties:
                    _validate(value, properties[key], child_path)
                elif additional is False:
                    raise ReceiptValidationError(
                        f"receipt invalid: unexpected key {key!r} at {path}"
                        if path != "$"
                        else f"receipt invalid: unexpected key {key!r}"
                    )
                elif isinstance(additional, dict):
                    _validate(value, additional, child_path)

    if "items" in schema:
        if not isinstance(instance, list):
            if "type" not in schema:
                raise ReceiptValidationError(
                    f"receipt invalid: {path} has type "
                    f"{type(instance).__name__}, expected array"
                )
        else:
            items_schema = schema["items"]
            if not isinstance(items_schema, dict):
                raise ReceiptValidationError(
                    f"receipt invalid: schema items at {path} must be an object"
                )
            for i, item in enumerate(instance):
                _validate(item, items_schema, f"{path}[{i}]")


def validate_receipt(receipt: dict[str, Any], schema: dict[str, Any]) -> None:
    """Validate a receipt dict against the loaded schema. Raises on failure."""
    _validate(receipt, schema, "$")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 3:
        print(
            "usage: dispatch_receipt.py <raw_envelope.json> "
            "<schema.json> <receipt_out.json>",
            file=sys.stderr,
        )
        return 2

    raw_path, schema_path, receipt_path = args

    try:
        with open(raw_path, encoding="utf-8") as f:
            envelope = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"failed to read envelope {raw_path}: {exc}", file=sys.stderr)
        return 2

    if not isinstance(envelope, dict):
        print(
            f"no structured receipt found in envelope; inspect {raw_path}",
            file=sys.stderr,
        )
        return 4

    receipt = extract_receipt(envelope)
    if not isinstance(receipt, dict):
        print(
            f"no structured receipt found in envelope; inspect {raw_path}",
            file=sys.stderr,
        )
        return 4

    try:
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"failed to read schema {schema_path}: {exc}", file=sys.stderr)
        return 2

    try:
        validate_receipt(receipt, schema)
    except ReceiptValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 3

    with open(receipt_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # Summary lines (session is printed by dispatch.sh from the envelope).
    print(f"[dispatch] status:   {receipt.get('status', '?')}")
    print(f"[dispatch] branch:   {receipt.get('branch', '?')}")
    print(f"[dispatch] commit:   {receipt.get('commit', '?')}")
    print(f"[dispatch] worktree: {receipt.get('worktree_path', '?')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
