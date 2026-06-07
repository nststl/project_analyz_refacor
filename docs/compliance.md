# Відповідність вимогам курсової

Остання локальна перевірка: `pytest tests` + `coverage` (поріг 70% у `pyproject.toml`).

## Обов’язкові критерії

| Вимога | Статус | Де перевірити |
|--------|--------|----------------|
| **200+ тестів** | ✅ | `pytest tests --co -q` |
| **Покриття ≥ 70%** | ✅ | `pytest --cov=...` → `fail_under = 70` |
| **SonarQube / SonarCloud + Quality Gate** | ⚙️ | CI job `SonarCloud scan`; [sonarcloud.io](https://sonarcloud.io/project/overview?id=nststl_project_analyz_refacor) |
| **CI/CD артефакти** | ✅ | GitHub Actions → artifact `quality-reports` |
| **In-memory, без зовнішніх БД** | ✅ | `src/storage/in_memory.py` |
| **Шарова архітектура** | ✅ | `models` / `services` / `storage` / `web` |
| **GoF: Strategy** | ✅ | `src/patterns/penalty_strategy.py` |
| **GoF: Observer** | ✅ | `src/patterns/observer.py`, `ReservationQueueObserver` |
| **7 use cases** | ✅ | `docs/requirements.md`, UC-01…UC-07 |
| **UML / діаграми** | ✅ | `docs/diagrams/` |
| **AI-контекст** | ✅ | `.cursorrules`, `.cursor/rules/` |
| **Веб-інтерфейс** | ✅ | `python run.py` → http://127.0.0.1:5000 |

## Use cases (домен + веб)

| UC | Опис | Код | Веб |
|----|------|-----|-----|
| UC-01 | Видача | `LoanService.borrow` | Кнопка «Взяти» |
| UC-02 | Повернення вчасно | `LoanService.return_loan` | «Повернути» |
| UC-03 | Штраф за прострочення | `PenaltyStrategy` | Історія повернень |
| UC-04 | Резерв FIFO | `ReservationService.enqueue` | «Резерв», список резервів |
| UC-05 | Observer | `ReservationQueueObserver` | Сповіщення |
| UC-06 | Блок бібліотекарем | `UserAdministrationService` | Режим **Бібліотекар** (читач не блокує себе) |
| UC-07 | Авто-блокування | `AutoBlockingService` | Після повернення з штрафом |

## Команди для самоперевірки

```powershell
cd "d:\projects pycharm\kursova_nasti"
.\.venv\Scripts\Activate.ps1
pytest tests --co -q
pytest tests --cov=models --cov=services --cov=storage --cov=patterns --cov=utils --cov=web --cov-report=term-missing -q
python run.py
```

## SonarCloud

- Проєкт: `nststl_project_analyz_refacor`, org `nststl`
- GitHub secret: `SONAR_TOKEN` (user token)
- Free plan: mainline-аналіз (див. `.github/workflows/ci-pipeline.yml`)

## Що здавати викладачу

1. Посилання на GitHub `nststl/project_analyz_refacor`
2. Скріншот зеленого CI + Quality Gate
3. Артефакт `quality-reports` або локальні `coverage.xml` / `htmlcov`
4. Запуск сайту: `python run.py`
