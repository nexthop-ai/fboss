# fboss-bug-scrub — evals

## Positive routing (skill MUST fire)
1. "Let's do a bug scrub of the FBOSS CLI Jira backlog and rank what to work on this week."
2. "Refresh the FBOSS CLI triage spreadsheet with the latest stars-ai-triage-auto heavy hitters from QPN."
3. "Which open NOS-346 / NOS-7785 tickets should the CLI team pick up? Put it in a CSV with notes."

## Negative routing (skill MUST NOT fire — expected skill in parens)
1. "Fingerprint this failing ConfigAclRuleTest run / file a STARS ticket." (stars-triage)
2. "Move NOS-16272 to In Progress and assign it to me." (jira-expert)
3. "Why does QPN's release-health page show no FBOSS data?" (qpn)
4. "How many StarsBot tickets were closed as duplicate last month?" (stars-dup-audit)
5. "Root-cause NOS-15884, the fboss_sw_agent FATAL after config commit." (systematic-debugging)

## Behavioral
- **E-cat3:** no ticket whose parent is NOS-5388 appears in the CSV.
- **E-status:** every row is New, Reopened, or Backlog; QPN tickets in other statuses are reported to the user as a watch list, not silently dropped.
- **E-heavy:** every QPN 7-day ticket with an open status is in the CSV even when it lacks the `stars-ai-triage-auto` label.
- **E-rank:** the top of the list is ordered by 7-day hits; tickets with high 30-day but zero 7-day hits carry a "verify fixed" note rather than being ranked top-10 or dropped.
- **E-tail:** long-tail STARS rows have an auto note stating age and 90-day hit count.
- **E-sheet:** the sheet is checked empty before writing; Jira IDs are HYPERLINK formulas; `gws` output is stripped of its first line before parsing.
