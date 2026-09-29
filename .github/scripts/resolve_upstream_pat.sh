#!/usr/bin/env bash
# Pick the PAT a workflow should use for an upstream facebook/fboss PR: the PR
# author's own <AUTHOR>_UPSTREAM_REBASE secret when it exists and works, else the
# shared rabbit PAT. Shared by rebase-upstream-pr.yml and
# autorebase-upstream-prs.yml.
#
# GitHub only lets *expressions* index the secrets context, so a caller runs
# this in two steps:
#   derive <pr>   look up the author, print login/user/secret_name/head_author
#                 to $GITHUB_OUTPUT (needs GH_TOKEN with read on facebook/fboss);
#   pick          with CANDIDATE=${{ secrets[<secret_name>] }} plus SECRET_NAME,
#                 LOGIN, AUTHOR_USER, HEAD_AUTHOR from derive, validate it and
#                 print token_secret/git_name/git_email to $GITHUB_OUTPUT. Only
#                 the secret *name* is emitted; job outputs cannot carry values.
#
# pick falls back (with a ::warning:: naming the reason) when the secret is
# unset, rejected by the API (expired/revoked), owned by someone other than the
# PR author, or cannot push to nexthop-ai/fboss and private-fboss.
set -euo pipefail

UPSTREAM_REPO=${UPSTREAM_REPO:-facebook/fboss}
PUSH_REPOS=${PUSH_REPOS:-"nexthop-ai/fboss nexthop-ai/private-fboss"}
FALLBACK_SECRET=${FALLBACK_SECRET:-RABBIT_NEXTHOP_PAT}
FALLBACK_NAME=${FALLBACK_NAME:-rabbit-nexthop}
FALLBACK_EMAIL=${FALLBACK_EMAIL:-rabbit@nexthop.ai}
OUT=${GITHUB_OUTPUT:-/dev/stdout}

derive() {
  local pr=$1 login user secret_name head_author
  login=$(gh api "repos/${UPSTREAM_REPO}/pulls/${pr}" --jq .user.login)
  # Same login -> user mapping as rebase_upstream_pr.py (author_user).
  user=$(printf '%s' "${login,,}" | sed -e 's/-nexthop$//' -e 's/[^a-z0-9_.-]/-/g')
  secret_name=$(printf '%s' "${user^^}" | sed 's/[^A-Z0-9]/_/g')_UPSTREAM_REBASE
  # The PR's own commits carry the author's git name; profiles often have none.
  head_author=$(gh api "repos/${UPSTREAM_REPO}/pulls/${pr}/commits" --jq '.[-1].commit.author.name')
  echo "PR #${pr} author: ${login} -> user '${user}' -> secret ${secret_name}"
  {
    echo "login=${login}"
    echo "user=${user}"
    echo "secret_name=${secret_name}"
    echo "head_author=${head_author}"
  } >>"$OUT"
}

fallback() {
  echo "::warning::${SECRET_NAME}: $1 -- falling back to ${FALLBACK_SECRET}"
  {
    echo "token_secret=${FALLBACK_SECRET}"
    echo "git_name=${FALLBACK_NAME}"
    echo "git_email=${FALLBACK_EMAIL}"
  } >>"$OUT"
  exit 0
}

pick() {
  : "${SECRET_NAME:?}" "${LOGIN:?}" "${AUTHOR_USER:?}"
  [ -n "${CANDIDATE:-}" ] || fallback "secret not set"
  export GH_TOKEN="$CANDIDATE"
  local me repo token_login name
  # /user fails with 401 for an expired or revoked token.
  me=$(gh api user 2>/dev/null) || fallback "token rejected (expired or revoked?)"
  for repo in $PUSH_REPOS; do
    [ "$(gh api "repos/${repo}" --jq '.permissions.push' 2>/dev/null)" = "true" ] ||
      fallback "no push access to ${repo}"
  done
  token_login=$(jq -r .login <<<"$me")
  [ "$token_login" = "$LOGIN" ] || fallback "token belongs to ${token_login}, not PR author ${LOGIN}"
  name=$(jq -r '.name // empty' <<<"$me")
  name=${name:-${HEAD_AUTHOR:-$token_login}}
  echo "Using ${SECRET_NAME} (${token_login})"
  {
    echo "token_secret=${SECRET_NAME}"
    echo "git_name=${name}"
    echo "git_email=${AUTHOR_USER}@nexthop.ai"
  } >>"$OUT"
}

case "${1:-}" in
derive) derive "${2:?usage: $0 derive <pr>}" ;;
pick) pick ;;
*)
  echo "usage: $0 derive <pr> | pick" >&2
  exit 2
  ;;
esac
