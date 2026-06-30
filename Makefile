lint: ## Run linters
	@uv run ruff format .
	@uv run ruff check .
	@uv run pyrefly check .

test: ## Run tests
	@uv run pytest \
		--cov src \
		--cov-report term-missing