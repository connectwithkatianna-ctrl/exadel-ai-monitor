#!/usr/bin/env python3
"""Aggregate monitor.py and serp_monitor.py logs into per-date trend stats."""
import argparse
import glob
import json
from collections import defaultdict, Counter

import yaml

# Display names are the AI platform/product, not the company that makes it.
PLATFORM_NAMES = {
    "openai": "ChatGPT",
    "anthropic": "Claude",
    "gemini": "Gemini",
    "perplexity": "Perplexity",
}


def is_branded(text, brand):
    """A prompt/query that already contains the brand name isn't testing organic
    recall — the model or search engine is just echoing back a word we gave it."""
    return brand.lower() in text.lower()


def load_jsonl(paths):
    records = []
    for path in paths:
        with open(path) as f:
            for line in f:
                records.append(json.loads(line))
    return records


def load_ai_records(results_dir):
    paths = [p for p in glob.glob(f"{results_dir}/*.jsonl") if "serp-" not in p]
    return load_jsonl(sorted(paths))


def load_serp_records(results_dir):
    return load_jsonl(sorted(glob.glob(f"{results_dir}/serp-*.jsonl")))


def print_ai_report(records, brand):
    if not records:
        print("No AI-assistant records found.")
        return

    organic = [r for r in records if not is_branded(r["prompt"], brand)]
    excluded = len(records) - len(organic)

    print("=== AI assistant visibility (organic mentions only) ===")
    if excluded:
        print(f"(excluding {excluded} response(s) to prompts that already name \"{brand}\" "
              f"— those are echoes, not organic recall)")

    groups = defaultdict(list)
    for r in organic:
        groups[(r["timestamp"][:10], r["provider"])].append(r)

    print(f"{'date':12s} {'provider':12s} {'mention rate':14s} {'avg position':14s}")
    for (date, provider), items in sorted(groups.items()):
        mentioned = [r for r in items if r["brand_mentioned"]]
        rate = 100 * len(mentioned) / len(items)
        positions = [r["brand_position"] for r in mentioned if r["brand_position"]]
        avg_pos = f"{sum(positions) / len(positions):.1f}" if positions else "n/a"
        name = PLATFORM_NAMES.get(provider, provider)
        print(f"{date:12s} {name:12s} {rate:5.0f}%{'':9s} {avg_pos:14s}")

    competitor_counts = Counter()
    for r in organic:
        competitor_counts.update(r["competitors_mentioned"])
    if competitor_counts:
        print("\nCompetitor mention frequency, organic prompts only (all-time):")
        for name, count in competitor_counts.most_common():
            print(f"  {name:20s} {count}")


def print_serp_report(records, brand):
    if not records:
        print("No Google search records found.")
        return

    target_domain = records[0]["target_domain"]
    non_branded = [r for r in records if not is_branded(r["query"], brand)]
    excluded = len(records) - len(non_branded)

    print(f"\n=== Google search ranking: {target_domain} (non-branded keywords only) ===")
    if excluded:
        print(f"(excluding {excluded} quer{'y' if excluded == 1 else 'ies'} that already contain "
              f"\"{brand}\" — branded searches don't measure discoverability by new prospects)")

    groups = defaultdict(list)
    for r in non_branded:
        groups[r["timestamp"][:10]].append(r)

    print(f"{'date':12s} {'appear rate':14s} {'avg position':14s}")
    for date, items in sorted(groups.items()):
        ranked = [r for r in items if r["domain_mentioned"]]
        rate = 100 * len(ranked) / len(items)
        positions = [r["domain_position"] for r in ranked]
        avg_pos = f"{sum(positions) / len(positions):.1f}" if positions else "n/a"
        print(f"{date:12s} {rate:5.0f}%{'':9s} {avg_pos:14s}")

    competitor_counts = Counter()
    for r in non_branded:
        competitor_counts.update(c["name"] for c in r["competitors_ranked"])
    if competitor_counts:
        print("\nCompetitor domains appearing in results, non-branded keywords only (all-time):")
        for name, count in competitor_counts.most_common():
            print(f"  {name:20s} {count}")


def print_keyword_gap(records, brand):
    """Per-keyword competitive gap: the metric that actually drives an SEO backlog.
    Appear-rate/avg-position are blended averages; this shows, keyword by keyword,
    exactly where a competitor is capturing a top-10 slot that Exadel isn't."""
    non_branded = [r for r in records if not is_branded(r["query"], brand)]
    if not non_branded:
        return

    latest_by_query = {}
    for r in sorted(non_branded, key=lambda r: r["timestamp"]):
        latest_by_query[r["query"]] = r  # last write wins -> most recent run per query

    print("\n=== Competitive keyword gap (most recent run per keyword) ===")
    print(f"{'query':45s} {'exadel.com':12s} {'top competitor in top 10':30s}")
    gap_count = 0
    for query, r in latest_by_query.items():
        exadel = f"#{r['domain_position']}" if r["domain_mentioned"] else "not ranked"
        if r["competitors_ranked"]:
            best = min(r["competitors_ranked"], key=lambda c: c["position"])
            comp = f"{best['name']} (#{best['position']})"
        else:
            comp = "none in top 10"
        if not r["domain_mentioned"] and r["competitors_ranked"]:
            gap_count += 1
        print(f"{query:45s} {exadel:12s} {comp:30s}")

    if gap_count:
        print(f"\n{gap_count}/{len(latest_by_query)} keyword(s): a tracked competitor ranks in the "
              f"top 10 while exadel.com does not — these are the priority targets for new/updated "
              f"content and on-page SEO.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", default="results")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)
    brand = config["brand"]

    print_ai_report(load_ai_records(args.results_dir), brand)
    serp_records = load_serp_records(args.results_dir)
    print_serp_report(serp_records, brand)
    print_keyword_gap(serp_records, brand)


if __name__ == "__main__":
    main()
