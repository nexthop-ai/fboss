#!/usr/bin/env bash
# Fetch open FBOSS CLI bug candidates from Jira (acli) and QPN into $1.
set -euo pipefail
OUT=${1:?usage: fetch.sh <outdir>}
mkdir -p "$OUT/meta"
cd "$OUT"
F="key,summary,status,priority,reporter,assignee,labels,description"
ST='status in (New, Reopened, Backlog)'
acli jira workitem search --jql "parent = NOS-346 AND $ST" --fields "$F" --paginate --json >j1.json
acli jira workitem search --jql "parent = NOS-7785 AND $ST" --fields "$F" --paginate --json >j2.json
acli jira workitem search --jql "parent = NOS-5388 AND $ST" --fields "key,summary" --paginate --json >j3.json
acli jira workitem search --jql "labels = stars-ai-triage-auto AND $ST" --fields "$F" --paginate --json >j4all.json
for d in 7 30 90; do
  curl -sf "https://qpn.sw.internal.nexthop.ai/api/v1/stars/top-bugs?os=fboss&package=cli&days=$d&source=t_recs&limit=200" >top$d.json
done
jq -r '.items[].ticket_id' top90.json | sort -u >qpn90.keys
jq -r '.[].key' j4all.json | sort -u >j4all.keys
jq -r '.[] | select((.fields.summary + " " + (.fields.description|tostring)) | test("fboss2|cli/fboss2|package: cli"; "i")) | .key' j4all.json | sort -u >j4cli.keys
comm -12 qpn90.keys j4all.keys >qpn_in_stars.keys
# QPN heavy hitters that the label query missed: keep those still open.
comm -23 qpn90.keys j4all.keys >qpn_unlabeled.keys
: >qpn_extra.keys
while read -r k; do
  st=$(jq -r --arg k "$k" '.items[] | select(.ticket_id==$k) | .jira.status' top90.json | head -1)
  case "$st" in NEW | New | Reopened | Backlog) echo "$k" >>qpn_extra.keys ;; esac
done <qpn_unlabeled.keys
cat qpn_in_stars.keys j4cli.keys qpn_extra.keys | sort -u >cat4.keys
{
  jq -r '.[].key' j1.json j2.json
  cat cat4.keys
} | sort -u >all.keys

# Per-platform hit breakdown (90d): QPN timeline grouped by model, for tickets that
# have hits. The timeline's per-model sum reconciles exactly with hit_count; one
# request per ticket. (A `model=<name>` filter on /top-bugs also works but is one
# request per platform.)
jq -r '.items[].ticket_id' top7.json top30.json top90.json | sort -u >hit.keys
comm -12 hit.keys all.keys >hit_our.keys
: >platforms.jsonl
xargs -P 8 -I{} sh -c '
  curl -sf "https://qpn.sw.internal.nexthop.ai/api/v1/stars/top-bugs/timeline?ticket_id={}&group_by=model&os=fboss&package=cli&days=90&source=t_recs" \
  | jq -c --arg k {} "{key:\$k,days:90,totals:([.points[].counts|to_entries[]]|group_by(.key)|map({key:.[0].key,value:(map(.value)|add)})|from_entries)}" || true
' <hit_our.keys >>platforms.jsonl

# Codename prefixes: /hits pairs each event's `model` with its `testbed`, so the
# testbed prefix (stlr, wdg, ...) is derived rather than hardcoded. One file per
# ticket — concurrent appends of >4KB lines are not atomic and corrupt a shared
# file. build_csv.py reduces these pairs to model -> most-common-prefix.
mkdir -p platform_pairs
rm -f platform_pairs/*.json
xargs -P 8 -I{} sh -c '
  if curl -sf "https://qpn.sw.internal.nexthop.ai/api/v1/stars/top-bugs/hits?ticket_id={}&os=fboss&package=cli&days=90&source=t_recs&limit=1000" \
       | jq -c "[.items[]|{model,testbed}]" > platform_pairs/{}.json; then :; else rm -f platform_pairs/{}.json; fi
' <hit_our.keys

xargs -P 8 -I{} sh -c 'acli jira workitem view {} --fields "key,summary,status,priority,reporter,assignee,labels,created,updated,components,parent,customfield_10388,issuetype,resolution,description" --json > meta/{}.json 2>/dev/null' <all.keys
echo "cat1=$(jq length j1.json) cat2=$(jq length j2.json) cat3(excluded)=$(jq length j3.json) cat4=$(wc -l <cat4.keys) (unlabeled heavy hitters added: $(tr '\n' ' ' <qpn_extra.keys))"
echo "QPN tickets excluded by status (watch list):"
comm -23 qpn_unlabeled.keys qpn_extra.keys | while read -r k; do jq -r --arg k "$k" '.items[] | select(.ticket_id==$k) | "  \(.ticket_id)\t\(.jira.status)\t\(.hit_count) hits/90d\t\(.jira.summary)"' top90.json | head -1; done
