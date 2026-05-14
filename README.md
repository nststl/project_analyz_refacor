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

У workflow уже стоїть [`SonarSource/sonarqube-scan-action`](https://github.com/SonarSource/sonarqube-scan-action). Для **SonarQube Server** додай у GitHub Secrets **`SONAR_HOST_URL`** (URL інстансу) і розкоментуй **`sonar.host.url`** у `sonar-project.properties`. Для **SonarCloud** `SONAR_HOST_URL` не потрібен.

### Помилка в CI: `Project not found` після `Analysis report uploaded`

Сканер уже відправив звіт, але крок **очікування Quality Gate** не може прочитати проєкт через API. Найчастіше:

1. **`SONAR_TOKEN` не той акаунт / недостатні права** — токен має належати користувачу з доступом до організації **`nststl`** і проєкту **`nststl_project2`**. Перевір: **SonarCloud → Organization `nststl` → (шестерня) Administration → Security** і створи **Organization analysis token**, або токен з правами аналізу саме цього проєкту. Онови секрет `SONAR_TOKEN` у GitHub.
2. **Ключ проєкту не збігається** — у SonarCloud відкрий проєкт → **Project Information** і скопіюй **Project key** один-в-один у `sonar-project.properties` (`sonar.projectKey`).
3. **Прив’язка до GitHub (ALM)** — у логах було `Project binding: NONEXISTENT`. У Sonar: **Project Settings → General → Pull Request / DevOps platform integration** і прив’яжи репо **`nststl/project2`** — це знімає частину проблем із гілками та статусом.
4. **Немає гілки `master`** — у логах попередження `Could not find ref: master`. У **SonarCloud → Branches** вкажи основну гілку **`kursova`** (або у GitHub зроби default branch `kursova`), щоб порівняння “new code” не ламалось.

Якщо терміново треба зелений CI без розбору токена, тимчасово прибери з workflow рядок `-Dsonar.qualitygate.wait=true` — аналіз у Sonar все одно з’явиться, але job не чекатиме на Quality Gate у тому ж процесі.

## Артефакти CI

Після кожного успішного прогону workflow **CI Quality Gate** у GitHub Actions з’являється артефакт **`quality-reports`** (ZIP): `coverage.xml`, `reports/junit.xml`, каталог `htmlcov/`.

## Захист гілки (рекомендація)

У GitHub: **Settings → Branches → Branch protection** для `kursova` / `main`: увімкни **Require status checks to pass** (обов’язковий job `build-test-analyze`) та заборону merge при падінні тестів / coverage.

## Легасі OMS (не входить у основну курсову)

Старий демо-скрипт авіаційного OMS (SQLite + MongoDB) залишено в каталозі [`legacy/`](legacy/README.md) лише для історії; **основна здача** — бібліотечний in-memory код у `src/` та тести в `tests/`.
