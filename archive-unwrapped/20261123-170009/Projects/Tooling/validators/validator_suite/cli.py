from Projects.Tooling.validators.validator_suite.runner import run_all_validators, fix_all

def run_cli():
    import argparse
    parser = argparse.ArgumentParser(description='Prismata Validator Suite')
    parser.add_argument("--fix", action="store_true", help="Fix all issues")
    parser.add_argument("--gui", action="store_true", help="Launch GUI dashboard")
    parser.add_argument("--root", default=".", help="Repo root to validate")

    args = parser.parse_args()

    if args.gui:
        from Projects.Tooling.validators.validator_suite.gui import ValidatorDashboard
        app = ValidatorDashboard()
        app.mainloop()
        return

    results = run_all_validators(args.root)
    print("Validator Suite Report")
    print("----------------------")
    print(f"Casing issues: {len(results['casing']['issues'])}")
    print(f"BOM issues: {len(results['bom']['issues'])}")
    print(f"Repo gate issues: {results['repo_gate']['summary']['failed_checks']}")

    if args.fix:
        fix_all(results)
        print("\nFixes applied.")
