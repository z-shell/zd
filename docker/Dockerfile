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
ARG SHELL=/bin/zsh
ARG DIR=/static
#ARG ZI_HOME_DIR=/home/${ZUSER}/.zi
#ARG ZI_BIN_DIR=/home/${ZUSER}/.zi/bin

ENV ZUSER=${ZUSER} PUID=${PUID}
ENV PGID=${PGID} APK_ADD=${APK_ADD}
ENV DIR=${DIR} TERM=${TERM}
ENV ZI_ZSH_VERSION=${ZI_ZSH_VERSION}
ENV ZI_HOME_DIR=${ZI_HOME_DIR}
ENV ZI_BIN_DIR=${ZI_BIN_DIR}

# trunk-ignore(hadolint/DL3018)
RUN apk --no-cache --virtual base add coreutils curl \
jq git libuser rsync sudo zsh ncurses-dev pcre-dev zlib-dev alpine-zsh-config \
&& apk --no-cache --virtual zsh-build-tools add autoconf bash build-base go vim

WORKDIR $DIR
COPY . .
RUN chmod +x entrypoint.sh && ./entrypoint.sh

VOLUME ["/src", "/data"]
COPY --chown=${ZUSER} . /src

USER ${ZUSER}
WORKDIR /home/${ZUSER}

RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/z-shell/zi-src/main/lib/sh/install.sh)" -- -i skip \
&& /bin/zsh -cl -- '@zi-scheduler burst || true'

CMD ["/bin/zsh", "-il"]
