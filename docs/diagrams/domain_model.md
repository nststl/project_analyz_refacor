# Модель предметної області

```mermaid
classDiagram
  class User {
    +String id
    +String name
    +Role role
    +DateTime blocked_until
    +int max_concurrent_loans
    +is_blocked_at(when) bool
  }
  class Book {
    +String id
    +String title
    +BookCategory category
    +int total_copies
    +int available_copies
  }
  class Loan {
    +String id
    +DateTime borrowed_at
    +DateTime due_at
    +DateTime returned_at
    +Decimal penalty_amount
    +LoanState state
  }
  class Reservation {
    +String id
    +int sequence
  }
  class Role {
    <<enumeration>>
    READER
    LIBRARIAN
  }
  class BookCategory {
    <<enumeration>>
    STANDARD
    RARE
    REFERENCE
  }
  User "1" --> "*" Loan : оформлює
  Book "1" --> "*" Loan : примірник
  User "1" --> "*" Reservation : у черзі
  Book "1" --> "*" Reservation : на книгу
  User --> Role
  Book --> BookCategory
```

Категорія книги (`STANDARD`, `RARE`, `REFERENCE`) впливає на розрахунок штрафу в патерні **Strategy**.  
`REFERENCE` не видаються назовні. Ліміт одночасних позик задається полем `max_concurrent_loans`.
