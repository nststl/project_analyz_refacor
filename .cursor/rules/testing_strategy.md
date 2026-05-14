# Стратегія тестування та звітів

## Фреймворк

- **pytest** — модульні та інтеграційні тести в `tests/`.
- **pytest-cov** + **coverage.py** — XML і HTML для людей і для Sonar.

> Для Java/JaCoCo аналог той самий за змістом: **JUnit XML + coverage XML/HTML**; у Python це **`reports/junit.xml`** + **`coverage.xml`** + **`htmlcov/`**.

## Команди (локально / CI)

```bash
mkdir -p reports htmlcov
pytest tests \
  --junitxml=reports/junit.xml \
  --cov=models --cov=services --cov=storage --cov=patterns --cov=utils \
  --cov-report=xml:coverage.xml \
  --cov-report=html:htmlcov
```

Поріг **fail_under** заданий у `pyproject.toml` (не нижче **70%**).

## Що тестувати в пріоритеті

- **Граничні значення**: 0 прострочених днів, рівно на дедлайні, +1 день; 0 доступних примірників; ліміт активних позик.
- **Ролі**: читач не може виконувати дії бібліотекаря і навпаки.
- **Черга резерву**: порядок FIFO за `sequence`, заборона дублікату резерву тим самим читачем.
- **Observer**: після `return_loan` є сповіщення, якщо є черга.
- **Mock**: ізоляція шару сервісу від конкретного репозиторію (`unittest.mock.Mock` / `MagicMock` spec за `Protocol`).

## Sonar

- `coverage.xml` у корені після прогону.
- `reports/junit.xml` для імпорту тестів у Sonar.
- Шляхи вказані в `sonar-project.properties`.
