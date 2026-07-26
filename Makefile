install:
	@uv sync
debug:
	@uv run python3 -m pdb -m src $(MAP)
run:
	@uv run python3 -m src $(MAP)
clean:
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name ".mypy_cache" -exec rm -rf {} +
lint:
	@uv run  mypy src --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs
	@flake8 src
.PHONY: lint clean run debug install
