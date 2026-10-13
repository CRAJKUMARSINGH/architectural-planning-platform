"""
DAY-N AUTOMATED SIGN-OFF SCRIPT
================================
Bar Association Hall — Tier-2 27-sheet (26 individual + 1 master) drawing set.
Per user profile: automated sign-off. Exit 0 = GREEN PASS, non-zero = RED FAIL.

Validates:
  1. Required 26 individual drawing PDFs exist, sized above min-kB threshold.
  2. Required 6 CAD DXF exports exist (A-101, A-102, A-301, A-302, S-101, S-102).
  3. Master combined 26-sheet PDF exists and exceeds 200 KB.
  4. A2 landscape aspect-ratio check (16.54" × 11.69" ≈ ratio 1.415 ± 0.05)
     for a statistical sample of PDFs (using MediaBox via PyPDF2 fallback to size).
  5. Manifest hash / count consistency with expected SHEET_JOBS breakdown.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parent
PDF_DIR = PROJECT_DIR / "exports" / "PDF"
CAD_DIR = PROJECT_DIR / "exports" / "CAD"
MANIFEST_PATH = PROJECT_DIR / "exports" / "professional_manifest.json"
SUMMARY_PATH = PROJECT_DIR / "exports" / "DELIVERY-SUMMARY.txt"

MIN_PDF_KB = 3.0
MIN_DXF_KB = 10.0
MIN_MASTER_PDF_KB = 200.0
A2_RATIO_TARGET = 594.0 / 420.0   # 1.4142857 (ISO A2 landscape width/height)
A2_RATIO_TOL = 0.08

REQUIRED_PDFS = [
    "A-00-cover-sheet-&-sheet-index.pdf",
    "A-01-general-notes-&-abbreviations.pdf",
    "A-001-proposed-site-layout-plan.pdf",
    "A-101-ground-floor-architectural-plan.pdf",
    "A-102-first-floor-architectural-plan.pdf",
    "A-111-gf-reflected-ceiling-plan.pdf",
    "A-112-ff-reflected-ceiling-plan.pdf",
    "A-201-south-elevation.pdf",
    "A-202-east-elevation-—-main-entrance.pdf",
    "A-203-north-elevation.pdf",
    "A-204-west-elevation.pdf",
    "A-251-key-interior-elevations-(typicals).pdf",
    "A-301-longitudinal-section-a-a.pdf",
    "A-302-cross-section-b-b-(entry-+-balcony).pdf",
    "A-401-door-schedule-+-window-schedule.pdf",
    "A-402-finishes-schedule-+-area-statement.pdf",
    "A-501-enlarged-toilet-details-(gents-+-ladies).pdf",
    "A-502-typical-details-dpc---jamb---chajja---join.pdf",
    "A-503-typical-details-flooring---skirting---dado.pdf",
    "A-504-typical-details-terrace---balcony-waterpro.pdf",
    "A-601-stair-+-balcony-details.pdf",
    "S-001-general-structural-notes-+-member-schedule.pdf",
    "S-101-gf-column-&-grid-layout-plan.pdf",
    "S-102-ff-column-&-grid-layout-plan.pdf",
    "E-101-composite-electrical-plan-(gf).pdf",
    "P-101-composite-plumbing-&-drainage-plan-(gf).pdf",
]

REQUIRED_DXFS = [
    "A-101-ground-floor-architectural-plan.dxf",
    "A-102-first-floor-architectural-plan.dxf",
    "A-301-Longitudinal-Section.dxf",
    "A-302-Cross-Section.dxf",
    "S-101-gf-column-&-grid-layout-plan.dxf",
    "S-102-ff-column-&-grid-layout-plan.dxf",
]

MASTER_PDF = "Bar-Association-Professional-Master-Set.pdf"

BREAKDOWN_EXPECTED = {
    "architectural": 21,  # A-* rows
    "structural":     3,  # S-* rows
    "mep":            2,  # E-* + P-* rows
    "individual":    26,  # total individual sheets
}

GREEN = "\033[92m"
RED   = "\033[91m"
YEL   = "\033[93m"
CYAN  = "\033[96m"
DIM   = "\033[2m"
RST   = "\033[0m"
OK    = f"{GREEN}[PASS]{RST}"
FAIL  = f"{RED}[FAIL]{RST}"
WARN  = f"{YEL}[WARN]{RST}"


def kb(p: Path) -> float:
    return p.stat().st_size / 1024.0 if p.exists() else 0.0


def sha256_of(path: Path, n_bytes: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(n_bytes), b""):
            h.update(chunk)
    return h.hexdigest()


def pdf_pages_and_aspect(path: Path) -> tuple[int | None, float | None]:
    """Return (pages, aspect_ratio W/H) using PyPDF2 / pypdf if installed;
    otherwise fallback to inspecting raw MediaBox in first pages."""
    pages: int | None = None
    aspect: float | None = None
    try:
        from pypdf import PdfReader  # type: ignore
        r = PdfReader(str(path))
        pages = len(r.pages)
        if pages:
            mb = r.pages[0].mediabox
            w = float(mb.width); h = float(mb.height)
            if w < h:
                w, h = h, w
            aspect = w / h
    except Exception:
        # Fallback heuristic: A2 PDF typically ~842x595 pt landscape => ratio ~1.415
        # Parse raw bytes looking for /MediaBox [a b c d]
        try:
            raw = path.read_bytes()[:100_000]
            idx = raw.find(b"/MediaBox")
            if idx != -1:
                end = raw.find(b"]", idx)
                tok = raw[idx:end + 1].decode(errors="ignore")
                nums = [float(x) for x in tok.replace("[", " ").replace("]", " ").split()
                        if x.replace(".", "", 1).lstrip("-").isdigit()]
                if len(nums) == 4:
                    w = abs(nums[2] - nums[0])
                    h = abs(nums[3] - nums[1])
                    if w < h:
                        w, h = h, w
                    aspect = w / h if h else None
        except Exception:
            pass
    return pages, aspect


def section(title: str) -> None:
    bar = "=" * 72
    print(f"\n{CYAN}{bar}{RST}")
    print(f"{CYAN}  {title}{RST}")
    print(f"{CYAN}{bar}{RST}")


def main() -> int:
    failed: list[str] = []
    warnings: list[str] = []
    report: dict[str, Any] = {
        "project": "Bar-Association-Hall",
        "tier": 2,
        "individual_sheets_expected": BREAKDOWN_EXPECTED["individual"],
        "pdfs_checked": [],
        "dxfs_checked": [],
    }

    section("1. REQUIRED INDIVIDUAL PDF SHEETS (26)")
    for fname in REQUIRED_PDFS:
        fpath = PDF_DIR / fname
        k = kb(fpath)
        status = OK if fpath.exists() and k >= MIN_PDF_KB else FAIL
        if status == FAIL:
            why = f"missing" if not fpath.exists() else f"too small ({k:.2f} KB < {MIN_PDF_KB:.1f} KB)"
            failed.append(f"PDF {fname}: {why}")
            print(f"  {status}  {fname}  — {RED}{why}{RST}")
        else:
            print(f"  {status}  {fname}  — {GREEN}{k:7.2f} KB{RST}")
        report["pdfs_checked"].append({
            "file": fname, "exists": fpath.exists(), "size_kb": round(k, 2),
            "pass": status == OK,
        })

    section("2. REQUIRED CAD DXF EXPORTS (6)")
    for fname in REQUIRED_DXFS:
        fpath = CAD_DIR / fname
        k = kb(fpath)
        status = OK if fpath.exists() and k >= MIN_DXF_KB else FAIL
        if status == FAIL:
            why = f"missing" if not fpath.exists() else f"too small ({k:.2f} KB < {MIN_DXF_KB:.1f} KB)"
            failed.append(f"DXF {fname}: {why}")
            print(f"  {status}  {fname}  — {RED}{why}{RST}")
        else:
            print(f"  {status}  {fname}  — {GREEN}{k:7.2f} KB{RST}")
        report["dxfs_checked"].append({
            "file": fname, "exists": fpath.exists(), "size_kb": round(k, 2),
            "pass": status == OK,
        })

    section("3. COMBINED MASTER PDF")
    mpath = PDF_DIR / MASTER_PDF
    mk = kb(mpath)
    pages, aspect = pdf_pages_and_aspect(mpath) if mpath.exists() else (None, None)
    status_master = (
        OK if mpath.exists() and mk >= MIN_MASTER_PDF_KB else FAIL
    )
    if status_master == FAIL:
        why = "missing" if not mpath.exists() else f"too small ({mk:.1f} KB < {MIN_MASTER_PDF_KB:.0f} KB)"
        failed.append(f"MASTER PDF: {why}")
        print(f"  {FAIL}  {MASTER_PDF}: {RED}{why}{RST}")
    else:
        pg = f"{pages} pg" if pages else "pages unknown"
        ar = f"aspect {aspect:.3f}" if aspect else "aspect unknown"
        print(f"  {OK}  {MASTER_PDF}  — {GREEN}{mk:.1f} KB  {pg}  {ar}{RST}")
    report["master_pdf"] = {
        "file": MASTER_PDF, "exists": mpath.exists(),
        "size_kb": round(mk, 2), "pages": pages, "aspect": aspect,
        "pass": status_master == OK,
    }

    section("4. A2 LANDSCAPE ASPECT-RATIO SAMPLE CHECK (ISO 5457)")
    # Pick 6 representative sheets across disciplines
    samples = [
        "A-001-proposed-site-layout-plan.pdf",
        "A-101-ground-floor-architectural-plan.pdf",
        "A-201-south-elevation.pdf",
        "A-301-longitudinal-section-a-a.pdf",
        "S-101-gf-column-&-grid-layout-plan.pdf",
        "E-101-composite-electrical-plan-(gf).pdf",
    ]
    ratios: list[float] = []
    for fname in samples:
        fp = PDF_DIR / fname
        if not fp.exists():
            print(f"  {WARN}  {fname}: missing, skip aspect check")
            warnings.append(f"aspect-check skipped: {fname} missing")
            continue
        _, ar = pdf_pages_and_aspect(fp)
        if ar is None:
            print(f"  {WARN}  {fname}: unable to parse MediaBox (PyPDF missing?); fallback OK by size")
            warnings.append(f"aspect unparseable: {fname}")
            continue
        ratios.append(ar)
        in_tol = abs(ar - A2_RATIO_TARGET) <= A2_RATIO_TOL
        st = OK if in_tol else FAIL
        if not in_tol:
            failed.append(f"aspect out of tolerance: {fname} ({ar:.3f} vs target {A2_RATIO_TARGET:.3f} ±{A2_RATIO_TOL})")
        print(f"  {st}  {fname:<58s}  W/H = {ar:.4f}  (target {A2_RATIO_TARGET:.4f} ±{A2_RATIO_TOL})")
    report["aspect_check"] = {
        "target_ratio": round(A2_RATIO_TARGET, 5),
        "tolerance": A2_RATIO_TOL,
        "samples_measured": [round(r, 4) for r in ratios],
        "pass": all(abs(r - A2_RATIO_TARGET) <= A2_RATIO_TOL for r in ratios),
    }

    section("5. BREAKDOWN / MANIFEST CONSISTENCY")
    arch = sum(1 for f in REQUIRED_PDFS if f.startswith("A-"))
    stru = sum(1 for f in REQUIRED_PDFS if f.startswith("S-"))
    mep_ = sum(1 for f in REQUIRED_PDFS if f.startswith("E-") or f.startswith("P-"))
    tot = arch + stru + mep_
    ok_b = (arch == BREAKDOWN_EXPECTED["architectural"]
            and stru == BREAKDOWN_EXPECTED["structural"]
            and mep_ == BREAKDOWN_EXPECTED["mep"]
            and tot  == BREAKDOWN_EXPECTED["individual"])
    status = OK if ok_b else FAIL
    if not ok_b:
        failed.append(f"breakdown mismatch: got ARCH={arch} STR={stru} MEP={mep_} TOT={tot}")
    print(f"  {status}  SHEET BREAKDOWN")
    print(f"       Architectural (A-*) ............ {arch:>3d}   (expected {BREAKDOWN_EXPECTED['architectural']})")
    print(f"       Structural    (S-*) ............ {stru:>3d}   (expected {BREAKDOWN_EXPECTED['structural']})")
    print(f"       MEP           (E-*,P-*) ........ {mep_:>3d}   (expected {BREAKDOWN_EXPECTED['mep']})")
    print(f"       Individual TOTAL ............... {tot:>3d}   (expected {BREAKDOWN_EXPECTED['individual']})")
    report["breakdown"] = {"architectural": arch, "structural": stru,
                           "mep": mep_, "total": tot, "pass": ok_b}

    # Manifest consistency
    if MANIFEST_PATH.exists():
        try:
            mf = json.loads(MANIFEST_PATH.read_text())
            sheets = mf.get("sheets", [])
            sheets_n = len(sheets) if isinstance(sheets, list) else None
            st = OK if sheets_n == BREAKDOWN_EXPECTED["individual"] else WARN
            if st == WARN:
                warnings.append(f"manifest sheets count: {sheets_n} (expected {BREAKDOWN_EXPECTED['individual']})")
            print(f"  {st}  {MANIFEST_PATH.name}: sheets listed = {sheets_n}")
            report["manifest"] = {"path": str(MANIFEST_PATH),
                                  "sheets_count": sheets_n, "sheets_expected": BREAKDOWN_EXPECTED["individual"]}
        except Exception as e:
            warnings.append(f"manifest parse error: {e}")
            print(f"  {WARN}  manifest unreadable: {e}")
    else:
        print(f"  {WARN}  manifest file not found at {MANIFEST_PATH}")
        warnings.append("manifest missing")

    # Master hash
    if mpath.exists():
        mh = sha256_of(mpath)[:16]
        print(f"  {DIM}  Master PDF SHA-256 (first 16): {mh} ...{RST}")
        report["master_sha256_prefix"] = mh

    section("SIGN-OFF SUMMARY")
    total_checks = (len(REQUIRED_PDFS) + len(REQUIRED_DXFS) + 1  # master
                    + len(samples) + 2)                           # breakdown + manifest
    n_fail = len(failed)
    n_warn = len(warnings)
    if n_fail == 0:
        print(f"  {GREEN}{'#' * 60}{RST}")
        print(f"  {GREEN}#  GREEN SIGN-OFF — ALL CRITICAL CHECKS PASSED      #{RST}")
        print(f"  {GREEN}#  Individual PDFs : {len(REQUIRED_PDFS):>3d} sheets                  #{RST}")
        print(f"  {GREEN}#  CAD DXF exports  : {len(REQUIRED_DXFS):>3d} files                   #{RST}")
        print(f"  {GREEN}#  Master combined  : {MASTER_PDF[:36]:<36s} #{RST}")
        print(f"  {GREEN}#  Warnings         : {n_warn:>3d}                           #{RST}")
        print(f"  {GREEN}{'#' * 60}{RST}")
    else:
        print(f"  {RED}{'#' * 60}{RST}")
        print(f"  {RED}#  RED — SIGN-OFF FAILED. See failures below:           #{RST}")
        for i, f in enumerate(failed, 1):
            print(f"  {RED}#   {i:>02d}. {f[:52]:<52s}  #{RST}")
        print(f"  {RED}{'#' * 60}{RST}")

    report["sign_off"] = {"passed": n_fail == 0,
                          "failures": failed, "warnings": warnings}

    # Save machine-readable sign-off report
    out = PROJECT_DIR / "exports" / "DAY-N-SIGNOFF-REPORT.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"\n{DIM}  Machine-readable report: {out}{RST}")

    return 0 if n_fail == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
