# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et
#
# Sourced after `zi unload'. Everything the plug-in put into the shell has to be
# gone, and the Plugin Standard callback has to have run while it was going.

if (( ${+functions[_zd_unload_probe]} )); then
  builtin print -r -- "unload-broken: the plug-in's function survived unload"
elif (( ${+aliases[_zd_unload_probe_alias]} )); then
  builtin print -r -- "unload-broken: the plug-in's alias survived unload"
elif [[ ${(j.:.)fpath} != ${ZD_FPATH_BEFORE} ]]; then
  builtin print -r -- "unload-broken: \$fpath was not restored"
elif [[ ! -s ${ZD_UNLOAD_LOG} ]]; then
  builtin print -r -- "unload-broken: the @zsh-plugin-run-on-unload callback did not run"
else
  builtin print -r -- unload-shell-state-ok
fi
