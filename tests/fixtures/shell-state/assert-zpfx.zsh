# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et
# Sourced by the inner shell after zi: programs installed with sbin must land
# under the test data directory, not in a ZPFX the caller exported.
if [[ ${ZPFX} = ${ZI[HOME_DIR]}/polaris ]]; then
  print -r -- zpfx-isolated-ok
else
  print -r -- "zpfx-leaked: ZPFX=${ZPFX} ZI[HOME_DIR]=${ZI[HOME_DIR]}"
fi
