# Архітектура: in-memory бібліотека

## Мета

Система керування бібліотекою з **читачами** та **бібліотекарями**, обліком примірників, **позиками**, **чергою резерву** та **політикою штрафів**. Дані — in-memory репозиторії за `Protocol`.

## Шари

1. **`src/models`** — `User`, `Book`, `Loan`, `Reservation`; переліки `Role`, `BookCategory`, `LoanState`.
2. **`src/storage/protocols.py`** — `IUserRepository`, `IBookRepository`, `ILoanRepository`, `IReservationRepository`.
3. **`src/storage/in_memory.py`** — реалізації на словниках; без I/O.
4. **`src/services`**:
   - `loan_service.py` — видача/повернення, Strategy штрафів, Observer через Subject.
   - `reservation_service.py` — FIFO-черга, `ReservationQueueObserver`.
   - `user_administration.py` — блокування бібліотекарем.
   - `auto_blocking.py` + `blocking_policy.py` — автоблокування.
5. **`src/patterns`** — `penalty_strategy.py`, `observer.py`.
6. **`src/utils`** — календарні дні прострочення.
7. **`src/web`** — Flask UI, `SimulatedClock`, симулятор часу, лог подій.

## Інверсія залежностей

Сервіси приймають інтерфейси репозиторіїв і стратегій; тести підставляють in-memory або `unittest.mock`.

## Діаграми

Повний набір UML (Mermaid): `docs/diagrams/`.
