# Система керування бібліотекою (in-memory)

[![CI](https://github.com/nststl/project_analyz_refacor/actions/workflows/ci-pipeline.yml/badge.svg?branch=main)](https://github.com/nststl/project_analyz_refacor/actions/workflows/ci-pipeline.yml?query=branch%3Amain)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=nststl_project_analyz_refacor&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=nststl_project_analyz_refacor)

> **SonarCloud (ваш акаунт `nststl`):** секрет **`SONAR_TOKEN`** у GitHub. Проєкт у [SonarCloud](https://sonarcloud.io) з ключем **`nststl_project_analyz_refacor`**, org **`nststl`**. CI чекає **Quality Gate**.

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
| `src/web` | Веб-інтерфейс (Flask) поверх домену |

## Запуск сайту (веб-інтерфейс)

```powershell
cd "d:\projects pycharm\kursova_nasti"
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Відкрий у браузері: **http://127.0.0.1:5000** (сайт також слухає `0.0.0.0:5000` — можна зайти з іншого пристрою в тій самій мережі).

**Веб-інтерфейс:** режими **Читач** / **Бібліотекар** (читач не може заблокувати себе), каталог з пошуком, резерви зі скасуванням, історія штрафів, сповіщення Observer.

Повний чеклист вимог курсової: [`docs/compliance.md`](docs/compliance.md).

## Запуск тестів локально

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate    # Linux/macOS

pip install -r requirements.txt
mkdir -p reports htmlcov       # Linux/macOS; у PowerShell: mkdir reports, htmlcov -Force

pytest tests --junitxml=reports/junit.xml ^
  --cov=models --cov=services --cov=storage --cov=patterns --cov=utils --cov=web ^
  --cov-report=xml:coverage.xml --cov-report=html:htmlcov
```

Поріг покриття **70%** задано в `pyproject.toml` (`tool.coverage.report.fail_under`). Кількість тестів — **200+** (параметризовані матриці + модульні/інтеграційні).

## Docker

```bash
docker build -t library-ci .
docker run --rm -v "%cd%/reports:/app/reports" -v "%cd%/htmlcov:/app/htmlcov" library-ci
```

(На Linux замість `%cd%` використай `$PWD`.)

## SonarCloud (ваш акаунт)

### 1. Проєкт на [sonarcloud.io](https://sonarcloud.io)

1. **+ → Analyze new project** → репозиторій **`nststl/project_analyz_refacor`**.
2. **Project key** = **`nststl_project_analyz_refacor`**, **organization** = **`nststl`** (як у [`sonar-project.properties`](sonar-project.properties)).
3. **Project Settings → DevOps Platform integration → GitHub** — прив’яжи репозиторій (усуває `Detected project binding: NONEXISTENT` у CI).

### 2. Токен для GitHub (найчастіша причина падіння CI)

Симптом: `Analysis report uploaded`, потім `Project not found` на Quality Gate.

**Не підходить:** токен з майстра **Analyze → GitHub Actions → Other CI** (лише upload, без API Quality Gate).

**Підходить (один з варіантів):**

1. **User token:** [sonarcloud.io/account](https://sonarcloud.io/account) → **Security** → **Generate Token**
2. **Organization token:** org **nststl** → **Administration** → **Security** → **Generate Token** (analysis token для org)

GitHub → **Settings → Secrets → Actions** → оновити **`SONAR_TOKEN`** новим токеном → **Re-run** workflow.

### 3. Помилка `Organization is not allowed to access data from non main branches` (HTTP 403)

На **Free plan** SonarCloud не можна читати Quality Gate для гілки `main` як окремої branch-аналітики. CI вимикає автоконфіг гілки для push (`-Dsonar.branch.autoconfig.disabled=true`). Токен при цьому має бути **user token** (див. крок 2).

Перевір результат: [проєкт у SonarCloud](https://sonarcloud.io/project/overview?id=nststl_project_analyz_refacor).

## Артефакти CI

Після кожного успішного прогону workflow **CI Quality Gate** у GitHub Actions з’являється артефакт **`quality-reports`** (ZIP): `coverage.xml`, `reports/junit.xml`, каталог `htmlcov/`.

## Захист гілки (рекомендація)

У GitHub: **Settings → Branches → Branch protection** для **`main`**: увімкни **Require status checks to pass** (job `build-test-analyze`).

