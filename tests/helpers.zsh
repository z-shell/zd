# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et

# Run a zi snippet in a fresh isolated zsh subprocess.
# $1 — zsh code to execute (unescaped; single-quote at call site to prevent
#       expansion before the function receives it).
# $2 — optional zsh code to execute after initializing ZI and before sourcing Zi.
#
# Variable interpolation note: ${_zi_bin} and ${_zi_data} are expanded by the
# outer shell when the inner command string is assembled. References to $VAR
# inside the script argument resolve in the *inner* shell after zi is sourced.
# To pass an outer variable's value into the script, let it expand in the
# caller: zi_test "zi light ${my_plugin}"
zi_test() {
  local script=$1
  local pre_source=${2:-}
  local _zi_bin="${ZI_BIN:-${XDG_DATA_HOME:-${HOME}/.local/share}/zi/bin}"
  local _zi_data="${ZI_DATA:-${TMPDIR:-/tmp}/zunit}"
  run env NO_COLOR=1 TERM=dumb zsh -c "
    typeset -gxU path
    path=( \${HOME}/go/bin \$path )
    typeset -gA ZI
    ZI[HOME_DIR]='${_zi_data}'
    ${pre_source}
    source '${_zi_bin}/zi.zsh'
    autoload -Uz _zi
    ${script}
  "
}
