# Якість коду та CI/CD

## Поточні показники

| Метрика | Значення | Де перевірити |
|---------|----------|----------------|
| Модульні / інтеграційні тести | **382+** | `pytest tests --co -q` |
| Покриття коду | **≥ 70%** (фактично ~88%) | `pyproject.toml` → `fail_under`; `htmlcov/` |
| SonarCloud Quality Gate | CI + [дашборд](https://sonarcloud.io/project/overview?id=nststl_project_analyz_refacor) | Badge у README |
| CI-артефакти | `quality-reports` | GitHub Actions → останній workflow run |

## Запуск перевірок локально

```bash
python -m venv .venv && source .venv/bin/activate   # або .venv\Scripts\activate на Windows
pip install -r requirements.txt
mkdir -p reports htmlcov

pytest tests \
  --junitxml=reports/junit.xml \
  --cov=models --cov=services --cov=storage --cov=patterns --cov=utils --cov=web \
  --cov-report=xml:coverage.xml \
  --cov-report=html:htmlcov \
  --cov-report=term-missing
```

## CI pipeline

Файл: `.github/workflows/ci-pipeline.yml`

| Крок | Результат |
|------|-----------|
| pytest + coverage | `coverage.xml`, `reports/junit.xml`, `htmlcov/` |
| upload-artifact | ZIP **`quality-reports`** |
| SonarCloud scan | Статичний аналіз + імпорт coverage/junit |
| Quality Gate wait | Job падає, якщо gate не пройдено |

## SonarCloud

| Параметр | Значення |
|----------|----------|
| Project key | `nststl_project_analyz_refacor` |
| Organization | `nststl` |
| Конфіг | `sonar-project.properties` |
| GitHub secret | `SONAR_TOKEN` (user token з sonarcloud.io/account) |

Quality Gate перевіряє, зокрема: `new_reliability_rating`, `new_security_rating`, `new_coverage`, `new_security_hotspots_reviewed`.

## Відповідність функціоналу тестам

| Use case | Модульні тести | Веб-тести |
|----------|----------------|-----------|
| UC-01…UC-03 | `test_loan_service.py`, `test_penalty_matrix.py` | `test_web.py` |
| UC-04, UC-05 | `test_reservation_and_repos.py` | `test_web.py` (reserve/return/observer) |
| UC-06, UC-07 | `test_admin_and_auto_block.py`, `test_blocking_matrix.py` | `test_web.py` (block, advance-time) |
| Strategy | `test_penalty_matrix.py` | `test_set_penalty_strategy_tiered` |
| Mock / ізоляція | `test_mock_isolation.py` | — |

## Docker

```bash
docker build -t library-system .
docker run --rm library-system
```

Контейнер виконує той самий набір pytest-команд, що й CI.
