#!/usr/bin/env python3
"""Regression checks for safety-critical copy on DieselCodes static pages.

Run before publishing:
    python scripts/check_diagnostic_copy.py

Copy-level checks only; vehicle-specific manufacturer guidance still requires review.
"""
from pathlib import Path
import sys
from spn_safety_overrides import PAGES, apply_overrides

ROOT = Path(__file__).resolve().parents[1]
NO_START = ROOT / "problemy" / "ne-zavoditsya.html"
SPN_91 = ROOT / "kody" / "spn-91.html"


def main() -> int:
    errors = []
    no_start = NO_START.read_text(encoding="utf-8")
    pedal = SPN_91.read_text(encoding="utf-8")
    for term in ("If the engine will not start", "Do not attempt to drive", "What to check safely"):
        if term.casefold() not in no_start.casefold():
            errors.append(f"Missing no-start caution: {term}")
    for term in (
        "Get to somewhere with help without shutting the engine down.",
        "The reference does not mark any code in this group as a reason to stop.",
    ):
        if term.casefold() in no_start.casefold():
            errors.append(f"Misleading no-start advice returned: {term}")
    if '<b>Safe to drive</b>' in pedal or '<b>Safe to drive.</b>' in pedal:
        errors.append("SPN 91 page again unconditionally declares safe-to-drive")
    if "Driving safety cannot be determined from SPN 91 alone." not in pedal:
        errors.append("SPN 91 FAQ safety disclaimer is missing")
    for spn in PAGES:
        relative = f"kody/spn-{spn}.html"
        page = (ROOT / relative).read_text(encoding="utf-8")
        if apply_overrides(relative, page) != page:
            errors.append(f"SPN {spn} OEM safety correction is missing")
    if errors:
        print("\n".join("FAIL: " + error for error in errors))
        return 1
    print("PASS: no-start and five SPN safety-copy regression checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
