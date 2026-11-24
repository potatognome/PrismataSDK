from Projects.Tooling.validators.casing_linter.core.scanner import scan_all_yaml
from Projects.Tooling.validators.casing_linter.core.fixer import fix_yaml_file
from Projects.Tooling.validators.casing_linter.core.report import generate_report

def run_cli():
    import argparse
    parser = argparse.ArgumentParser(description='Prismata Casing Linter')
    parser.add_argument('--fix', action='store_true', help='Auto-fix casing issues')
    parser.add_argument('--report', type=str, help='Write audit report')

    args = parser.parse_args()

    issues = scan_all_yaml()
    report = generate_report(issues)

    print(report)

    if args.report:
        with open(args.report, 'w') as f:
            f.write(report)

    if args.fix:
        fixed_files = set()
        for path, key, casing in issues:
            new_path = fix_yaml_file(path)
            fixed_files.add(new_path)
        print('\nFixed files:')
        for f in fixed_files:
            print('  ', f)
