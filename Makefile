# -*- mode: makefile; -*-

SHELL      := bash
ZI_BIN     ?= $(HOME)/.local/share/zi/bin
ZI_DATA    ?= /tmp/zunit-local
IMAGE      ?= ghcr.io/z-shell/zd
TAG        ?= latest
TERM       ?= xterm-256color
TEST_FILES  = annexes compat ice packages plugins shell-state snippets utils

ifdef FILE
_SUITES := tests/$(FILE).zunit
else
_SUITES := $(patsubst %,tests/%.zunit,$(TEST_FILES))
endif

.PHONY: test run shell build help

## test [FILE=<suite>]              — run ZUnit natively (all suites, or one)
test: bin/zunit
	@for f in $(_SUITES); do \
	  echo "==> $$f"; \
	  PATH="$(CURDIR)/bin:$$PATH" \
	    ZI_BIN="$(ZI_BIN)" \
	    ZI_DATA="$(ZI_DATA)" \
	    TERM=$(TERM) \
	    bin/zunit --tap --verbose "$$f" || exit $$?; \
	done

## run CMD="<zi snippet>"           — run a zi command in Docker
run:
ifndef CMD
	$(error Usage: make run CMD="zi light fzf")
endif
	docker run --rm \
	  --env TERM=$(TERM) \
	  --env ZI_DATA=/tmp/zd-run \
	  $(IMAGE):$(TAG) \
	  zsh -ilc "$(CMD)"

## shell                            — interactive Docker shell with zi loaded
shell:
	docker run --rm -it \
	  --env TERM=$(TERM) \
	  --env ZI_DATA=/tmp/zd-shell \
	  $(IMAGE):$(TAG) \
	  zsh -il

## build [TAG=<tag>] [ZSH_VERSION=<ver>] — build Docker image locally
build:
	CONTAINER_TAG=$(TAG) bash scripts/build.sh \
	  $(if $(ZSH_VERSION),--zsh-version $(ZSH_VERSION)) \
	  --image $(IMAGE)

## help                             — list available targets
help:
	@grep -E '^## ' Makefile | sed 's/^## /  /'

# Install zunit + helpers into bin/ — mirrors what test-native.yml does in CI.
bin/zunit:
	@echo "Installing zunit into bin/ ..."
	@mkdir -p bin
	@curl -fsSL 'https://raw.githubusercontent.com/zdharma/revolver/v0.2.4/revolver' \
	  > bin/revolver
	@curl -fsSL 'https://raw.githubusercontent.com/zdharma/color/d8f91ab5fcfceb623ae45d3333ad0e543775549c/color.zsh' \
	  > bin/color
	@rm -rf /tmp/zunit.git
	@git clone --depth 1 https://github.com/zdharma/zunit.git /tmp/zunit.git
	@cd /tmp/zunit.git && ./build.zsh
	@mv /tmp/zunit.git/zunit bin/zunit
	@chmod u+x bin/color bin/revolver bin/zunit
	@rm -rf /tmp/zunit.git
	@echo "Done."
