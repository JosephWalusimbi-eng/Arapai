#!/usr/bin/env python
"""
ADTC benchmark CLI — measures tokens/sec, TTFT, peak RSS, latency.

Usage (from project root, venv active):
    python benchmark.py
    python benchmark.py --tier light --max-tokens 128
"""
import argparse
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.llm_engine import benchmark_inference, get_model_path
from backend.math_engine import solve
from backend.memory_utils import memory_summary, reset_peak_rss


DEFAULT_PROMPT = (
    "User: A student connects a thin, long wire and the bulb is dimmer than with a "
    "short thick wire. Explain why.\nAssistant:"
)


def run_math_check():
    expr = "(48/6)+7*2"
    result = solve(expr)
    return {"expression": expr, "result": result, "ok": result == 22.0}


def main():
    parser = argparse.ArgumentParser(description="Arapai ADTC inference benchmark")
    parser.add_argument("--tier", default="light", choices=["light", "standard", "advanced"])
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--no-stream", action="store_true")
    parser.add_argument("--json-out", default="benchmark_results.json")
    args = parser.parse_args()

    try:
        get_model_path(args.tier)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    reset_peak_rss()
    math = run_math_check()

    print(f"Running benchmark — tier={args.tier}, max_tokens={args.max_tokens}")
    results = benchmark_inference(
        prompt=DEFAULT_PROMPT,
        max_tokens=args.max_tokens,
        model_tier=args.tier,
        stream=not args.no_stream,
    )
    results["math_engine"] = math
    results["memory"] = memory_summary()

    print("\n=== Arapai ADTC Benchmark ===")
    print(f"Model tier:          {results['model_tier']}")
    print(f"Time to first token: {results['time_to_first_token_s']} s")
    print(f"Total latency:       {results['total_latency_s']} s")
    print(f"Tokens (approx):     {results['tokens_approx']}")
    print(f"Tokens/sec:          {results['tokens_per_sec']}")
    print(f"Peak RSS:            {results['peak_rss_mb']} MB")
    print(f"Headroom (<7 GB):    {results['memory']['headroom_mb']} MB")
    print(f"Math engine check:   {math}")

    with open(args.json_out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved: {args.json_out}")


if __name__ == "__main__":
    main()
