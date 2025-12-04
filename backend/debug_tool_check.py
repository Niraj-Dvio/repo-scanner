from scanner import check_tool_version

tools = ['npm', 'npx', 'snyk', 'semgrep', 'pip-audit', 'trufflehog']
for t in tools:
    v = check_tool_version(t)
    print(f"{t}: {v or 'not installed'}")
