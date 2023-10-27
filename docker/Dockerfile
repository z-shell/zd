ARG VERSION=latest
FROM alpine:${VERSION}
LABEL maintainer="<%= Z-Shell Community %>"
LABEL email="<%= team@zshell.dev =%>"

ARG HOSTNAME=zi@docker-alpine
ARG DIR=/static
ARG SHELL=/bin/zsh
ARG ZUSER=user
ARG PUID=${UID:-1000}
ARG PGID=${GID:-1000}
ARG TERM=${TERM:-xterm-256color}

ENV ZUSER=${ZUSER}
ENV PUID=${PUID}
ENV PGID=${PGID}
ENV DIR=${DIR}
ENV TERM=${TERM}
ENV HOSTNAME=${HOSTNAME}
ENV ZI_ZSH_VERSION=${ZI_ZSH_VERSION}
ENV ZI_HOME_DIR=${ZI_HOME_DIR} ZI_BIN_DIR=${ZI_BIN_DIR}

RUN apk --no-cache --virtual base add coreutils curl \
jq git libuser rsync zsh ncurses-dev pcre-dev zlib-dev alpine-zsh-config \
&& apk --no-cache --virtual zsh-build-tools add autoconf bash build-base go vim

WORKDIR ${DIR}
COPY . .
RUN chmod +x entrypoint.sh && ./entrypoint.sh

VOLUME ["/src", "/data"]
COPY --chown=${ZUSER} . /src

USER ${ZUSER}
WORKDIR /home/${ZUSER}
SHELL ["/bin/zsh", "-c"]

RUN curl -fsSLO 'https://raw.githubusercontent.com/z-shell/zi-src/main/lib/sh/install.sh' \
&& chmod +x install.sh && ./install.sh -i skip

CMD ["zsh", "-l"]
