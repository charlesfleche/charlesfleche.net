Title: Working on several branches at once with git worktree
Description: One repository, several checkouts side by side
Tags: [git, claude]

I discovered `git worktree` while asking Claude to work on several features in parallel. Agents editing the same checkout would step on each other's toes, so each one got its own worktree instead.

A worktree is an additional working directory attached to the same repository. All worktrees share the same `.git` history, objects and branches, but each has its own checked out branch, index and files on disk. No need to `git stash` or clone the repository a second time to work on another branch.

```bash
# Create ../myrepo-feature-a with a new branch feature-a
git worktree add -b feature-a ../myrepo-feature-a

# Check out an existing branch in another directory
git worktree add ../myrepo-fix fix-typo

# List the worktrees
git worktree list

# Remove a worktree once the branch is merged
git worktree remove ../myrepo-feature-a
```

A commit made in one worktree is immediately visible from the others, as they are the same repository. The only rule: a branch can be checked out in a single worktree at a time.
