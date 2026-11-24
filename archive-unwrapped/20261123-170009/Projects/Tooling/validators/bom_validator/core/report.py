def generate_report(files):
    lines = []
    lines.append('BOM Audit Report')
    lines.append('----------------')
    lines.append(f'Files containing BOM: {len(files)}')
    lines.append('')

    for f in files:
        lines.append(str(f))

    return '\\n'.join(lines)
