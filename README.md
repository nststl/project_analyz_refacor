# Система керування бібліотекою (in-memory)

[![CI](https://github.com/nststl/project_analyz_refacor/actions/workflows/ci-pipeline.yml/badge.svg?branch=main)](https://github.com/nststl/project_analyz_refacor/actions/workflows/ci-pipeline.yml?query=branch%3Amain)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=nststl_project_analyz_refacor&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=nststl_project_analyz_refacor)

> **Sonar (перевірка викладачем):** у GitHub обов’язково додай секрет **`SONAR_TOKEN`**. У [SonarCloud](https://sonarcloud.io) створи проєкт і вистав ті самі **`sonar.projectKey`** та **`sonar.organization`**, що й у файлі [`sonar-project.properties`](sonar-project.properties) (зараз `nststl_project_analyz_refacor` / `nststl`). **CI чекає на Quality Gate** (`-Dsonar.qualitygate.wait=true`).

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

## SonarCloud / SonarQube (для викладача)

### SonarCloud (типовий варіант)

1. Увійди на [sonarcloud.io](https://sonarcloud.io) через GitHub і додай репозиторій **[nststl/project_analyz_refacor](https://github.com/nststl/project_analyz_refacor)**.
2. У **Administration → Update Key** (або при створенні) вистав **Project Key** рівно **`nststl_project_analyz_refacor`** (як у [`sonar-project.properties`](sonar-project.properties)).
3. **Organization** у SonarCloud має збігатися з **`sonar.organization=nststl`** у `sonar-project.properties` (якщо організація інша — зміни файл).
4. Згенеруй токен: **My Account → Security** (або токен аналізу проєкту) і додай у GitHub: **Settings → Secrets and variables → Actions → `SONAR_TOKEN`**.
5. Після push на **`main`** відкрий **Actions**: job має пройти тести, зібрати `coverage.xml` / `reports/junit.xml`, потім **Sonar scan** і чекати **Quality Gate**.

### Якщо викладач дає self-hosted SonarQube

У workflow уже стоїть [`SonarSource/sonarqube-scan-action`](https://github.com/SonarSource/sonarqube-scan-action). Для **SonarQube Server** додай у GitHub Secrets **`SONAR_HOST_URL`** (URL інстансу) і розкоментуй **`sonar.host.url`** у `sonar-project.properties`. Для **SonarCloud** `SONAR_HOST_URL` не потрібен.

### Помилка в CI: `Project not found` після `Analysis report uploaded`

Сканер уже відправив звіт, але крок **очікування Quality Gate** не може прочитати проєкт через API. Найчастіше:

1. **Неправильний тип `SONAR_TOKEN`.** Токен з майстра **«Analyze → Other CI»** лише для одного проєкту інколи **дозволяє відправити звіт**, але **не дозволяє** опитати API статусу / Quality Gate → тоді upload ОК, а wait падає з `Project not found`.  
   **Зроби так:** SonarCloud → **My Account → Security** → **Generate token** (користувач з доступом до org **`nststl`** і проєкту **`nststl_project_analyz_refacor`**).  
   Або: **Organization `nststl` → Administration → Security → Organization analysis token**.  
   Онови секрет **`SONAR_TOKEN`** у GitHub цим токеном (не GitHub PAT).
2. **Ключ проєкту** — у SonarCloud → **Project Information** скопіюй **Project key** один-в-один у `sonar-project.properties` (`sonar.projectKey`).
3. **Прив’язка GitHub** — у Sonar: **Project Settings → DevOps platform integration** → прив’яжи **`nststl/project_analyz_refacor`**.
4. Основна гілка — **`main`** (у GitHub **Settings → General → Default branch**).
5. У workflow у крок Sonar передаються **`SONAR_TOKEN`** і **`GITHUB_TOKEN`** (як рекомендує інтеграція SonarCloud + GitHub).

Якщо терміново треба зелений CI: тимчасово прибери `-Dsonar.qualitygate.wait=true` — аналіз у Sonar лишиться, але job не чекатиме на Quality Gate в одному прогоні.

## Артефакти CI

Після кожного успішного прогону workflow **CI Quality Gate** у GitHub Actions з’являється артефакт **`quality-reports`** (ZIP): `coverage.xml`, `reports/junit.xml`, каталог `htmlcov/`.

## Захист гілки (рекомендація)

У GitHub: **Settings → Branches → Branch protection** для **`main`**: увімкни **Require status checks to pass** (job `build-test-analyze`).

