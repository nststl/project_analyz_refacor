# Library Management System

[![CI](https://github.com/nststl/project_analyz_refacor/actions/workflows/ci-pipeline.yml/badge.svg?branch=main)](https://github.com/nststl/project_analyz_refacor/actions/workflows/ci-pipeline.yml?query=branch%3Amain)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=nststl_project_analyz_refacor&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=nststl_project_analyz_refacor)

In-memory система керування публічною бібліотекою: облік примірників, позик, резервів, штрафів і блокувань. Доменна логіка відокремлена від веб-інтерфейсу; дані зберігаються в оперативній пам’яті без зовнішніх БД.

**Репозиторій:** [github.com/nststl/project_analyz_refacor](https://github.com/nststl/project_analyz_refacor)

## Можливості

- **Ролі:** читач і бібліотекар (окремі сценарії в UI).
- **Позики:** видача, повернення, ліміт одночасних позик (2 книги на читача).
- **Резерви:** FIFO-черга на книгу; сповіщення наступного читача через **Observer**.
- **Штрафи:** нарахування за прострочення; вибір стратегії **Linear** / **Tiered** (Strategy).
- **Блокування:** вручну (бібліотекар) та автоматично за політикою заборгованості.
- **Симулятор часу:** перемотка дати для перевірки прострочення, штрафів і автоблокування.
- **Якість коду:** 380+ тестів, coverage ≥ 70%, SonarCloud Quality Gate, CI-артефакти.

## Архітектура

| Шар | Каталог | Відповідальність |
|-----|---------|------------------|
| Models | `src/models` | Сутності, переліки |
| Storage | `src/storage` | `Protocol` репозиторіїв, in-memory реалізації |
| Services | `src/services` | Бізнес-сценарії (позики, резерви, адміністрування) |
| Patterns | `src/patterns` | GoF: **Strategy** (штрафи), **Observer** (наявність книги) |
| Utils | `src/utils` | Робота з датами, календарні дні прострочення |
| Web | `src/web` | Flask UI — тонкий шар над сервісами |

Детальніше: [`docs/requirements.md`](docs/requirements.md), діаграми: [`docs/diagrams/`](docs/diagrams/), метрики якості: [`docs/quality.md`](docs/quality.md).

## Структура репозиторію

```
src/                    # Вихідний код (models, services, storage, patterns, web)
tests/                  # Модульні та інтеграційні тести (pytest)
docs/                   # Вимоги, UML-діаграми, звіт якості
.github/workflows/      # CI: тести, coverage, SonarCloud, артефакти
.cursor/rules/          # Контекст для AI-асистентів (архітектура, тестування)
run.py                  # Точка входу веб-додатку
Dockerfile              # Ізольований прогін тестів
sonar-project.properties
pyproject.toml
```

## Швидкий старт

### Вимоги

- Python 3.10+
- Git

### Встановлення та веб-інтерфейс

```bash
git clone https://github.com/nststl/project_analyz_refacor.git
cd project_analyz_refacor

python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/macOS:  source .venv/bin/activate

pip install -r requirements.txt
python run.py
```

Відкрити в браузері: **http://127.0.0.1:5000**

### Тести та покриття

```bash
mkdir -p reports htmlcov   # PowerShell: mkdir reports, htmlcov -Force

pytest tests \
  --junitxml=reports/junit.xml \
  --cov=models --cov=services --cov=storage --cov=patterns --cov=utils --cov=web \
  --cov-report=xml:coverage.xml \
  --cov-report=html:htmlcov
```

HTML-звіт покриття: `htmlcov/index.html`. Поріг **70%** — у `pyproject.toml`.

### Docker

```bash
docker build -t library-system .
docker run --rm -v "$PWD/reports:/app/reports" -v "$PWD/htmlcov:/app/htmlcov" library-system
```

## CI/CD

Workflow **CI Quality Gate** (`.github/workflows/ci-pipeline.yml`) на кожен push/PR у `main`:

1. Запуск pytest + coverage + JUnit XML  
2. Завантаження артефакту **`quality-reports`** (`coverage.xml`, `reports/junit.xml`, `htmlcov/`)  
3. Аналіз SonarCloud і перевірка Quality Gate  

SonarCloud: проєкт `nststl_project_analyz_refacor`, організація `nststl`.

## Документація

| Файл | Зміст |
|------|--------|
| [`docs/requirements.md`](docs/requirements.md) | Предметна область, актори, use cases, правила |
| [`docs/quality.md`](docs/quality.md) | Тести, покриття, SonarCloud, CI-артефакти |
| [`docs/diagrams/use_cases.md`](docs/diagrams/use_cases.md) | Діаграма прецедентів |
| [`docs/diagrams/domain_model.md`](docs/diagrams/domain_model.md) | Концептуальна модель |
| [`docs/diagrams/class_diagram.md`](docs/diagrams/class_diagram.md) | Класи та залежності |
| [`docs/diagrams/architecture.md`](docs/diagrams/architecture.md) | Шари та потік даних |
