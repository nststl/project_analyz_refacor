# Архітектура шарів

## Діаграма компонентів

```mermaid
flowchart TB
  subgraph Presentation["Presentation (src/web)"]
    UI[Flask routes + templates]
    SIM[SimulatedClock / event log]
  end

  subgraph Application["Application (src/services)"]
    LS[LoanService]
    RS[ReservationService]
    UA[UserAdministrationService]
    AB[AutoBlockingService]
  end

  subgraph Domain["Domain (src/models + src/patterns)"]
    ENT[Entities / Enums]
    STR[PenaltyStrategy]
    OBS[Observer Subject]
  end

  subgraph Infrastructure["Infrastructure (src/storage)"]
    REPO[InMemory Repositories]
  end

  subgraph Quality["Quality"]
    TST[pytest 380+ tests]
    CI[GitHub Actions + SonarCloud]
  end

  UI --> LS
  UI --> RS
  UI --> UA
  UI --> AB
  UI --> SIM
  LS --> STR
  LS --> OBS
  LS --> REPO
  RS --> OBS
  RS --> REPO
  UA --> REPO
  AB --> REPO
  LS --> ENT
  RS --> ENT
  TST --> Application
  CI --> TST
```

## Потік: повернення книги з чергою резерву

```mermaid
sequenceDiagram
  participant UI as Web UI
  participant LS as LoanService
  participant SUB as BookAvailabilitySubject
  participant OBS as ReservationQueueObserver
  participant REPO as Repositories

  UI->>LS: return_loan_with_events(loan_id)
  LS->>REPO: оновити Loan, Book.available_copies
  LS->>SUB: notify(book_id, copies)
  SUB->>OBS: on_book_available()
  OBS-->>LS: event (book_id, next_reader)
  LS-->>UI: loan + availability_events
  UI->>UI: log UC-05 у event log
```

## Принципи

- **SOLID:** сервіси залежать від абстракцій (`Protocol`), не від реалізацій.
- **Thin web layer:** маршрути делегують у `LoanService` / helpers; без бізнес-логіки в Jinja.
- **In-memory only:** без зовнішніх БД і HTTP API в домені.
- **Testability:** mock-репозиторії, параметризовані матриці штрафів і блокувань.
