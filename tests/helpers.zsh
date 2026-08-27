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
  local _test_home="${_zi_data}/home"
  local _test_zdotdir="${_zi_data}/zdotdir"
  local _test_config="${_zi_data}/config"
  local _test_cache="${_zi_data}/cache"
  mkdir -p "${_test_home}" "${_test_zdotdir}" "${_test_config}" "${_test_cache}"
  run env \
    HOME="${_test_home}" \
    ZDOTDIR="${_test_zdotdir}" \
    XDG_CONFIG_HOME="${_test_config}" \
    XDG_CACHE_HOME="${_test_cache}" \
    NO_COLOR=1 \
    TERM=dumb \
    zsh -f -c "
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
