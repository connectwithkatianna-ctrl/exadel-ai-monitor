#!/usr/bin/env python3
"""Query SerpApi (Google search results) for a keyword set and check organic ranking + competitor domains."""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
import yaml

TIMEOUT = 30
SEARCH_URL = "https://serpapi.com/search.json"


def domain_of(url):
    netloc = urlparse(url).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc


def search(query, api_key, num_results):
    resp = requests.get(
        SEARCH_URL,
        params={"engine": "google", "api_key": api_key, "q": query, "num": num_results},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json().get("organic_results", [])


def analyze_results(items, target_domain, competitors):
    target_domain = target_domain.lower()
    domain_position = None
    competitors_ranked = []

    for i, item in enumerate(items, start=1):
        link_domain = domain_of(item.get("link", ""))
        text = f"{item.get('title', '')} {item.get('snippet', '')} {link_domain}".lower()

        if domain_position is None and target_domain in link_domain:
            domain_position = i

        for name in competitors:
            if name.lower() in text:
                competitors_ranked.append({"position": i, "name": name, "domain": link_domain})

    return {
        "domain_mentioned": domain_position is not None,
        "domain_position": domain_position,
        "competitors_ranked": competitors_ranked,
        "top_results": [
            {"position": i, "title": it.get("title"), "link": it.get("link")}
            for i, it in enumerate(items, start=1)
        ],
    }


def run(config):
    target_domain = config["target_domain"]
    competitors = config["competitors"]
    queries = config["search_queries"]
    num_results = config.get("google_search", {}).get("num_results", 10)

    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        print("[skip] google_search: SERPAPI_API_KEY not set", file=sys.stderr)
        return []

    results = []
    for query in queries:
        try:
            items = search(query, api_key, num_results)
        except Exception as exc:
            print(f"[error] google_search / {query!r}: {exc}", file=sys.stderr)
            continue

        analysis = analyze_results(items, target_domain, competitors)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query": query,
            "target_domain": target_domain,
            **analysis,
        }
        results.append(record)

        flag = "YES" if record["domain_mentioned"] else "no"
        pos = f" (#{record['domain_position']})" if record["domain_position"] else ""
        print(f"[google_search] ranked={flag}{pos}  query={query!r}")

    return results


def save(results, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"serp-{datetime.now(timezone.utc).date()}.jsonl")
    with open(path, "a") as f:
        for record in results:
            f.write(json.dumps(record) + "\n")
    return path


def print_summary(results, target_domain, brand):
    non_branded = [r for r in results if brand.lower() not in r["query"].lower()]
    excluded = len(results) - len(non_branded)
    ranked = sum(r["domain_mentioned"] for r in non_branded)
    rate = 100 * ranked / len(non_branded) if non_branded else 0
    print(f"\n=== Summary: {target_domain} Google ranking (non-branded keywords) ===")
    if excluded:
        print(f"(excluding {excluded} quer{'y' if excluded == 1 else 'ies'} that already contain "
              f"\"{brand}\")")
    print(f"appeared in top results: {ranked}/{len(non_branded)} ({rate:.0f}%)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--out-dir", default="results")
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    results = run(config)
    if not results:
        print("No SERP results collected — check API keys and config.", file=sys.stderr)
        sys.exit(1)

    path = save(results, args.out_dir)
    print(f"\nSaved {len(results)} records to {path}")
    print_summary(results, config["target_domain"], config["brand"])


if __name__ == "__main__":
    main()
