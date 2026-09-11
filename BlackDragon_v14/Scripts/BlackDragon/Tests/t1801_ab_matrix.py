#!/usr/bin/env python3
"""Generate/verify T18 Fluid OFF->0->1->2->3 acceptance sets and parse evidence logs."""
from __future__ import annotations
import argparse
import json
import re
import tempfile
from pathlib import Path

VARIANTS = [
    ("off", False, 0),
    ("shadow", True, 0),
    ("dca", True, 1),
    ("dca_py", True, 2),
    ("dca_py_rh", True, 3),
]
TARGET_KEYS = ("UseFluidRegime", "FluidMode")


def _bool_text(v: bool) -> str:
    return "true" if v else "false"


def parse_set(text: str):
    return text.splitlines(keepends=True)


def split_assignment(line: str):
    raw = line.rstrip("\r\n")
    ending = line[len(raw):]
    if "=" not in raw or raw.lstrip().startswith(";"):
        return None
    key, rhs = raw.split("=", 1)
    key = key.strip()
    return key, rhs, ending


def rewrite_value(line: str, key: str, value: str) -> str:
    parsed = split_assignment(line)
    if parsed is None or parsed[0] != key:
        return line
    _, rhs, ending = parsed
    parts = rhs.split("||")
    parts[0] = value
    return f"{key}={'||'.join(parts)}{ending}"


def values(lines):
    out = {}
    for line in lines:
        parsed = split_assignment(line)
        if parsed:
            key, rhs, _ = parsed
            out[key] = rhs.split("||", 1)[0]
    return out


def generate_variants(baseline_text: str):
    base = parse_set(baseline_text)
    base_values = values(base)
    missing = [k for k in TARGET_KEYS if k not in base_values]
    if missing:
        raise ValueError("baseline missing Fluid keys: " + ", ".join(missing))
    result = {}
    for name, use, mode in VARIANTS:
        lines = list(base)
        lines = [rewrite_value(x, "UseFluidRegime", _bool_text(use)) for x in lines]
        lines = [rewrite_value(x, "FluidMode", str(mode)) for x in lines]
        result[name] = "".join(lines)
    return result


def canonical_non_target(text: str):
    rows = []
    for line in parse_set(text):
        parsed = split_assignment(line)
        if parsed and parsed[0] in TARGET_KEYS:
            key, rhs, ending = parsed
            parts = rhs.split("||")
            parts[0] = "<FLUID>"
            rows.append(f"{key}={'||'.join(parts)}{ending}")
        else:
            rows.append(line)
    return "".join(rows)


def verify_matrix(matrix):
    expected = {name: (_bool_text(use), str(mode)) for name, use, mode in VARIANTS}
    if set(matrix) != set(expected):
        raise AssertionError("variant names mismatch")
    baseline = None
    for name, text in matrix.items():
        v = values(parse_set(text))
        if (v.get("UseFluidRegime"), v.get("FluidMode")) != expected[name]:
            raise AssertionError(f"{name} Fluid values mismatch: {v}")
        c = canonical_non_target(text)
        if baseline is None:
            baseline = c
        elif c != baseline:
            raise AssertionError(f"{name} changed non-Fluid set content")


def parse_log(text: str):
    out = {
        "ready": len(re.findall(r"Fluid READY", text)),
        "heartbeat": len(re.findall(r"Fluid HEARTBEAT", text)),
        "dca_block_lines": len(re.findall(r"Fluid DCA BLOCK", text)),
        "py_block_lines": len(re.findall(r"Fluid PY BLOCK", text)),
        "rh_block_lines": len(re.findall(r"Fluid RH BLOCK", text)),
        "latest_counters": None,
    }
    matches = re.findall(r"DCA=(\d+)/(\d+)\s+PY=(\d+)/(\d+)\s+RH=(\d+)/(\d+)", text)
    if matches:
        d = tuple(int(x) for x in matches[-1])
        out["latest_counters"] = {
            "dca_eval": d[0], "dca_block": d[1],
            "py_eval": d[2], "py_block": d[3],
            "rh_eval": d[4], "rh_block": d[5],
        }
    return out


def self_test():
    sample = (
        "; baseline\n"
        "UseFluidRegime=false||false||0||true||N\n"
        "FluidMode=0||0||0||3||N\n"
        "FluidFastWindow=5||5||1||30||N\n"
        "RecoveryMode_=1||1||0||1||N\n"
    )
    matrix = generate_variants(sample)
    verify_matrix(matrix)
    parsed = parse_log(
        "Fluid READY | mode=DCA+PY+RH | counters(eval/block) DCA=0/0 PY=0/0 RH=0/0\n"
        "Fluid PY BLOCK | dir=BUY | counters(eval/block) DCA=10/2 PY=7/3 RH=4/1\n"
        "Fluid HEARTBEAT | mode=DCA+PY+RH | counters(eval/block) DCA=20/5 PY=11/4 RH=8/2\n"
    )
    assert parsed["ready"] == 1 and parsed["heartbeat"] == 1
    assert parsed["py_block_lines"] == 1
    assert parsed["latest_counters"]["rh_block"] == 2
    print("T18.01 A/B harness: 5 variants PASS; parser PASS")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--baseline", type=Path)
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--logs", type=Path, help="file or directory of tester/journal logs")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return 0

    if not args.baseline or not args.out_dir:
        ap.error("--baseline and --out-dir are required unless --self-test")
    baseline = args.baseline.read_text(encoding="utf-8-sig")
    matrix = generate_variants(baseline)
    verify_matrix(matrix)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"baseline": str(args.baseline), "variants": {}}
    for name, use, mode in VARIANTS:
        path = args.out_dir / f"t1801-fluid-{name}.set"
        path.write_text(matrix[name], encoding="utf-8")
        manifest["variants"][name] = {
            "path": str(path), "UseFluidRegime": use, "FluidMode": mode
        }

    evidence = {}
    if args.logs:
        paths = [args.logs] if args.logs.is_file() else sorted(p for p in args.logs.rglob("*") if p.is_file())
        for p in paths:
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            evidence[str(p)] = parse_log(text)
    manifest["evidence"] = evidence
    (args.out_dir / "t1801-ab-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"T18.01 A/B matrix generated: {len(VARIANTS)} variants; non-Fluid settings byte-equivalent")
    if args.logs:
        print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
