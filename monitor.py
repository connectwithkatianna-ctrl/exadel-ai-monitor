#!/usr/bin/env python3
"""Query multiple AI assistants with a prompt set and log whether/how they mention a brand."""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

import requests
import yaml

TIMEOUT = 60


def call_openai(prompt, model):
    key = os.environ["OPENAI_API_KEY"]
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}]},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def call_anthropic(prompt, model):
    key = os.environ["ANTHROPIC_API_KEY"]
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
        json={
            "model": model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]


def call_gemini(prompt, model):
    key = os.environ["GOOGLE_API_KEY"]
    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        params={"key": key},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def call_perplexity(prompt, model):
    key = os.environ["PERPLEXITY_API_KEY"]
    resp = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}]},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


CALLERS = {
    "openai": call_openai,
    "anthropic": call_anthropic,
    "gemini": call_gemini,
    "perplexity": call_perplexity,
}

REQUIRED_ENV = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
}

# Display names are the AI platform/product, not the company that makes it.
PLATFORM_NAMES = {
    "openai": "ChatGPT",
    "anthropic": "Claude",
    "gemini": "Gemini",
    "perplexity": "Perplexity",
}

LIST_ITEM_RE = re.compile(r"^\s*(\d+)[.)]\s+", re.MULTILINE)


def find_position(text, name):
    """Return the 1-based rank of `name` if the response is a numbered list, else None."""
    lower = text.lower()
    idx = lower.find(name.lower())
    if idx == -1:
        return None
    preceding = text[:idx]
    matches = list(LIST_ITEM_RE.finditer(preceding))
    if not matches:
        return None
    return int(matches[-1].group(1))


def analyze_response(text, brand, competitors):
    mentioned = brand.lower() in text.lower()
    return {
        "brand_mentioned": mentioned,
        "brand_position": find_position(text, brand) if mentioned else None,
        "competitors_mentioned": [c for c in competitors if c.lower() in text.lower()],
    }


def run(config, providers_filter=None):
    brand = config["brand"]
    competitors = config["competitors"]
    prompts = config["prompts"]
    results = []

    for provider, settings in config["providers"].items():
        if not settings.get("enabled"):
            continue
        if providers_filter and provider not in providers_filter:
            continue
        env_var = REQUIRED_ENV[provider]
        if env_var not in os.environ:
            print(f"[skip] {provider}: {env_var} not set", file=sys.stderr)
            continue

        for prompt in prompts:
            try:
                text = CALLERS[provider](prompt, settings["model"])
            except Exception as exc:
                print(f"[error] {provider} / {prompt!r}: {exc}", file=sys.stderr)
                continue

            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "provider": provider,
                "model": settings["model"],
                "prompt": prompt,
                "response": text,
                **analyze_response(text, brand, competitors),
            }
            results.append(record)
            flag = "YES" if record["brand_mentioned"] else "no"
            pos = f" (#{record['brand_position']})" if record["brand_position"] else ""
            print(f"[{PLATFORM_NAMES.get(provider, provider)}] mentioned={flag}{pos}  prompt={prompt[:60]!r}")

    return results


def save(results, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{datetime.now(timezone.utc).date()}.jsonl")
    with open(path, "a") as f:
        for record in results:
            f.write(json.dumps(record) + "\n")
    return path


def print_summary(results, brand):
    organic = [r for r in results if brand.lower() not in r["prompt"].lower()]
    excluded = len(results) - len(organic)

    by_provider = {}
    for r in organic:
        by_provider.setdefault(r["provider"], []).append(r)

    print(f"\n=== Summary: {brand} organic visibility ===")
    if excluded:
        print(f"(excluding {excluded} response(s) to prompts that already name \"{brand}\" "
              f"— those are echoes, not organic recall)")
    for provider, records in by_provider.items():
        mentioned = sum(r["brand_mentioned"] for r in records)
        rate = 100 * mentioned / len(records) if records else 0
        name = PLATFORM_NAMES.get(provider, provider)
        print(f"{name:12s} organic mention rate: {mentioned}/{len(records)} ({rate:.0f}%)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--out-dir", default="results")
    parser.add_argument("--providers", nargs="+", help="restrict to specific providers")
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    results = run(config, providers_filter=args.providers)
    if not results:
        print("No results collected — check API keys and config.", file=sys.stderr)
        sys.exit(1)

    path = save(results, args.out_dir)
    print(f"\nSaved {len(results)} records to {path}")
    print_summary(results, config["brand"])


if __name__ == "__main__":
    main()
