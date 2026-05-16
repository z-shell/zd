#!/usr/bin/env sh

HOME="/home/${ZUSER}"
export HOME

# Change root's default shell from bash to zsh.
command sed -i -r 's#^(root:.+):/bin/bash#\1:/bin/zsh#' /etc/passwd

# Create the unprivileged user with a home directory and zsh as login shell.
command useradd -m -s /bin/zsh -u "${PUID}" "${ZUSER}"

command printf '%s\n' "${ZUSER} ALL=(ALL) NOPASSWD: ALL" >/etc/sudoers.d/user
command mkdir -p /src /data
command chown -R "${PUID}:${PGID}" /src /data
