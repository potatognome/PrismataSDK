import os
from uditool.scanner import scan_globs


def test_scan_sample(tmp_path):
    # create a sample yaml without udi
    p = tmp_path / "Projects" / "demo" / "config"
    p.mkdir(parents=True)
    f = p / "sample.yaml"
    f.write_text("metadata:\n  name: Sample Item\n")
    out = tmp_path / "out"
    out.mkdir()
    reports = scan_globs([str(f)], str(out))
    assert len(reports) == 1
    assert reports[0]["drift"]
    # suggested location should be metadata.udi
    assert reports[0].get("suggested_udi_location") == "metadata.udi"
