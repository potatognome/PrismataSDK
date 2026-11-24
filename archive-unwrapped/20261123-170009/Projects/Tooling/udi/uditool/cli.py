import argparse
from .scanner import scan_globs


def main():
    parser = argparse.ArgumentParser(prog="uditool")
    sub = parser.add_subparsers(dest="cmd")
    p = sub.add_parser("scan")
    p.add_argument("--globs", nargs="+", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--aggregate", action="store_true", help="Write aggregated full-report.yaml into --out")
    args = parser.parse_args()
    if args.cmd == "scan":
        reports = scan_globs(args.globs, args.out, aggregate=args.aggregate)
        print(f"Scanned {len(reports)} files; reports in {args.out}")


if __name__ == "__main__":
    main()
