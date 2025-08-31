# ShowAds CSV -> API konektor


Tento projekt realizuje spracovanie CSV vstupu (aj miliony riadkov), validaciu zaznamov a efektivne odoslanie na ShowAds API s podporou batchovania a JSON logovania. Repo je pripravene tak, aby sa dalo ihned spustit lokalne, v CI a aj v Dockeri. Nizsie su detailne postupy, logovanie, testy a troubleshooting.

---

## Obsah

- [Funkcie](#funkcie)
- [Systemove poziadavky](#systemove-poziadavky)
- [Rychly start (Windows PowerShell)](#rychly-start-windows-powerShell)
- [Rychly start (macOS/Linux bash)](#rychly-start-macoslinux-bash)
- [Konfiguracia (.env)](#konfiguracia-env)
- [CLI pouzitie](#cli-pouzitie)
- [JSON log schema a logovanie (stderr)](#json-log-schema-a-logovanie-stderr)
- [API limity a retry politika](#api-limity-a-retry-politika)
- [Testy, coverage, format, lint](#testy-coverage-format-lint)
- [Docker](#docker)
- [CI (GitHub Actions)](#ci-github-actions)

---

## Funkcie

- Nacitanie CSV s povinnymi hlavickami: `name,age,banner_id,cookie`.
- Validacia (MVP):
  - `name`: neprazdny retazec (do buducna: pismena, medzery, hyphen).
  - `age`: integer (do buducna: interval `[MIN_AGE, MAX_AGE]`).
  - `banner_id`: integer (do buducna: rozsah `0..99`).
- Batchovanie pri odosielani na bulk endpoint (odporucany limit `<= 1000`).
- Konfiguracia cez `.env` alebo env premenne.
- Rolling deduplikacia `(cookie,banner_id)` so sliding oknom pre nizsiu spotrebu pamate.
- JSON logy na **stderr** (+ sumar na stdout).
- Volitelny export nevalidnych riadkov s chybou cez `--errors-out`.
- Progress bar pri odosielani (mozno vypnut `--no-progress`).
- Export metrik behu do JSON cez `--metrics-out`.

---

## Systemove poziadavky

- Python 3.12+ (odporucane 3.13)
- Windows PowerShell 5+ alebo bash
- Docker

---

## Rychly start (Windows PowerShell)

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env

@'
name,age,banner_id,cookie
Alice,25,5,c1
Bob,26,2,c2
Carol,27,3,c3
Dave,28,4,c4
Eve,29,5,c5
'@ | Set-Content -Encoding UTF8 .\data.csv

$env:PYTHONPATH = "$PWD\src"
set LOG_JSON=true
set LOG_LEVEL=INFO
```

## Rychly start (macOS/Linux bash)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

cat > data.csv << 'EOF'
name,age,banner_id,cookie
Alice,25,5,c1
Bob,26,2,c2
Carol,27,3,c3
Dave,28,4,c4
Eve,29,5,c5
EOF

export PYTHONPATH="$PWD/src"
export LOG_JSON=true
export LOG_LEVEL=INFO
```

## Konfiguracia (.env)

Aktivne cita:

```
LOG_JSON=true            # JSON logy na stderr
LOG_LEVEL=INFO           # DEBUG|INFO|WARNING|ERROR
BULK_BATCH_SIZE=1000     # max 1000 (ShowAds bulk limit)
DEDUP_WINDOW=100000      # pocet pametanych parov (cookie,banner_id)
```

Rezervovane (dalsie iteracie):

```
SHOWADS_BASE_URL=https://api.showads.example.com
SHOWADS_PROJECT_KEY=***
MIN_AGE=18
MAX_AGE=99
REQUEST_TIMEOUT_SECONDS=10
MAX_RETRIES=3
RETRY_BACKOFF_SECONDS=1.0
```

## CLI pouzitie

Napoveda:

```
python -m showads_client --help
```

Validacia CSV (bez siete):

```
python -m showads_client validate ./data.csv 2> ./logs.jsonl
# stdout: {"valid": 5, "invalid": 0}

# zapis nevalidnych riadkov s chybou
python -m showads_client validate ./data.csv --errors-out invalid.csv
# invalid.csv: name,age,banner_id,cookie,error
```

Odoslanie:

```
# ukazka: male batch-e
# Windows:   set BULK_BATCH_SIZE=2
# macOS/Linux: export BULK_BATCH_SIZE=2
python -m showads_client send ./data.csv 2> ./logs.jsonl
# stdout: {"total": 5, "sent": 5}

# zapis nevalidnych riadkov a metrik
python -m showads_client send ./data.csv --errors-out invalid.csv --metrics-out m.json
# progress bar je defaultne zapnuty, vypnutie: --no-progress
```

Velkost deduplikačneho okna je mozne nastavit parametrom `--dedup-window` alebo
premennou prostredia `DEDUP_WINDOW`. Vyssie cislo vyzaduje viac pamate, no
zachyti aj duplikaty, ktore su od seba vzdialenejsie. Nizsia hodnota setri
pamat, ale duplikaty oddelene viac nez dane okno sa nemusia odstranit.

## JSON log schema a logovanie (stderr)

Logy su JSON Lines na stderr, jedna udalost = jeden riadok. Povinne polia:

```
ts (ISO8601, UTC, napr. 2025-08-28T18:00:01.234Z)

level (DEBUG|INFO|WARNING|ERROR)

event (run_start, batch_sent, send_complete, validate_complete, error)

run_id (uuid/short id jedneho behu)

command (validate alebo send)
```

Podla kontextu sa doplnaju:

```
batch_index, size (pre odoslane batch-e)

duration_s (pre *_complete)

retries (pocet retry pokusov pre batch)

error_code, error_msg (pri zlyhani)
```

Priklad (jsonl):

```
{"ts":"2025-08-28T18:00:00.123Z","level":"INFO","event":"run_start","run_id":"...","command":"send","csv_path":"data.csv","batch_size":2}
{"ts":"2025-08-28T18:00:00.456Z","level":"INFO","event":"batch_sent","run_id":"...","batch_index":1,"size":2,"response_status":"stubbed"}
{"ts":"2025-08-28T18:00:01.234Z","level":"INFO","event":"send_complete","run_id":"...","total":5,"sent":5,"duration_s":0.12}
```

## Metrics a monitoring

Prikaz `send` podporuje `--metrics-out FILE`, ktory ulozi sumarizovane metriky
o behu ako JSON. Zakladne polia:

```
rows_read, rows_valid, rows_invalid
rows_sent, rows_failed
rate_limited, final_parallel, final_backoff
total_batches, total_retries, max_retries, avg_batch_time_s
```

Tieto metriky je vhodne monitorovat (napr. v Prometheuse alebo inom systeme) na
odhalenie spomalenia alebo zvyseneho poctu retry pokusov, ktory moze signalizovat
problemy s limity ShowAds API.

## API limity a retry politika

Bulk batch size limit: max 1 000 zaznamov v jednom requeste (BULK_BATCH_SIZE <= 1000).

Rate-limiting a chyby: API moze vratit 429 alebo 5xx. V buducej iteracii pouzijeme MAX_RETRIES a RETRY_BACKOFF_SECONDS (s jitterom) na automaticky retry. Teraz sa chyby propagujú volajucemu.

## Testy, coverage, format, lint
```
pytest -q -ra --cov=showads_client --cov-report=term-missing --cov-fail-under=85
python -m black src tests
python -m pyflakes src tests
```

## Docker

Dockerfile je sucastou repa. Build & run:

```
docker build -t showads-mvp:dev .
docker run --rm -it --env-file .env -v "$PWD/data:/app/data" showads-mvp:dev
```

## CI (GitHub Actions)

Repo obsahuje workflow ci.yml s matrixom OS × Python verzie (3.12/3.13).


