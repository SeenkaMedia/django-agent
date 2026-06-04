.PHONY: install test test-live build clean

install:
	pip install -e .

test:
	python runtests.py

test-live:
	python runtests.py --live

build:
	python -m build

clean:
	rm -rf build dist *.egg-info .pytest_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
