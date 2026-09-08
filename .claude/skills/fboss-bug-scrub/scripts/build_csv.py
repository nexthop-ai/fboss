#!/usr/bin/env python3
"""Build the ranked bug-scrub CSV (+ Sheets body.json) from fetch.sh output.

Optional inputs in the same dir: notes.json {key: note}, order.json [keys best-first].
Unranked rows fall through to the rule-based order and auto notes."""
import csv, datetime as dt, glob, json, os, re, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
os.chdir(OUT)
today = dt.date.today()
load = lambda f: json.load(open(f))
j1, j2, j4all = load('j1.json'), load('j2.json'), load('j4all.json')
cat4keys = set(open('cat4.keys').read().split())
meta = {os.path.basename(p)[:-5]: load(p) for p in glob.glob('meta/*.json')}
notes = load('notes.json') if os.path.exists('notes.json') else {}
order = {k: i for i, k in enumerate(load('order.json'))} if os.path.exists('order.json') else {}
qpn = {}
for d in (7, 30, 90):
    for it in load(f'top{d}.json')['items']:
        qpn.setdefault(it['ticket_id'], {})[d] = it

rows = {}
def add(key, f, cat):
    m = meta.get(key, {}).get('fields', {})
    created = (m.get('created') or f.get('created') or '')[:10]
    q = qpn.get(key, {})
    h = lambda d: q[d]['hit_count'] if d in q else 0
    rows[key] = dict(
        key=key, cat=cat, status=f['status']['name'], prio=(f.get('priority') or {}).get('name', ''),
        reporter=(f.get('reporter') or {}).get('displayName', ''),
        assignee=(f.get('assignee') or {}).get('displayName', '') or '',
        comps='|'.join(c['name'] for c in m.get('components', [])), labels='|'.join(f.get('labels', [])),
        created=created, age=(today - dt.date.fromisoformat(created)).days if created else '',
        h7=h(7), h30=h(30), h90=h(90),
        trend=q[7]['trend'] if 7 in q else (q[30]['trend'] if 30 in q else ''),
        last=q[90]['last_seen'][:10] if 90 in q else '', title=f['summary'].strip())

for i in j1: add(i['key'], i['fields'], '1-Mosaic NOS-346')
for i in j2: add(i['key'], i['fields'], '2-FBOSS Problems NOS-7785')
for i in j4all:
    if i['key'] in cat4keys: add(i['key'], i['fields'], '4-STARS auto-triage')
for k in cat4keys - set(rows):          # QPN heavy hitters without the label
    if k in meta: add(k, meta[k]['fields'], '4-STARS auto-triage')

CLI_RE = re.compile(r'fboss2|\bcli\b|config session|rollback|config reload|show ')
def cli_flag(r):
    if r['cat'][0] in '14': return 'Yes'
    return 'Yes' if CLI_RE.search(r['title'].lower()) else 'No'

def auto_note(r):
    t = r['title']; wk = r['age'] // 7 if r['age'] != '' else '?'
    if r['cat'][0] == '4':
        if r['h90'] == 0:
            return f"STARS auto-triage; opened {wk} weeks ago, 0 CLI-package hits in the last 90 days. Long tail; candidate for WONTFIX/close if it stays quiet."
        return f"STARS auto-triage; opened {wk} weeks ago, {r['h7']} hits in 7d / {r['h90']} in 90d. Long tail; revisit only if hit count grows."
    if r['cat'][0] == '1':
        role = ', '.join(l for l in r['labels'].split('|') if l.startswith('mosaic-cli-')) or 'no role label'
        if re.match(r'(Implement fboss2 config|FBOSS: fboss2|FBOSS CLI|FBOSS:)', t):
            return f"Mosaic CLI spec command not yet implemented ({role}). Feature gap, not a bug; confirm with the requester whether still needed before Mosaic closes."
        return "Mosaic epic item; feature/infra work rather than a bug. Low priority for a bug scrub."
    if cli_flag(r) == 'No':
        return f"Not a CLI bug (component: {r['comps'] or 'n/a'}); belongs to platform/BMC/SAI/routing owners. Listed for completeness, out of scope for the CLI scrub."
    return "FBOSS problem touching the CLI surface; needs a shallow look to confirm owner."

PR = {'P1': 0, 'P2': 1, 'P3': 2, 'P4': 3}
def score(r):
    k = r['key']
    if k in order: return (0, order[k])
    pr = PR.get(r['prio'], 4)
    if r['cat'][0] == '4': return (1, -(r['h7'] * 10 + r['h90']))
    if r['cat'][0] == '2': return (2 if cli_flag(r) == 'Yes' else 3, pr, r['created'])
    lab = r['labels']; t = r['title'].lower()
    return (4, pr, 0 if ('mosaic-cli-fsw' in lab or 'mosaic-cli-rsw' in lab) else 1, 0 if 'config' in t else 1, r['created'])

out = sorted(rows.values(), key=score)
cols = ['Jira ID', 'Category', 'CLI related', 'Status', 'Priority', 'Reporter', 'Assignee', 'Components',
        'Created', 'Age (days)', 'Hits 7d', 'Hits 30d', 'Hits 90d', 'Trend', 'Last seen', 'Title', 'Notes']
grid = [cols]
for r in out:
    grid.append([r['key'], r['cat'], cli_flag(r), r['status'], r['prio'], r['reporter'], r['assignee'], r['comps'],
                 r['created'], r['age'], r['h7'] or '', r['h30'] or '', r['h90'] or '', r['trend'], r['last'],
                 r['title'], notes.get(r['key']) or auto_note(r)])
with open('fboss_cli_bug_scrub.csv', 'w', newline='') as fh:
    csv.writer(fh).writerows(grid)
sheet = [list(grid[0])] + [[f'=HYPERLINK("https://nexthopai.atlassian.net/browse/{row[0]}","{row[0]}")', *row[1:]] for row in grid[1:]]
json.dump({'values': sheet}, open('body.json', 'w'))
missing = [k for k in order if k not in rows]
print(f"{len(out)} rows, {sum(k in rows for k in notes)} hand-noted -> {OUT}/fboss_cli_bug_scrub.csv, body.json"
      + (f"; order.json keys not found: {missing}" if missing else ''))
