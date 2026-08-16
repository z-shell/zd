# zd — Zi Docker Testing Environment

`zd` is the official test harness for the [Zi](https://github.com/z-shell/zi) plugin manager. It provides a ZUnit test suite that verifies Zi commands work correctly — plugin installation, snippet loading, ice modifiers, annexes, and packages. The suite runs natively on CI for every pull request and inside Docker containers for Zsh version compatibility testing. It also works as a reusable workflow so other repos in the Z-Shell ecosystem can test against a specific Zi commit.

The image is based on **Debian trixie-slim** (`debian:trixie-slim`), providing full glibc compatibility and the breadth of the `apt` ecosystem — making it straightforward to add test dependencies or use the container as an interactive development environment.

## Architecture

```text
                    ┌─────────────────────────────────┐
                    │         test-native.yml          │
  push / PR ───────▶│  ubuntu-latest · zsh from apt   │
  schedule          │  one job per .zunit file (fast)  │
  workflow_call ───▶│  supports zi_repo + zi_ref input │
                    └─────────────────────────────────┘

                    ┌─────────────────────────────────┐
  weekly ──────────▶│         test-matrix.yml          │
  workflow_dispatch │  Docker · Zsh 5.5.1 – 5.9        │
                    │  one job per Zsh version          │
                    └─────────────────────────────────┘

                    ┌─────────────────────────────────┐
  local ───────────▶│            Makefile              │
                    │  make test / run / shell / build │
                    └─────────────────────────────────┘
```

Native CI catches regressions on every merge. The Docker matrix verifies Zsh version compatibility on a weekly cadence without blocking pull requests. The Makefile gives contributors a local workflow identical to CI.

## Quick Start

```sh
# Run the full ZUnit suite natively (installs zunit on first run)
make test

# Run a single ad-hoc zi command in Docker
make run CMD="zi light z-shell/z-a-bin-gem-node"

# Open an interactive shell with zi already loaded
make shell
```

Pull the prebuilt image directly:

```sh
docker run --rm -it ghcr.io/z-shell/zd:latest
docker run --rm -it ghcr.io/z-shell/zd:zsh-5.9
```

## Documentation

| Topic                                                      | File                                           |
| ---------------------------------------------------------- | ---------------------------------------------- |
| Local testing — Makefile targets, env vars, Docker         | [docs/local-testing.md](docs/local-testing.md) |
| CI workflows — triggers, inputs, caching                   | [docs/ci-workflows.md](docs/ci-workflows.md)   |
| Cross-repo integration — test your zi PR from another repo | [docs/cross-repo.md](docs/cross-repo.md)       |
| Writing tests — zi_test, assertions, adding suites         | [docs/writing-tests.md](docs/writing-tests.md) |

## Available Image Tags

| Tag         | Zsh version          |
| ----------- | -------------------- |
| `latest`    | Debian's default Zsh (5.9) |
| `zsh-5.5.1` | 5.5.1                |
| `zsh-5.6.2` | 5.6.2                |
| `zsh-5.7.1` | 5.7.1                |
| `zsh-5.8`   | 5.8                  |
| `zsh-5.8.1` | 5.8.1                |
| `zsh-5.9`   | 5.9                  |

Images are published to `ghcr.io/z-shell/zd` on every push to `main` and on a weekly schedule.

## Contributing

1. Fork the repo and create a branch.
2. Add or edit test files in `tests/`.
3. Run `make test` to verify locally.
4. Open a pull request — CI runs the full suite automatically.

See [docs/writing-tests.md](docs/writing-tests.md) for the test authoring guide.
