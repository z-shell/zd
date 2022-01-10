ARG VERSION=latest
FROM alpine:${VERSION}

ARG ZUSER=z-dev
ARG PUID=1000
ARG PGID=1000
ARG TERM=xterm-256color
ARG ZI_ZSH_VERSION
ARG APK_ADD

ENV ZUSER=${ZUSER} PUID=${PUID} PGID=${PGID} APK_ADD=${APK_ADD} \
  SHELL=/bin/zsh TERM=${TERM} ZI_ZSH_VERSION=${ZI_ZSH_VERSION}

RUN apk --no-cache --virtual base add coreutils curl jq git libuser rsync sudo zsh && \
  apk --no-cache --virtual zsh-build-tools add autoconf bash build-base ncurses-dev pcre-dev zlib-dev

RUN sed -ir 's#^(root:.+):/bin/ash#\1:/bin/zsh#' /etc/passwd && \
  adduser -D -s /bin/zsh -u "${PUID}" -h "/home/${ZUSER}" "${ZUSER}" && \
  printf "${ZUSER} ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/user && \
  mkdir -p /src /data /static && chown -R "${PUID}:${PGID}" /data /static

RUN ln -sfv /src/docker/zshenv /home/${ZUSER}/.zshenv && \
  ln -sfv /src/docker/zshrc /home/${ZUSER}/.zshrc

RUN if [ -f /home/${ZUSER}/bootstrap.sh ]; then \
  chmod u+x /home/${ZUSER}/bootstrap.sh; \
  /home/${ZUSER}/bootstrap.sh; \
  fi

WORKDIR /home/${ZUSER}
VOLUME ["/src", "/data"]

COPY --chown=${ZUSER} . /src

USER ${ZUSER}

RUN ZI_HOME_DIR=/static zsh -ils -c -- '@zi-scheduler burst'

CMD ["/bin/zsh"]
