# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et
# Sourced by the inner shell after zi: programs installed with sbin or
# `go install' must land under the test home, not in a ZPFX or GOPATH the
# caller exported.
if [[ ${ZPFX} = "${ZI[HOME_DIR]}/polaris" && ${GOPATH} = "${HOME}/go" ]]; then
  print -r -- zpfx-isolated-ok
else
  print -r -- "zpfx-leaked: ZPFX=${ZPFX} GOPATH=${GOPATH} ZI[HOME_DIR]=${ZI[HOME_DIR]} HOME=${HOME}"
fi
