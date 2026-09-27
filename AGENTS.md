# Project Guidelines — zd

This project follows the organization-wide [Z-Shell Organization Guidelines](https://github.com/z-shell/.github/blob/main/AGENTS.md).

## What this is

`zd` provides Docker container images based on Debian trixie-slim with Zsh and Zi for local development and CI matrix validation across the Z-Shell ecosystem.

## Build & Test

- Build image: `make build`
- Run the Zi ZUnit suite natively: `make test`
- Build controlled profiles: `make controlled-build PROFILE=module-build ZSH_VERSION=5.9.2 ZSH_PATCH_SET=trap-bounds-a3547fd4`
- Test the execution contract: `python3 -m unittest discover -s tests -p 'test_zd.py' -v`
- Run repository-owned commands with `bin/zd run`; read [the execution contract](docs/controlled-execution.md).

The existing interactive image initializes Zi. Controlled `runtime` and
`module-build` profiles have no user configuration or automatic Zi loading.
Use exact image digests and explicit runtime patch profiles for reproducible
validation. Container checks supplement the owning repository's native tests.
