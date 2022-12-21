## Lint your code using pylint
.PHONY: lint
lint:
	python -m pylint --version
	python -m pylint src
## Run tests using pytest
.PHONY: test
test:
	python -m pytest --version
	python -m pytest youtube_recommender/tests
## Format your code using black
# .PHONY: black
# black:
# 	python -m black --version
# 	python -m black .## Run ci part
.PHONY: ci
	ci: precommit lint test

.PHONY: install
install: 
	pip install -U .

deploy-scrape-service:
	kubectl apply -f $(find ./kubernetes -name 'scrape-service*.yaml' -o -name '*secret.yaml' -type f | tr '\n' ',' | sed 's/,$//')

sync_env_to_here:
	rsync -avz -e ssh $(SERVER_USER)@$(SERVER_ADDR):$(REPO_PATH)/.env $(REPO_PATH)

sync_secrets_to_here:
	rsync -avz -e ssh $(SERVER_USER)@$(SERVER_ADDR):$(REPO_PATH)/kubernetes/secrets $(REPO_PATH)/kubernetes

sync_env_to_server:
	rsync -avz -e ssh $(REPO_PATH)/.env $(SERVER_USER)@$(SERVER_ADDR):$(REPO_PATH)/.env

sync_secrets_to_server:
	rsync -avz -e ssh $(REPO_PATH)/kubernetes/secrets $(SERVER_USER)@$(SERVER_ADDR):$(REPO_PATH)/kubernetes
