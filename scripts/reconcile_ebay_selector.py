"""Reconcile eBay keyword/categoryId descriptions with a merged backend revision.

The original discovery timestamp and public API schema hashes remain unchanged.
This overlay records source provenance without claiming a production refresh.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess

from reconcile_ebay_sold import NAMES, PACKAGE, digest, write_json


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
        NAMES[0]: {field: endpoint["requestSchema"]["properties"][field]["description"]
                   for field in ("keyword", "categoryId")}
    }
    java_path = backend / ("sa-business/sa-skill-api/src/main/java/com/zixun/"
                           "selleragent/skillapi/definition/skills/EbaySearchSkill.java")
    source = java_path.read_text(encoding="utf-8")
    descriptions[NAMES[1]] = {}
    for field, field_type in (("keyword", "string"), ("categoryId", "integer")):
        pattern = rf'p\("{field}", "{field_type}", false, "([^"]+)",'
        matches = re.findall(pattern, source)
        if len(matches) != 1:
            raise SystemExit(f"Expected one eBay Skill {field} definition")
        descriptions[NAMES[1]][field] = matches[0]
    for fields in descriptions.values():
        if "required unless categoryId is supplied" not in fields["keyword"] or \
                "required unless keyword is supplied" not in fields["categoryId"]:
            raise SystemExit("Backend source lacks the conditional selector rule")

    tools_path = PACKAGE / "tools.json"
    contract_path = PACKAGE / "api-contract.json"
    snapshot = json.loads(tools_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    by_name = {tool["name"]: tool for tool in snapshot["tools"]}
    if any(name not in by_name or name not in contract["toolBindings"] for name in NAMES):
        raise SystemExit("Both eBay tools must exist in the bundled catalog and contract")
    before_count = len(snapshot["tools"])
    for name in NAMES:
        properties = by_name[name]["inputSchema"]["properties"]
        for field, description in descriptions[name].items():
            if "required unless" in properties[field]["description"]:
                raise SystemExit(f"{name}.{field} already has conditional selector guidance")
            properties[field]["description"] = description
        contract["toolBindings"][name]["inputSchemaSha256"] = digest(by_name[name]["inputSchema"])

    snapshot["sha256"] = digest(snapshot["tools"])
    update = {
        "observedAt": datetime.now(timezone.utc).isoformat(),
        "source": f"https://git.ziniao.com/nexscope/service/backend-java/-/commit/{revision}",
        "scope": "Two eBay MCP input schemas gained conditional keyword/categoryId guidance "
                 "from merged backend source; not a live production discovery",
        "coverageDiff": {"before": before_count, "after": len(snapshot["tools"]),
                         "added": [], "removed": []},
        "tools": list(NAMES),
    }
    snapshot.setdefault("incrementalUpdates", []).append(update)
    contract["toolCatalog"]["sha256"] = snapshot["sha256"]
    contract["toolCatalog"].setdefault("incrementalUpdates", []).append(update)
    write_json(tools_path, snapshot)
    write_json(contract_path, contract)
    print(f"Reconciled eBay selector descriptions from backend {revision}; {before_count} tools unchanged")


if __name__ == "__main__":
    main()
