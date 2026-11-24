import glob
import os
import yaml
from .config import DETECTOR_VERSION, UDI_REGEX, CANONICAL_KINDS
from .udi_utils import derive_udi_from_path_and_content, parse_udi, validate_udi


def _find_udi_location(data):
    """Return (udi_value, location_string) where location_string describes where the udi was found."""
    if not isinstance(data, dict):
        return None, None
    # top-level udi
    if "udi" in data and data.get("udi"):
        return data.get("udi"), "top-level.udi"
    # legacy id fields at top-level
    for legacy in ("id", "schema_id", "capability_id", "menu_id"):
        if legacy in data and data.get(legacy):
            return data.get(legacy), f"top-level.{legacy}"
    # metadata subsection
    meta = data.get("metadata")
    if isinstance(meta, dict):
        if "udi" in meta and meta.get("udi"):
            return meta.get("udi"), "metadata.udi"
        for legacy in ("id", "schema_id", "capability_id", "menu_id"):
            if legacy in meta and meta.get(legacy):
                return meta.get(legacy), f"metadata.{legacy}"
    return None, None


def scan_globs(globs, out_dir, aggregate=False):
    os.makedirs(out_dir, exist_ok=True)
    files = []
    for g in globs:
        files.extend(glob.glob(g, recursive=True))
    reports = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                content = fh.read()
            data = yaml.safe_load(content) or {}
        except Exception:
            data = {}
        udi = None
        udi_loc = None
        if isinstance(data, dict):
            udi, udi_loc = _find_udi_location(data)
        record = {"artifact_path": f, "existing_ids": {"udi": udi, "location": udi_loc}, "drift": []}
        if not udi:
            expected = derive_udi_from_path_and_content(f, metadata_name=(data.get("metadata") or {}).get("name") if isinstance(data.get("metadata"), dict) else None)
            # prefer recommending placement under metadata.udi
            record["expected_udi"] = expected
            record["suggested_udi_location"] = "metadata.udi"
            # keep drift compact: code + severity + actual (no repeated expected field)
            record["drift"].append({"code": "MISSING_UDI", "severity": "critical", "actual": None})
        else:
            valid, errors = validate_udi(udi)
            if not valid:
                record["drift"].append({"code": "INVALID_UDI_PATTERN", "severity": "critical", "actual": udi, "errors": errors})
            else:
                parsed = parse_udi(udi)
                # kind check
                if parsed and parsed.get("kind") not in CANONICAL_KINDS:
                    record["drift"].append({"code": "INVALID_KIND", "severity": "high", "actual": parsed.get("kind")})
        reports.append(record)
        outpath = os.path.join(out_dir, os.path.basename(f) + ".udi-report.yaml")
        with open(outpath, "w", encoding="utf-8") as oh:
            yaml.safe_dump(record, oh)
    summary = {"detector_version": DETECTOR_VERSION, "scanned": len(files), "reports": len(reports)}
    with open(os.path.join(out_dir, "summary.yaml"), "w", encoding="utf-8") as sh:
        yaml.safe_dump(summary, sh)
    if aggregate:
        full = {"detector_version": DETECTOR_VERSION, "scanned": len(files), "reports": len(reports), "generated_at": None, "files": reports}
        # generated_at left None for caller to populate if desired; write to out_dir/full-report.yaml
        with open(os.path.join(out_dir, "full-report.yaml"), "w", encoding="utf-8") as fh:
            yaml.safe_dump(full, fh)
    return reports
