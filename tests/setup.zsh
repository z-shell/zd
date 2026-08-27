#!/usr/bin/env zunit
# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et

setup() {
  export ZI_DATA="${ZI_DATA:-${TMPDIR:-/tmp}/zunit}"

  {
    color magenta @setup started
    color magenta "ZI_DATA=${ZI_DATA}"
  } >&2

  [[ ${ZI_DATA} = /* && ${ZI_DATA} != / ]] || {
    print -u2 -r -- "Refusing unsafe ZI_DATA: ${ZI_DATA}"
    return 1
  }

  # Preserve mount points while clearing hidden and ordinary test artifacts.
  mkdir -p -- "${ZI_DATA}"
  local -a artifacts=( "${ZI_DATA}"/*(DN) )
  if (( ${#artifacts} )); then
    chmod -R u+rwX -- "${artifacts[@]}"
    rm -rf -- "${artifacts[@]}"
  fi
}
