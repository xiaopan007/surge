#!/usr/bin/env python3
import ipaddress
import json
import urllib.request
from pathlib import Path


DERP_MAP_URL = "https://controlplane.tailscale.com/derpmap/default"
OUTPUT = Path(__file__).resolve().parents[1] / "tailscale.list"

STATIC_RULES = [
    "DOMAIN-SUFFIX,tailscale.com",
    "DOMAIN-SUFFIX,ts.net",
    "IP-CIDR,100.64.0.0/10,no-resolve",
    "IP-CIDR,192.200.0.0/24,no-resolve",
    "IP-CIDR6,2606:B740:49::/48,no-resolve",
    "IP-CIDR,199.165.136.0/24,no-resolve",
    "IP-CIDR6,2606:B740:1::/48,no-resolve",
    "DEST-PORT,3478",
    "DEST-PORT,41641",
]


def ip_sort_key(value: str) -> tuple[int, int]:
    parsed = ipaddress.ip_address(value)
    return parsed.version, int(parsed)


def main() -> None:
    with urllib.request.urlopen(DERP_MAP_URL, timeout=30) as response:
        derp_map = json.load(response)

    hostnames: set[str] = set()
    ipv4: set[str] = set()
    ipv6: set[str] = set()

    for region in derp_map.get("Regions", {}).values():
        for node in region.get("Nodes", []):
            hostname = node.get("HostName")
            if hostname:
                hostnames.add(hostname)

            node_ipv4 = node.get("IPv4")
            if node_ipv4:
                ipv4.add(node_ipv4)

            node_ipv6 = node.get("IPv6")
            if node_ipv6:
                ipv6.add(node_ipv6)

    rules = list(STATIC_RULES)
    rules.extend(f"DOMAIN,{hostname}" for hostname in sorted(hostnames))
    rules.extend(f"IP-CIDR,{ip}/32,no-resolve" for ip in sorted(ipv4, key=ip_sort_key))
    rules.extend(f"IP-CIDR6,{ip}/128,no-resolve" for ip in sorted(ipv6, key=ip_sort_key))

    OUTPUT.write_text("\n".join([f"# 规则数量: {len(rules)}"] + rules) + "\n")


if __name__ == "__main__":
    main()
