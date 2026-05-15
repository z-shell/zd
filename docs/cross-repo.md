# Cross-Repo Integration

`test-native.yml` is published as a reusable GitHub Actions workflow via the `workflow_call` trigger. Any repository in (or outside) the Z-Shell ecosystem can call it to run the full ZUnit suite against a specific Zi commit, branch, or tag — without maintaining a copy of the test infrastructure.

## How it works

When called with `zi_repo` and `zi_ref` inputs, `test-native.yml` clones that exact revision of Zi directly instead of using the default install script. The rest of the workflow is identical: the full test matrix runs (`annexes`, `ice`, `packages`, `plugins`, `snippets`), and results appear in the caller's GitHub Actions UI.

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
    uses: z-shell/zd/.github/workflows/test-native.yml@main
    with:
      zi_repo: z-shell/zi # the repo being tested
      zi_ref: ${{ github.sha }} # the exact commit under test
```

**What each field does:**

| Field                                                     | Purpose                                                            |
| --------------------------------------------------------- | ------------------------------------------------------------------ |
| `uses: z-shell/zd/.github/workflows/test-native.yml@main` | Calls the reusable workflow at the `main` ref of `zd`              |
| `zi_repo: z-shell/zi`                                     | Tells `zd` to clone this repo instead of using the default install |
| `zi_ref: ${{ github.sha }}`                               | Pins to the exact commit that triggered the caller's workflow      |

The caller's `GITHUB_TOKEN` is used automatically — no additional secrets are required. Both repositories must be public.

---

## Input reference

| Input     | Type     | Required | Default | Description                                                                                |
| --------- | -------- | -------- | ------- | ------------------------------------------------------------------------------------------ |
| `zi_repo` | `string` | No       | `""`    | GitHub repo for Zi in `owner/name` format. When empty, the default install script is used. |
| `zi_ref`  | `string` | No       | `main`  | Branch name, tag, or full commit SHA to check out.                                         |

---

## Choosing `zi_ref`

**`${{ github.sha }}`** — use this in pull request workflows. Tests the exact commit under review. No ambiguity about what is being tested.

```yaml
zi_ref: ${{ github.sha }}
```

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

The `uses:` line can reference `zd` by branch or by tag:

```yaml
# Always use the latest zd (may include breaking changes)
uses: z-shell/zd/.github/workflows/test-native.yml@main

# Pin to a specific zd release (stable, auditable)
uses: z-shell/zd/.github/workflows/test-native.yml@v1.0.0

# Pin to a specific commit SHA (most stable)
uses: z-shell/zd/.github/workflows/test-native.yml@a1b2c3d
```

For production CI in a release-tracked repo, pinning to a tag or SHA is recommended. For development repos following Zi's `main` branch, `@main` is sufficient.
