#!/usr/bin/env bash
set -euo pipefail

bypass_label="no-jira"
jira_issue_key_pattern='(^|[^[:alnum:]_])(CMS|DPD)-[0-9]+([^[:alnum:]_]|$)'
branch_name="${BRANCH_NAME:-$(git symbolic-ref --quiet --short HEAD 2>/dev/null || true)}"

if [[ -z "${branch_name}" ]]; then
    echo "Unable to determine the current branch name for validation." >&2
    exit 1
fi

shopt -s nocasematch
if [[ "${branch_name}" == dependabot/* ]] || [[ "${branch_name}" == *"${bypass_label}"* ]]; then
    echo "Skipping branch name validation for bypass branch '${branch_name}'."
    shopt -u nocasematch
    exit 0
fi
shopt -u nocasematch

if [[ ! "${branch_name}" =~ ${jira_issue_key_pattern} ]]; then
    echo "Branch name must contain a Jira issue key in the form CMS-<number> or DPD-<number>. Optionally, use '${bypass_label}' in the branch name or on the PR. Got '${branch_name}'." >&2
    exit 1
fi

echo "Branch name contains a valid Jira issue key."
