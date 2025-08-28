# ShowAds CSV -> API Connector

Tento projekt realizuje spracovanie CSV vstupu (aj miliony riadkov), validaciu zaznamov a efektivne odoslanie na ShowAds API s podporou batchovania a JSON logovania. Repo je pripravene tak, aby sa dalo ihned spustit lokalne, v CI a aj v Dockeri.

**Stav:** Inicialny MVP skeleton (sietove volania su zatial stub). Nizsie su detailne postupy, logovanie, testy a troubleshooting.

---

## Obsah

* [Funkcie](#funkcie)
* [Systemove poziadavky](#systemove-poziadavky)
* [Struktura repozitara](#struktura-repozitara)
* [Rychly start (Windows PowerShell)](#rychly-start-windows-powershell)
* [Rychly start (macoslinux-bash)](#rychly-start-macoslinux-bash)
* [Konfiguracia (.env)](#konfiguracia-env)
* [CLI pouzitie](#cli-pouzitie)
* [JSON logovanie (stderr)](#json-logovanie-stderr)
* [Testy, coverage, format, lint](#testy-coverage-format-lint)
* [Docker (volitelne)](#docker-volitelne)
* [CI (GitHub Actions)](#ci-github-actions)
* [Troubleshooting](#troubleshooting)
* [Roadmap](#roadmap)
* [Prvy commit a push na GitHub](#prvy-commit-a-push-na-github)

---

## Funkcie

* Nacitanie CSV s povinnymi hlavickami: `name,age,banner_id`.
* Validacia (MVP):

  * `name`: neprazdny retazec (do buducna: pismena, medzery, pripustny hyphen).
  * `age`: integer (do buducna: interval `[MIN_AGE, MAX_AGE]`).
  * `banner_id`: integer (do buducna: rozsah `0..99`).
* Batchovanie pri odosielani na bulk endpoint (odporucany limit `<= 1000`).
* Konfiguracia cez `.env` alebo env premenne.
* JSON logy na **stderr** (+ sumar na stdout).

---

## Systemove poziadavky

* Python 3.12+ (odporucane 3.13)
* Windows PowerShell 5+ alebo bash
* Volitelne: Docker (slim image)

---

## Struktura repozitara

```
src/showads_client/
  __init__.py
  __main__.py     # umozni 'python -m showads_client ...'
  config.py       # nacitanie .env; LOG_JSON/LOG_LEVEL/BULK_BATCH_SIZE
  validators.py   # validacie riadkov (MVP)
  batching.py     # chunkovanie listu na batch-e
  api_client.py   # auth/bulk send (zatial stub)
  cli.py          # CLI: validate, send (stdout JSON; stderr logy)

tests/
  conftest.py
  test_*.py       # unit/cli testy; coverage >= 85 %

requirements.txt
.env.example
README.md
```

---

## Rychly start (Windows PowerShell)

```powershell
# 1) Venv
py -3 -m venv .venv
.venv\Scripts\Activate.ps1

# 2) Zavislosti
pip install -r requirements.txt

# 3) Konfiguracia
copy .env.example .env

# 4) Ukazkovy CSV subor (UTF8)
@'
name,age,banner_id
Alice,25,5
Bob,26,2
Carol,27,3
Dave,28,4
Eve,29,5
'@ | Set-Content -Encoding UTF8 .\data.csv

# 5) PYTHONPATH, aby videl modul zo src/
$env:PYTHONPATH = "$PWD\src"

# 6) JSON logy a INFO level
set LOG_JSON=true
set LOG_LEVEL=INFO
```

**Poznamky (Windows):**

* Ak PowerShell nepodporuje `utf8NoBOM`, pouzite `-Encoding UTF8` alebo `-Encoding ASCII`.
* JSON riadky v README su **vystupy programu**, nie prikazy. Nevykonavajte ich v PS, inak vznikne chyba *Unexpected token*.

---

## Rychly start (macOS/Linux bash)

```bash
# 1) Venv
python3 -m venv .venv
source .venv/bin/activate

# 2) Zavislosti
pip install -r requirements.txt

# 3) Konfiguracia
cp .env.example .env

# 4) Ukazkovy CSV subor (UTF-8)
cat > data.csv << 'EOF'
name,age,banner_id
Alice,25,5
Bob,26,2
Carol,27,3
Dave,28,4
Eve,29,5
EOF

# 5) PYTHONPATH
export PYTHONPATH="$PWD/src"

# 6) JSON logy a INFO level
export LOG_JSON=true
export LOG_LEVEL=INFO
```

---

## Konfiguracia (.env)

MVP aktivne cita:

```
LOG_JSON=true            # true/false -> JSON logy na stderr
LOG_LEVEL=INFO           # DEBUG|INFO|WARNING|ERROR
BULK_BATCH_SIZE=1000     # velkost batchu pri 'send' (drzte <= 1000)
```

Rezervovane (pripravene na dalsie iteracie):

```
SHOWADS_BASE_URL=https://api.showads.example.com
SHOWADS_PROJECT_KEY=***
MIN_AGE=18
MAX_AGE=99
REQUEST_TIMEOUT_SECONDS=10
MAX_RETRIES=3
RETRY_BACKOFF_SECONDS=1.0
```

---

## CLI pouzitie

**Napoveda:**

```bash
python -m showads_client --help
```

**Validacia CSV (bez siete):**

```bash
python -m showads_client validate ./data.csv 2> ./logs.jsonl
# stdout: {"valid": 5, "invalid": 0}
# stderr: JSON logy (ak LOG_JSON=true)
```

**Odoslanie (MVP stub s batchovanim):**

```bash
# priklad: umelo zmensime batch na 2 kusy, aby bolo vidno rozdelenie
# Windows:   set BULK_BATCH_SIZE=2
# macOS/Linux: export BULK_BATCH_SIZE=2
python -m showads_client send ./data.csv 2> ./logs.jsonl
# stdout: {"total": 5, "sent": 5}
# stderr: run_start / batch_sent / send_complete (pozri nizsie)
```

---

## JSON logovanie (stderr)

Presmerujte `stderr` do suboru: `2> logs.jsonl` (Windows aj bash).

**Ukazka vystupu (jsonl):**

```json
{"ts":"2025-08-28T18:00:00.123Z","level":"INFO","event":"run_start","run_id":"...","command":"send","csv_path":"data.csv","batch_size":2}
{"ts":"2025-08-28T18:00:00.456Z","level":"INFO","event":"batch_sent","run_id":"...","batch_index":1,"size":2,"response_status":"stubbed"}
{"ts":"2025-08-28T18:00:00.789Z","level":"INFO","event":"batch_sent","run_id":"...","batch_index":2,"size":2,"response_status":"stubbed"}
{"ts":"2025-08-28T18:00:01.001Z","level":"INFO","event":"batch_sent","run_id":"...","batch_index":3,"size":1,"response_status":"stubbed"}
{"ts":"2025-08-28T18:00:01.234Z","level":"INFO","event":"send_complete","run_id":"...","total":5,"sent":5,"duration_s":0.12}
```

**Poznamka:** V PowerShell pouzite na zobrazenie: `Get-Content .\logs.jsonl`.

---

## Testy, coverage, format, lint

**Testy s coverage (min 85 %):**

```bash
pytest -q -ra --cov=showads_client --cov-report=term-missing --cov-fail-under=85
```

**Format a lint:**

```bash
python -m black src tests
python -m pyflakes src tests
```

**Poznamky:**

* Varovanie `CoverageWarning: Module ... previously imported, but not measured` je bezne pri niektorych flowoch pytestu.
* Pyflakes moze nahlasit nepouzite importy v testoch (mozte ich odstranit, prip. ignorovat v MVP).

---

## Docker (volitelne)

**Dockerfile** (minimal):

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
ENV PYTHONPATH=/app/src
CMD ["python", "-m", "showads_client", "--help"]
```

**Build a beh:**

```bash
docker build -t showads-mvp:dev .
docker run --rm -it --env-file .env -v "$PWD/data:/app/data" showads-mvp:dev
```

---

## CI (GitHub Actions)

`.github/workflows/ci.yml`:

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt
      - run: pytest -q -ra --cov=showads_client --cov-report=term-missing --cov-fail-under=85
```

---
## Roadmap

1. Prisne validatory: `name` (regex), `age` v `[MIN_AGE, MAX_AGE]`, `banner_id` v `0..99`.
2. Realne ShowAds API: `POST /auth`, token cache/refresh; `POST /banners/show/bulk`.
3. Retry/backoff na `429/5xx` (`MAX_RETRIES`, `RETRY_BACKOFF_SECONDS`, jitter).
4. Rozsirene metriky v logoch: latencie, histogramy, pomery chyb.
5. Streaming CSV pre pametovo efektivne spracovanie pri milionoch riadkov.

---
