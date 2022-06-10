#!/usr/bin/env bash
# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et

run_tests() {
  cd "$(
    cd "$(dirname "$0")" >/dev/null 2>&1
    pwd -P
  )/.." || exit 9

  zunit run --verbose "$@"
}

if [[ ${BASH_SOURCE[0]} == "${0}" ]]; then
  run_tests "$@"
fi
