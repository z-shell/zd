#!/usr/bin/env sh

HOME="/home/${ZUSER}"
export HOME

command sed -i -r 's#^(root:.+):/bin/ash#\1:/bin/zsh#' /etc/passwd
command adduser -D -s /bin/zsh -u "${PUID}" -h "${HOME}" "${ZUSER}"

command printf '%s' "${ZUSER} ALL=(ALL) NOPASSWD: ALL" >/etc/sudoers.d/user
command mkdir -p /src /data
command chown -R "${PUID}:${PGID}" /src /data
