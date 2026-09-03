# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et
#
# A plug-in that leaves every kind of state unload is responsible for removing:
# a function, an alias, an $fpath entry, and a Plugin Standard unload callback.

0=${(%):-%N}
fpath+=( ${0:A:h}/functions )

_zd_unload_probe() { builtin print -r -- unload-probe-body }
alias _zd_unload_probe_alias='builtin print -r -- unload-probe-aliased'

# Recorded to a file rather than a parameter, because unload is entitled to
# remove parameters the plug-in created and the assertion runs afterwards.
@zsh-plugin-run-on-unload 'builtin print -r -- standard-callback-ran >> ${ZD_UNLOAD_LOG}'
