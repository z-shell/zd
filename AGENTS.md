# Project Guidelines — zd

This project follows the organization-wide [Z-Shell Organization Guidelines](https://github.com/z-shell/.github/blob/main/AGENTS.md).

## What this is

`zd` provides Docker container images based on Debian trixie-slim with Zsh and Zi for local development and CI matrix validation across the Z-Shell ecosystem.

## Build & Test

- Build image: `make build`
- Run container test suite: `make test`
- Inspect container entrypoints: `bin/zd`
