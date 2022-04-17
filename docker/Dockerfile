ARG VERSION=latest
FROM alpine:${VERSION}

ARG ZUSER=z-user
ARG PUID=1000
ARG PGID=1000
ARG TERM=xterm-256color
ARG ZI_ZSH_VERSION
ARG APK_ADD

ENV ZUSER=${ZUSER} PUID=${PUID} PGID=${PGID} APK_ADD=${APK_ADD} \
  SHELL=/bin/zsh TERM=${TERM} ZI_ZSH_VERSION=${ZI_ZSH_VERSION}

RUN apk --no-cache --virtual base add coreutils curl jq git libuser rsync sudo zsh ncurses-dev pcre-dev zlib-dev && \
  apk --no-cache --virtual zsh-build-tools add autoconf bash build-base go vim && \
  sed -ir 's#^(root:.+):/bin/ash#\1:/bin/zsh#' /etc/passwd && \
  adduser -D -s /bin/zsh -u "${PUID}" -h "/home/${ZUSER}" "${ZUSER}" && \
  printf "${ZUSER} ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/user && \
  mkdir -p /src /data /static && chown -R "${PUID}:${PGID}" /src /data /static
RUN cp -fv /src/docker/zshenv /home/${ZUSER}/.zshenv && \
  cp -fv /src/docker/zshrc /home/${ZUSER}/.zshrc

WORKDIR /home/${ZUSER}
VOLUME ["/src", "/data"]
COPY --chown=${ZUSER} . /src

RUN git clone https://github.com/z-shell/zi.git /home/${ZUSER}/.zi/bin
RUN ZI_HOME_DIR=/home/${ZUSER}/.zi ZI_BIN_DIR=/home/${ZUSER}/.zi/bin zsh -ils -c -- '@zi-scheduler burst | true'
CMD ["/bin/zsh", "-il"]
