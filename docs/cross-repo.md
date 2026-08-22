# Cross-Repo Integration

`test-native.yml` is published as a reusable GitHub Actions workflow via the `workflow_call` trigger. Any repository in (or outside) the Z-Shell ecosystem can call it to run the full ZUnit suite against a specific Zi commit, branch, or tag — without maintaining a copy of the test infrastructure.

## How it works

When called with `zi_repo` and `zi_ref` inputs, `test-native.yml` clones that
exact revision of Zi directly instead of using the default install script.
Callers may set `include_compat: true` to add the promotion-specific `compat`
suite to the standard matrix (`annexes`, `ice`, `packages`, `plugins`,
`snippets`). Results appear in the caller's GitHub Actions UI. Keep
`include_compat` false for hotfixes based on Zi's stable `main` branch; enable it
for a reviewed `next` promotion candidate.

This means a Zi pull request can trigger `zd` tests as part of its own CI pipeline, catching regressions in the test suite before the PR is merged.

---

## End-to-end example

Add this file to the repository you want to test from (e.g. `z-shell/zi`):

```yaml
# .github/workflows/zd-integration.yml
name: "zd integration tests"

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  zd:
    name: "ZUnit suite"
    permissions:
      contents: read
    uses: z-shell/zd/.github/workflows/test-native.yml@main
    with:
      zi_repo: z-shell/zi # the repo being tested
      # PRs use the head commit, not GitHub's synthetic merge commit.
      zi_ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}
      include_compat: ${{ github.head_ref == 'next' }}
```

**What each field does:**

| Field                                                                                                      | Purpose                                                                    |
| ---------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `permissions: contents: read`                                                                              | Grants only the repository access required by the reusable workflow        |
| `uses: z-shell/zd/.github/workflows/test-native.yml@main`                                                  | Calls the reusable workflow at the `main` ref of `zd`                      |
| `zi_repo: z-shell/zi`                                                                                      | Tells `zd` to clone this repo instead of using the default install         |
| `zi_ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha \|\| github.sha }}` | Pins PRs to their head commit and pushes to the commit that triggered them |
| `include_compat: ${{ github.head_ref == 'next' }}`                                                         | Adds promotion compatibility tests only for a `next` candidate             |

The caller's `GITHUB_TOKEN` is used automatically — no additional secrets are required. Both repositories must be public.

---

## Input reference

| Input            | Type      | Required | Default | Description                                                                                |
| ---------------- | --------- | -------- | ------- | ------------------------------------------------------------------------------------------ |
| `zi_repo`        | `string`  | No       | `""`    | GitHub repo for Zi in `owner/name` format. When empty, the default install script is used. |
| `zi_ref`         | `string`  | No       | `main`  | Branch name, tag, or full commit SHA to check out.                                         |
| `include_compat` | `boolean` | No       | `false` | Add the promotion-specific compatibility suite to the standard matrix.                     |

---

## Choosing `zi_ref`

**Exact commit SHA** — use immutable SHAs for both pull requests and pushes. For a pull request, `github.sha` is a synthetic merge commit, so pass `github.event.pull_request.head.sha`. For a push, pass `github.sha`.

```yaml
zi_ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}
```

The workflow recognizes a full 40-character hexadecimal value as an immutable commit SHA, fetches that object directly, and verifies that the checked-out commit matches it exactly.

**Branch name** — tracks a branch continuously. Useful for nightly runs against `main` without tying to a specific commit.

```yaml
zi_ref: main
zi_ref: develop
```

**Tag** — pins to a release. Use this when you want a stable baseline, not the latest development state.

```yaml
zi_ref: v1.2.3
```

---

## Permissions and tokens

`workflow_call` inherits the `GITHUB_TOKEN` from the calling workflow. The token is scoped to the caller's repository with read permissions on `contents`. No secrets need to be shared between repositories.

`zd` only performs outbound network requests (to install `zunit` and clone `zi_repo`) — it does not write back to either repository.

---

## Pinning the zd version

The `uses:` line can reference `zd` by branch, tag, or commit SHA:

```yaml
# Always use the latest zd (may include breaking changes)
uses: z-shell/zd/.github/workflows/test-native.yml@main

# Pin to a specific zd release (stable, auditable)
uses: z-shell/zd/.github/workflows/test-native.yml@v1.0.0

# Pin to a full commit SHA (most stable)
uses: z-shell/zd/.github/workflows/test-native.yml@a1b2c3d4e5f678901234567890abcdef12345678
```

For production CI, pin the reusable workflow itself to a full commit SHA. Branches and tags remain useful for development or release tracking but are mutable references.
