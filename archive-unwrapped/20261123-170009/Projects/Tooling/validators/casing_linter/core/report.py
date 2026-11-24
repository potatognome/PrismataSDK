def generate_report(issues):
    lines = []
    lines.append('Casing Audit Report')
    lines.append('-------------------')
    lines.append(f'Total issues: {len(issues)}')
    lines.append('')

    for path, key, casing in issues:
        lines.append(f'{path}: {key} ? {casing}')

    return '\\n'.join(lines)
