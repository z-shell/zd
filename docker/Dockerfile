ARG VERSION=edge
FROM alpine:$VERSION
LABEL maintainer="<%= Z-Shell Community %>"
LABEL email="<%= team@zshell.dev =%>"

ARG DIR
ARG PUID
ARG PGID
ARG TERM
ARG ZUSER
ARG ZHOST

ENV DIR=${DIR:-/static}
ENV PUID=${PUID:-1000}
ENV PGID=${PGID:-1000}
ENV TERM=${TERM:-xterm}
ENV ZUSER=${ZUSER:-user}
ENV HOST=$ZHOST

RUN set -ex && apk --no-cache add \
  alpine-zsh-config \
  ncurses-dev \
  build-base \
  coreutils \
  pcre-dev \
  zlib-dev \
  autoconf \
  libuser \
  rsync \
  bash \
  curl \
  sudo \
  zsh \
  git \
  vim \
  go \
  jq

WORKDIR $DIR
COPY . .
RUN chmod +x entrypoint.sh && ./entrypoint.sh

VOLUME ["/src", "/data"]
COPY --chown=$ZUSER . /src

USER $ZUSER
WORKDIR /home/$ZUSER

RUN /tmp/install.sh -i skip

SHELL ["/bin/zsh", "-lc", "@zi-scheduler burst"]

CMD ["zsh", "-il"]
