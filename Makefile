
.PHONY: install run test lint format docker-build docker-run

install:
\tpip install -r requirements.txt

run:
\tpython -m showads_client --help

test:
\tpytest -q --cov=showads_client --cov-report=term-missing

lint:
\tpython -m pyflakes src || true

format:
\tpython -m black src tests || true

docker-build:
\tdocker build -t showads-mvp:dev .

docker-run:
\tdocker run --rm -it --env-file .env -v %cd%/data:/app/data showads-mvp:dev
