# Система керування бібліотекою (in-memory)

[![CI](https://github.com/nststl/project2/actions/workflows/ci-pipeline.yml/badge.svg?branch=kursova)](https://github.com/nststl/project2/actions/workflows/ci-pipeline.yml?query=branch%3Akursova)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=nststl_project2&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=nststl_project2)

> **Sonar (перевірка викладачем):** у GitHub обов’язково додай секрет **`SONAR_TOKEN`**. У [SonarCloud](https://sonarcloud.io) створи проєкт і вистав ті самі **`sonar.projectKey`** та **`sonar.organization`**, що й у файлі [`sonar-project.properties`](sonar-project.properties) (зараз `nststl_project2` / `nststl`). Якщо в Sonar інший ключ — зміни properties і бейдж вище. CI чекає на **Quality Gate** (`-Dsonar.qualitygate.wait=true`).

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

## SonarCloud / SonarQube (для викладача)

### SonarCloud (типовий варіант)

1. Увійди на [sonarcloud.io](https://sonarcloud.io) через GitHub і додай організацію/репозиторій **nststl/project2** (або створи проєкт вручну).
2. У **Administration → Update Key** (або при створенні) вистав **Project Key** рівно **`nststl_project2`** (або зміни це значення і в [`sonar-project.properties`](sonar-project.properties), і бейдж у верхній частині README).
3. **Organization** у SonarCloud має збігатися з **`sonar.organization=nststl`** у `sonar-project.properties` (якщо організація інша — зміни файл).
4. Згенеруй токен: **My Account → Security** (або токен аналізу проєкту) і додай у GitHub: **Settings → Secrets and variables → Actions → `SONAR_TOKEN`**.
5. Після push на `kursova` відкрий **Actions**: job має пройти тести, зібрати `coverage.xml` / `reports/junit.xml`, потім **Sonar scan** і чекати **Quality Gate** (`sonar.qualitygate.wait=true` у workflow).

### Якщо викладач дає self-hosted SonarQube

Офіційний крок GitHub для Cloud (`sonarcloud-github-action`) **не підходить** для сервера без додаткових змін. Варіанти: попросити викладача прийняти лише звіти з артефактів CI, або замінити крок скану на [`SonarSource/sonarqube-scan-action`](https://github.com/SonarSource/sonarqube-scan-action) з змінними **`SONAR_HOST_URL`**, **`SONAR_TOKEN`** і розкоментованим **`sonar.host.url`** у `sonar-project.properties`.

## Артефакти CI

Після кожного успішного прогону workflow **CI Quality Gate** у GitHub Actions з’являється артефакт **`quality-reports`** (ZIP): `coverage.xml`, `reports/junit.xml`, каталог `htmlcov/`.

## Захист гілки (рекомендація)

У GitHub: **Settings → Branches → Branch protection** для `kursova` / `main`: увімкни **Require status checks to pass** (обов’язковий job `build-test-analyze`) та заборону merge при падінні тестів / coverage.

## Легасі OMS (не входить у основну курсову)

Старий демо-скрипт авіаційного OMS (SQLite + MongoDB) залишено в каталозі [`legacy/`](legacy/README.md) лише для історії; **основна здача** — бібліотечний in-memory код у `src/` та тести в `tests/`.
