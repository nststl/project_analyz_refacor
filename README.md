# Система керування бібліотекою (in-memory)

[![CI](https://github.com/nststl/project_analyz_refacor/actions/workflows/ci-pipeline.yml/badge.svg?branch=main)](https://github.com/nststl/project_analyz_refacor/actions/workflows/ci-pipeline.yml?query=branch%3Amain)
> **SonarQube (перевірка викладачем):** у GitHub Secrets додай **`SONAR_TOKEN`** і **`SONAR_HOST_URL`** (URL вашого SonarQube). На сервері створи проєкт з ключем **`nststl_project_analyz_refacor`** (як у [`sonar-project.properties`](sonar-project.properties)). **CI чекає на Quality Gate** (`-Dsonar.qualitygate.wait=true`).

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

Відкрий у браузері: **http://127.0.0.1:5000**

На сторінці можна: взяти книгу, повернути, поставити в резерв, заблокувати/розблокувати читача (демо бібліотекаря).

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

## SonarQube (self-hosted, для викладача)

Проєкт налаштований на **SonarQube Server** (не SonarCloud). У CI — [`SonarSource/sonarqube-scan-action`](https://github.com/SonarSource/sonarqube-scan-action).

### GitHub Secrets (репозиторій `project_analyz_refacor`)

| Secret | Значення |
|--------|----------|
| `SONAR_TOKEN` | SonarQube → **My Account → Security → Generate Token** (користувач з правом аналізу проєкту) |
| `SONAR_HOST_URL` | URL сервера, напр. `https://sonar.university.edu.ua` (**без** `/` в кінці) |

### На SonarQube

1. **Create project** (або **Analyze new project**) з ключем **`nststl_project_analyz_refacor`** — як у [`sonar-project.properties`](sonar-project.properties).
2. Якщо ключ інший — зміни `sonar.projectKey` у файлі під ваш сервер.
3. Увімкни **Quality Gate** (типовий «Sonar way» або вимоги курсу: coverage ≥ 70% тощо).

### Після push на `main`

Workflow: тести → `coverage.xml` / `junit.xml` → скан SonarQube → очікування **Quality Gate**.

### Типові помилки

- **`without SONAR_TOKEN`** — секрет не додано або неправильна назва.
- **`Project not found`** — немає проєкту з таким ключем на **вашому** SonarQube, або токен без доступу.
- **`Communicating with SonarQube Cloud`** — не задано **`SONAR_HOST_URL`** (сканер пішов у Cloud замість вашого сервера).

## Артефакти CI

Після кожного успішного прогону workflow **CI Quality Gate** у GitHub Actions з’являється артефакт **`quality-reports`** (ZIP): `coverage.xml`, `reports/junit.xml`, каталог `htmlcov/`.

## Захист гілки (рекомендація)

У GitHub: **Settings → Branches → Branch protection** для **`main`**: увімкни **Require status checks to pass** (job `build-test-analyze`).

