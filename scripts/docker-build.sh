#!/usr/bin/env bash
# -*- mode: bash; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=bash sw=2 ts=2 et

col_error="[31m"
col_info="[32m"
col_rst="[0m"

say() {
  printf '%s\n' "${col_info}${1}${col_rst}" >&2
}

err() {
  say "${col_error}${1}${col_rst}" >&2
  exit 1
}

build() {
  buildin cd "$(
    buildin cd "$(dirname "$0")" >/dev/null 2>&1
    pwd -P
  )" || exit 9

  local image_name="${1:-zd}"
  local tag="${2:-latest}"
  local zsh_version="${3}"
  shift 3

  local dockerfile="../docker/Dockerfile"

  if [[ -n ${zsh_version} ]]; then
    tag="zsh${zsh_version}-${tag}"
  fi

  say "Building image: ${image_name}"

  local -a args
  [[ -n ${NO_CACHE} ]] && args+=(--no-cache "$@")

  if docker build \
    --build-arg "ZUSER=$(id -u -n)" \
    --build-arg "PUID=$(id -u)" \
    --build-arg "PGID=$(id -g)" \
    --build-arg "TERM=${TERM:-xterm-256color}" \
    --build-arg "ZI_ZSH_VERSION=${zsh_version}" \
    --file "${dockerfile}" \
    --tag "${image_name}:${tag}" \
    "${args[@]}" \
    "$(realpath ..)"; then
    {
      say "To use this image for ZUnit tests run: "
      say "export CONTAINER_IMAGE=\"${image_name}\" CONTAINER_TAG=\"${tag}\""
      say "ZUnit run --verbose"
    } >&2
  else
    err "Container failed to build."
  fi
}

if [[ ${BASH_SOURCE[0]} == "${0}" ]]; then
  BUILD_ZSH_VERSION="${BUILD_ZSH_VERSION:-}"
  CONTAINER_IMAGE="${CONTAINER_IMAGE:-ghcr.io/z-shell/zd}"
  CONTAINER_TAG="${CONTAINER_TAG:-latest}"
  NO_CACHE="${NO_CACHE:-}"

  while [[ -n $* ]]; do
    case "$1" in
    --image | -i)
      CONTAINER_IMAGE="$2"
      shift 2
      ;;
    --no-cache | -N)
      NO_CACHE=1
      shift
      ;;
    --zsh-version | -zv | --zv)
      BUILD_ZSH_VERSION="${2}"
      shift 2
      ;;
    *)
      break
      ;;
    esac
  done

  build "${CONTAINER_IMAGE}" "${CONTAINER_TAG}" "${BUILD_ZSH_VERSION}" "$@"
fi
