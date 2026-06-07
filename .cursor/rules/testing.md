# Стратегія тестування

## Інструменти

| Інструмент | Призначення |
|------------|-------------|
| **pytest** | Модульні та інтеграційні тести (`tests/`) |
| **pytest-cov** | Покриття коду (XML + HTML) |
| **coverage.py** | Звіт для SonarCloud |

## Команди

```bash
mkdir -p reports htmlcov
pytest tests \
  --junitxml=reports/junit.xml \
  --cov=models --cov=services --cov=storage --cov=patterns --cov=utils --cov=web \
  --cov-report=xml:coverage.xml \
  --cov-report=html:htmlcov
```

Поріг: **70%** (`pyproject.toml` → `tool.coverage.report.fail_under`).

## Пріоритети покриття

- Граничні значення: 0 / +1 день прострочення, ліміт позик, 0 примірників.
- Ролі: читач vs бібліотекар.
- FIFO-черга, заборона дублікату резерву.
- Observer: подія після `return_loan_with_events`.
- Mock-ізоляція сервісів (`test_mock_isolation.py`).
- Веб-маршрути: CSRF, симулятор часу, стратегії штрафів.

## Звіти для SonarCloud

- `coverage.xml` — корінь проєкту після pytest.
- `reports/junit.xml` — результати тестів.
- Шляхи: `sonar-project.properties`.

Детальні метрики: [`docs/quality.md`](../docs/quality.md).
