# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et
#
# A plug-in that immediately autoloads a function it does not own. `_main_complete'
# ships with Zsh, so resolving it requires the caller's $fpath to survive the
# autoload substitution. See z-shell/zi#488.
#
# The assertions live here rather than in the zi_test argument because zunit's
# `run' re-quotes and evals each word, so a `$' in that argument is not reliably
# deferred to the inner shell. A sourced file is parsed only by the inner shell.

autoload +X -Uz _main_complete

if [[ ${functions[_main_complete]} == *_comp_setup* ]]; then
  print -r -- foreign-autoload-ok
else
  print -r -- "foreign-autoload-broken: [${functions[_main_complete]}]"
fi
