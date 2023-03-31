#!/usr/bin/env bash
# -*- mode: bash; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=bash sw=2 ts=2 et

run_tests() {
  command cd -P -- "$(dirname -- "$(command -v -- "$0" || true)")" && pwd -P || exit 9
  zunit run --verbose "$@"
}

if [[ ${BASH_SOURCE[0]} == "${0}" ]]; then
  run_tests "$@"
fi
