# The load on the dev server (see README.md): make -C perf <target>, a
# stand named from the root of the meta repository.
SHELL := /bin/bash
ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))..)
STAND ?=

.PHONY: help run check-host tune-host

help:
	@echo "run         a run of STAND, ingot-auth/perf/game: the candidate"
	@echo "            against the baseline [SCENARIOS=... ARGS=... TRIAL=1]"
	@echo "check-host  the state of the host, why a run would refuse it"
	@echo "tune-host   the boost off and the cores steady, sudo [MODE=off back]"

run:
	@[ -n "$(STAND)" ] || { echo "STAND=<addon>/perf/<stand>" >&2; exit 2; }
	$(ROOT)/perf/run $(ROOT)/$(STAND) $(SCENARIOS) -- $(ARGS)

check-host:
	@$(ROOT)/perf/check-host

tune-host:
	sudo $(ROOT)/perf/tune-host $(or $(MODE),on)
