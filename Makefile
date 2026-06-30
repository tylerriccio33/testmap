lint: ## Run linters
	@uv run ruff format .
	@uv run ruff check .
	@uv run pyrefly check .

test: ## Run tests
	@uv run pytest \
		--cov=testmap --cov=pytest_testmap \
		--cov-report term-missing
