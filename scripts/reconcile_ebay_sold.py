"""Reconcile bundled eBay discovery descriptions with an already merged backend revision.

This is a narrow, traceable overlay on the original discovery snapshot. It does
not claim that the corrected schemas were fetched from a deployed server.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "cli" / "nexscope_cli"
NAMES = ("nexscope_data_ebay_search", "nexscope_ebay_search")


def digest(value):
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                           allow_nan=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-root", type=Path, required=True)
    parser.add_argument("--expected-revision", required=True)
    args = parser.parse_args()
    backend = args.backend_root.resolve()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=backend,
                                       text=True).strip()
    if revision != args.expected_revision:
        raise SystemExit(f"Backend revision changed: {revision}")

    catalog_path = backend / "sa-business/sa-skill-api/src/main/resources/catalog/linkfox-data.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    endpoint = next(item for item in catalog["endpoints"] if item.get("path") == "/ebay/search")
    descriptions = {
        NAMES[0]: endpoint["requestSchema"]["properties"]["showOnly"]["description"]
    }
    java_path = backend / ("sa-business/sa-skill-api/src/main/java/com/zixun/"
                           "selleragent/skillapi/definition/skills/EbaySearchSkill.java")
    matches = re.findall(r'p\("showOnly", "string", false, "([^"]+)", null\)',
                         java_path.read_text(encoding="utf-8"))
    if len(matches) != 1:
        raise SystemExit("Expected one eBay Skill showOnly definition")
    descriptions[NAMES[1]] = matches[0]
    if any(re.search(r"`?Sold`?\s*\(Sold\)", text) for text in descriptions.values()):
        raise SystemExit("Backend source still advertises the retired Sold value")

    tools_path = PACKAGE / "tools.json"
    contract_path = PACKAGE / "api-contract.json"
    snapshot = json.loads(tools_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    by_name = {tool["name"]: tool for tool in snapshot["tools"]}
    if any(name not in by_name or name not in contract["toolBindings"] for name in NAMES):
        raise SystemExit("Both eBay tools must exist in the bundled catalog and contract")
    before_count = len(snapshot["tools"])
    for name in NAMES:
        field = by_name[name]["inputSchema"]["properties"]["showOnly"]
        if "Sold" not in field["description"]:
            raise SystemExit(f"Expected retired Sold text in {name}")
        field["description"] = descriptions[name]
        contract["toolBindings"][name]["inputSchemaSha256"] = digest(by_name[name]["inputSchema"])

    snapshot["sha256"] = digest(snapshot["tools"])
    # Preserve the original discovery timestamp and the independently observed
    # public request schema hashes. Only bundled MCP input descriptions changed.
    update = {
        "observedAt": datetime.now(timezone.utc).isoformat(),
        "source": f"https://git.ziniao.com/nexscope/service/backend-java/-/commit/{revision}",
        "scope": "Two eBay MCP input descriptions reconciled from merged backend source; "
                 "not a live production discovery",
        "coverageDiff": {"before": before_count, "after": len(snapshot["tools"]),
                         "added": [], "removed": []},
        "tools": list(NAMES),
    }
    snapshot.setdefault("incrementalUpdates", []).append(update)
    contract["toolCatalog"]["sha256"] = snapshot["sha256"]
    contract["toolCatalog"].setdefault("incrementalUpdates", []).append(update)
    write_json(tools_path, snapshot)
    write_json(contract_path, contract)
    print(f"Reconciled {', '.join(NAMES)} from backend {revision}; {before_count} tools unchanged")


if __name__ == "__main__":
    main()
