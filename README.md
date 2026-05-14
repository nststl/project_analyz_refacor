# Система керування бібліотекою (in-memory)

[![CI](https://github.com/nststl/project2/actions/workflows/ci-pipeline.yml/badge.svg?branch=kursova)](https://github.com/nststl/project2/actions/workflows/ci-pipeline.yml?query=branch%3Akursova)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=library-management-system&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=library-management-system)

> **Примітка:** бейдж SonarCloud запрацює після створення проєкту в SonarCloud і підстановки `sonar.projectKey` / `sonar.organization` у `sonar-project.properties`, а також секрету `SONAR_TOKEN` у GitHub Actions. Поки скан у workflow стоїть з `continue-on-error: true`, щоб гілка не ламалась без токена.

## Що це за проєкт

Доменна модель **бібліотеки**: читачі та бібліотекарі, **видача** та **повернення** примірників, **черга резерву** (FIFO), **нарахування штрафів** за прострочення (кілька стратегій), **блокування читача** (ручне бібліотекарем та автоматичне за політикою після серйозної заборгованості). Усі дані — **in-memory** (без зовнішніх БД та HTTP API), згідно з вимогами курсової.

Детальний опис вимог, акторів і сценаріїв: [`docs/requirements.md`](docs/requirements.md). UML-діаграми (Mermaid): [`docs/diagrams/`](docs/diagrams/).

## Архітектура (коротко)

| Шар | Призначення |
|-----|-------------|
| `src/models` | Сутності та переліки |
| `src/services` | Бізнес-логіка (кредити, резерви, адміністрування) |
| `src/storage` | Протоколи репозиторіїв + in-memory реалізації |
| `src/patterns` | **Strategy** (штрафи), **Observer** (сповіщення про наявність книги) |
| `src/utils` | Допоміжні функції (час, календарні дні прострочення) |

## Запуск тестів локально

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate    # Linux/macOS

pip install -r requirements.txt
mkdir -p reports htmlcov       # Linux/macOS; у PowerShell: mkdir reports, htmlcov -Force

pytest tests --junitxml=reports/junit.xml ^
  --cov=models --cov=services --cov=storage --cov=patterns --cov=utils ^
  --cov-report=xml:coverage.xml --cov-report=html:htmlcov
```

Поріг покриття **70%** задано в `pyproject.toml` (`tool.coverage.report.fail_under`). Кількість тестів — **200+** (параметризовані матриці + модульні/інтеграційні).

## Docker

```bash
docker build -t library-ci .
docker run --rm -v "%cd%/reports:/app/reports" -v "%cd%/htmlcov:/app/htmlcov" library-ci
```

(На Linux замість `%cd%` використай `$PWD`.)

## SonarQube / SonarCloud

1. Створи проєкт у [SonarCloud](https://sonarcloud.io) (або підключи self-hosted SonarQube).
2. Онови `sonar-project.properties`: `sonar.organization`, `sonar.projectKey`.
3. У репозиторії GitHub: **Settings → Secrets → Actions** — додай `SONAR_TOKEN`.
4. За потреби прибери `continue-on-error: true` у кроці Sonar у `.github/workflows/ci-pipeline.yml`, коли все налаштовано.

## Артефакти CI

Після кожного успішного прогону workflow **CI Quality Gate** у GitHub Actions з’являється артефакт **`quality-reports`** (ZIP): `coverage.xml`, `reports/junit.xml`, каталог `htmlcov/`.

## Захист гілки (рекомендація)

У GitHub: **Settings → Branches → Branch protection** для `kursova` / `main`: увімкни **Require status checks to pass** (обов’язковий job `build-test-analyze`) та заборону merge при падінні тестів / coverage.

## Легасі OMS (не входить у основну курсову)

Старий демо-скрипт авіаційного OMS (SQLite + MongoDB) залишено в каталозі [`legacy/`](legacy/README.md) лише для історії; **основна здача** — бібліотечний in-memory код у `src/` та тести в `tests/`.
