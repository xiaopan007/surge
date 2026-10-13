#!/usr/bin/env python3
from __future__ import annotations

import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


RAW_BASE_URL = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master"
CONNERSHUA_AI_URL = "https://raw.githubusercontent.com/ConnersHua/RuleGo/master/Surge/Ruleset/Extra/AI.list"
REPO_ROOT = Path(__file__).resolve().parents[1]
AI_OUTPUT = REPO_ROOT / "AI.list"
MAX_FETCH_ATTEMPTS = 4
RETRYABLE_HTTP_STATUS = {403, 429, 500, 502, 503, 504}

# blackmatrix7 does not publish a single AI aggregate list. Aggregate common
# AI service lists and keep compatibility dependencies, but let Apple/iCloud stay
# under the Apple policy group to avoid breaking CloudKit/iCloud sync. Keep the
# source paths explicit instead of discovering them through GitHub's repository
# tree API: hosted runners share anonymous API limits, which caused repeated 403s.
SOURCE_PATHS = [
    "rule/Surge/OpenAI/OpenAI.list",
    "rule/Surge/Claude/Claude.list",
    "rule/Surge/Anthropic/Anthropic.list",
    "rule/Surge/Gemini/Gemini.list",
    "rule/Surge/BardAI/BardAI.list",
    "rule/Surge/Copilot/Copilot.list",
    "rule/Surge/Civitai/Civitai.list",
    "rule/Surge/Jetbrains/Jetbrains.list",
    "rule/Surge/aiXcoder/aiXcoder.list",
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
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "xiaopan007-surge-ai-builder"},
    )
    for attempt in range(1, MAX_FETCH_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            if error.code not in RETRYABLE_HTTP_STATUS:
                raise
            last_error = error
        except (TimeoutError, urllib.error.URLError) as error:
            last_error = error

        if attempt < MAX_FETCH_ATTEMPTS:
            delay = 2 ** (attempt - 1)
            print(
                f"Fetch attempt {attempt} failed for {url}; retrying in {delay}s",
                file=sys.stderr,
            )
            time.sleep(delay)

    raise RuntimeError(
        f"Failed to fetch {url} after {MAX_FETCH_ATTEMPTS} attempts"
    ) from last_error


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
    seen: set[str] = set()
    rules: list[str] = []

    connershua_text = fetch_text(CONNERSHUA_AI_URL)
    source_texts = [
        (path, fetch_text(f"{RAW_BASE_URL}/{path}"))
        for path in SOURCE_PATHS
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
