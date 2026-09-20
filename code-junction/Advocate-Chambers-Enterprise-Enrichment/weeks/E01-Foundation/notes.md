# Week E01 — Implementation Notes

## Suggested Makefile Targets

```makefile
.PHONY: lint-py lint-web typecheck test-baseline verify

lint-py:
	ruff check scripts bar-association-hall services packages
	ruff format --check scripts bar-association-hall services packages
	mypy scripts services --ignore-missing-imports

lint-web:
	npm run lint:web

typecheck:
	npm run typecheck:web

test-baseline:
	python -m unittest discover -s tests -p 'test_*.py'
	npm run validate:week21 || true
	# add other critical validate targets as needed

verify: lint-py typecheck test-baseline
	@echo "Baseline verification complete"
```

## Baseline Directory Layout

```
baselines/
  2026-09-20/
    quality-gate-report.json
    week23-adversarial-expansion-report.json
    week25-performance-report.json
    README.md          # how the baseline was captured
```

## Common Pitfalls

- Running Ruff across generated reports or large CAD output directories → exclude them.
- mypy complaining about dynamic imports in the weekly scripts → use `type: ignore` sparingly and document.
- Changing `package-lock.json` or Python lock files accidentally → review diffs carefully.

## Migration Tip

If the root already has many weekly scripts, do **not** try to reorganize them in E01. Only add tooling around them. Structural moves belong to later weeks or a dedicated “repo organization” PR after E02.
