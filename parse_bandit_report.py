#!/usr/bin/env python3
import json

with open('bandit-report.json', 'r') as f:
    data = json.load(f)

metrics = data['metrics']
results = data['results']

print("=" * 60)
print("BANDIT SECURITY SCAN SUMMARY")
print("=" * 60)
print(f"Files scanned: {metrics['_totals']['loc']} lines of code")
print(f"Total issues found: {len(results)}")

# Count by severity
severity_counts = {}
for r in results:
    sev = r['issue_severity']
    severity_counts[sev] = severity_counts.get(sev, 0) + 1

print("\nSeverity Breakdown:")
for sev in ['HIGH', 'MEDIUM', 'LOW']:
    count = severity_counts.get(sev, 0)
    print(f"  {sev}: {count}")

# Count by confidence
confidence_counts = {}
for r in results:
    conf = r['issue_confidence']
    confidence_counts[conf] = confidence_counts.get(conf, 0) + 1

print("\nConfidence Breakdown:")
for conf in ['HIGH', 'MEDIUM', 'LOW']:
    count = confidence_counts.get(conf, 0)
    print(f"  {conf}: {count}")

# Show top 10 issues by severity
print("\n" + "=" * 60)
print("TOP 10 CRITICAL ISSUES (HIGH severity, HIGH confidence)")
print("=" * 60)
critical = [r for r in results if r['issue_severity'] == 'HIGH' and r['issue_confidence'] == 'HIGH']
for i, issue in enumerate(critical[:10], 1):
    print(f"\n{i}. {issue['test_name']} - {issue['issue_text']}")
    print(f"   File: {issue['filename']}:{issue['line_number']}")
    print(f"   Severity: {issue['issue_severity']}, Confidence: {issue['issue_confidence']}")
