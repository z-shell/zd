ARG VERSION=latest
FROM alpine:${VERSION}
LABEL maintainer="<%= Z-Shell Community %>"
LABEL email="<%= team@zshell.dev =%>"

ARG HOSTNAME=zi@docker
ARG ZUSER=z-user
ARG PUID=1000
ARG PGID=1000
ARG TERM=xterm-256color
ARG ZI_ZSH_VERSION
ARG APK_ADD

ENV ZUSER=${ZUSER} PUID=${PUID} \
PGID=${PGID} APK_ADD=${APK_ADD} \
SHELL=/bin/zsh HOSTNAME=zi@docker DIR=/static \
TERM=${TERM} ZI_ZSH_VERSION=${ZI_ZSH_VERSION}

# trunk-ignore(hadolint/DL3018)
RUN apk --no-cache --virtual base add coreutils curl \
jq git libuser rsync sudo zsh ncurses-dev pcre-dev zlib-dev \
&& apk --no-cache --virtual zsh-build-tools add autoconf bash build-base go vim

WORKDIR ${DIR}
COPY . ${DIR}
RUN chmod +x entrypoint.sh && ./entrypoint.sh

VOLUME ["/src", "/data"]
COPY --chown=${ZUSER} . /src

USER ${ZUSER}
WORKDIR /home/${ZUSER}

RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/z-shell/zi-src/main/lib/sh/install.sh)" -- -i skip \
&& ZI_HOME_DIR=/home/${ZUSER}/.zi ZI_BIN_DIR=/home/${ZUSER}/.zi/bin SHELL=/bin/zsh \
zsh -i -lc -- '@zi-scheduler burst || true '

CMD ["/bin/zsh", "-i", "-l"]
