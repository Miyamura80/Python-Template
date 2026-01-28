---
name: cleanup
description: Git branch hygiene - delete merged/closed branch, prune stale refs, sync dependencies
user_invocable: true
triggers:
  - /cleanup
---

# Git Cleanup Skill

Automates git branch hygiene after merging or closing PRs. Safely deletes merged branches (and force-deletes closed/abandoned branches), prunes stale remote tracking refs, syncs dependencies, and runs garbage collection.

## Workflow

Execute these steps in order:

### 1. Check current branch

```bash
git branch --show-current
```

Store the result as `CURRENT_BRANCH`.

### 2. Guard against main/master

If `CURRENT_BRANCH` is `main` or `master`:
- Report: "Already on main branch. No branch to clean up."
- Skip to step 7 (pull latest) and continue from there.

### 3. Check for uncommitted changes

```bash
git status --porcelain
```

If output is non-empty:
- Warn the user: "You have uncommitted changes. Please commit or stash them first."
- Stop and do not proceed.

### 4. Check if branch is merged or closed

First check for merged PRs:
```bash
gh pr list --state merged --head CURRENT_BRANCH --json number
```

If merged, proceed to step 5.

If not merged, check for closed PRs:
```bash
gh pr list --state closed --head CURRENT_BRANCH --json number
```

If closed (result is non-empty):
- Report: "Branch 'CURRENT_BRANCH' has a closed (unmerged) PR. Proceeding with deletion."
- Proceed to step 5 (will use force delete in step 6).

If neither merged nor closed:
- Check if the branch is merged locally: `git branch --merged main | grep -w CURRENT_BRANCH`
- If not merged anywhere, warn: "Branch 'CURRENT_BRANCH' does not appear to be merged or closed. Use `git branch -D` manually if you want to force delete."
- Stop and do not proceed.

Store whether the branch was `MERGED` or `CLOSED` for use in step 6.

### 5. Switch to main

```bash
git checkout main
```

### 6. Delete the branch

If branch was `MERGED`:
```bash
git branch -d CURRENT_BRANCH
```

If branch was `CLOSED` (PR closed without merging):
```bash
git branch -D CURRENT_BRANCH
```

Report: "Deleted branch CURRENT_BRANCH." (mention if force-deleted due to closed PR)

### 7. Pull latest

```bash
git pull origin main
```

### 8. Prune remote tracking refs

```bash
git fetch --prune
```

### 9. Delete stale local branches

Find and delete local branches whose upstream is gone:

```bash
git for-each-ref --format '%(refname:short) %(upstream:track)' refs/heads | while read branch track; do
  if [ "$track" = "[gone]" ]; then
    git branch -d "$branch" 2>/dev/null && echo "Deleted stale branch: $branch"
  fi
done
```

Report any branches deleted.

### 10. Sync dependencies

Detect package manager and sync:

- If `uv.lock` exists: `uv sync`
- Else if `bun.lockb` exists: `bun install`
- Else if `package-lock.json` exists: `npm install`
- Else if `requirements.txt` exists: `pip install -r requirements.txt`
- Else: Skip dependency sync

### 11. Git garbage collection

```bash
git gc --prune=now
```

### 12. Summary

Report completion:
- Branch deleted (if applicable)
- Number of stale branches pruned
- Dependencies synced (which package manager)
- Garbage collection complete

## Error Handling

- **Dirty working tree**: Stop immediately and ask user to commit/stash
- **Branch not merged or closed**: Warn and stop - never force delete without explicit user request
- **Branch closed (not merged)**: Force delete with `-D` since branch is abandoned
- **Already on main**: Skip branch deletion, continue with pull/prune/gc
- **No remote**: If `git pull` fails due to no remote, continue with local operations
- **gh CLI not available**: Fall back to `git branch --merged` check
