from pathlib import Path
from core.scanner import scan_yaml_for_bom
from core.fixer import remove_bom
from core.report import generate_report

def run_cli():
    import argparse
    parser = argparse.ArgumentParser(description='Prismata BOM Validator')
    parser.add_argument('--root', type=str, default='Meta', help='Root folder to scan')
    parser.add_argument('--fix', action='store_true', help='Remove BOM and version bump')
    parser.add_argument('--report', type=str, help='Write audit report')

    args = parser.parse_args()

    root = Path(args.root)
    bom_files = scan_yaml_for_bom(root)

    report = generate_report(bom_files)
    print(report)

    if args.report:
        with open(args.report, 'w') as f:
            f.write(report)

    if args.fix:
        fixed = []
        for f in bom_files:
            new_path = remove_bom(f)
            fixed.append(new_path)

        print('\nFixed files:')
        for f in fixed:
            print('  ', f)
