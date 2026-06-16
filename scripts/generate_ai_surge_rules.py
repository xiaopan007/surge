#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.request
from pathlib import Path


REPO_TREE_URL = "https://api.github.com/repos/blackmatrix7/ios_rule_script/git/trees/master?recursive=1"
RAW_BASE_URL = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master"
CONNERSHUA_AI_URL = "https://raw.githubusercontent.com/ConnersHua/RuleGo/master/Surge/Ruleset/Extra/AI.list"
REPO_ROOT = Path(__file__).resolve().parents[1]
AI_OUTPUT = REPO_ROOT / "AI.list"

# blackmatrix7 does not publish a single AI aggregate list. Aggregate common
# AI service lists and keep compatibility dependencies, but let Apple/iCloud
# stay under the Apple policy group to avoid breaking CloudKit/iCloud sync.
SOURCE_NAMES = [
    "OpenAI",
    "Claude",
    "Anthropic",
    "Gemini",
    "BardAI",
    "Copilot",
    "Civitai",
    "Jetbrains",
    "aiXcoder",
]

PREFERRED_SUFFIXES = [
    "_All_No_Resolve.list",
    "_No_Resolve.list",
    ".list",
    "_All.list",
    "_Domain.list",
    "_Resolve.list",
]

EXCLUDED_EXACT_VALUES = {
    # iCloud/CloudKit sync should stay out of AI policy groups.
    "gateway.icloud.com",
}

EXCLUDED_TREE_SUFFIXES = {
    "apple-cloudkit.com",
    "icloud-content.com",
    "icloud-content.com.cn",
    "icloud.com",
    "icloud.com.cn",
}

IP_RULE_PREFIXES = ("IP-CIDR,", "IP-CIDR6,", "IP-ASN,")
RULE_OPTIONS = {"extended-matching", "no-resolve"}


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "xiaopan007-surge-ai-builder"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def fetch_json(url: str) -> dict:
    return json.loads(fetch_text(url))


def choose_source_path(paths: set[str], name: str) -> str:
    base = f"rule/Surge/{name}/{name}"
    for suffix in PREFERRED_SUFFIXES:
        candidate = f"{base}{suffix}"
        if candidate in paths:
            return candidate
    raise RuntimeError(f"No Surge rule list found for {name}")


def normalize_rule(raw_line: str) -> str | None:
    line = raw_line.strip()
    if not line or line.startswith("#"):
        return None

    parts = [part.strip() for part in line.split(",")]
    while parts and parts[-1].lower() in RULE_OPTIONS:
        parts.pop()
    line = ",".join(parts)

    rule_type = parts[0].upper() if parts else ""
    rule_value = parts[1].lower() if len(parts) > 1 else ""
    if rule_value in EXCLUDED_EXACT_VALUES:
        return None
    if any(rule_value == suffix or rule_value.endswith(f".{suffix}") for suffix in EXCLUDED_TREE_SUFFIXES):
        return None
    if line.startswith(IP_RULE_PREFIXES) and not line.lower().endswith(",no-resolve"):
        line = f"{line},no-resolve"

    return line


def write_ruleset(path: Path, rules: list[str]) -> None:
    path.write_text("\n".join([f"# 规则数量: {len(rules)}"] + rules) + "\n")


def main() -> None:
    tree = fetch_json(REPO_TREE_URL)
    paths = {item["path"] for item in tree.get("tree", []) if item.get("type") == "blob"}

    selected_paths = [choose_source_path(paths, name) for name in SOURCE_NAMES]

    seen: set[str] = set()
    rules: list[str] = []

    connershua_text = fetch_text(CONNERSHUA_AI_URL)
    source_texts = [
        (path, fetch_text(f"{RAW_BASE_URL}/{path}"))
        for path in selected_paths
    ]
    source_texts.append(("ConnersHua/RuleGo Surge/Ruleset/Extra/AI.list", connershua_text))

    for _, text in source_texts:
        for raw_line in text.splitlines():
            rule = normalize_rule(raw_line)
            if rule and rule not in seen:
                seen.add(rule)
                rules.append(rule)

    write_ruleset(AI_OUTPUT, rules)


if __name__ == "__main__":
    main()
