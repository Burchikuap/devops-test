NAMESPACE ?= devops-platform
MONITORING_NAMESPACE ?= monitoring
JWT_SECRET ?= change-me-dev-secret
JWT_AUDIENCE ?= devops-clients
JWT_ISSUER ?= devops-test-suite

.PHONY: test
test:
	python3 -m pytest services/api/tests services/worker/tests

.PHONY: token
token:
	python3 infra/scripts/create_jwt.py \
		--secret "$(JWT_SECRET)" \
		--audience "$(JWT_AUDIENCE)" \
		--issuer "$(JWT_ISSUER)"

.PHONY: smoke
smoke:
	NAMESPACE=$(NAMESPACE) \
	JWT_SECRET=$(JWT_SECRET) \
	JWT_AUDIENCE=$(JWT_AUDIENCE) \
	JWT_ISSUER=$(JWT_ISSUER) \
	bash infra/scripts/smoke.sh

