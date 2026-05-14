import sqlite3
import random
import string
import os


def reset_and_seed():
    db_name = 'legacy_airlines.db'
    if os.path.exists(db_name):
        os.remove(db_name)
        print(f"Файл {db_name} видалено для очищення.")

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute('''
                   CREATE TABLE legacy_bookings
                   (
                       pnr_code          TEXT PRIMARY KEY,
                       names             TEXT,
                       last_names_unused TEXT,
                       flight_number     TEXT,
                       dep_city          TEXT,
                       arr_city          TEXT,
                       airline_brand     TEXT,
                       tickets           TEXT,
                       ancillaries       TEXT,
                       migrated          BOOLEAN DEFAULT 0
                   )
                   ''')

    cities = ["LONDON", "PARIS", "NEW YORK", "KYIV", "ROME", "BERLIN", "TOKYO", "WARSAW"]
    brands = ["SkyHigh", "LowCostAir", "GlobalWings", "EuroJet"]
    first_names = ["JOHN", "ALAN", "MARIA", "ELENA", "IVAN", "ANNA", "DMYTRO", "SOPHIA"]
    last_names = ["SMITH", "BROWN", "KORNIENKO", "TKACHUK", "WHITE", "WILSON"]
    services = ["Baggage 23kg", "VIP Lounge", "Fast Track", "Extra Legroom", "Wi-Fi"]

    data = []
    print("Генерація 10 000 нових записів...")

    for _ in range(10000):
        pnr = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        pax_count = random.randint(1, 3)

        # Генеруємо імена та квитки
        pax_names_list = []
        pax_tickets_list = []
        for _ in range(pax_count):
            full_name = f"{random.choice(first_names)} {random.choice(last_names)}"
            pax_names_list.append(full_name)
            pax_tickets_list.append(''.join(random.choices(string.digits, k=13)))

        # Генеруємо допки (код:послуга)
        anc_list = []
        for _ in range(random.randint(0, 2)):
            emd = ''.join(random.choices(string.digits, k=13))
            anc_list.append(f"{emd}:{random.choice(services)}")

        dep = random.choice(cities)
        arr = random.choice([c for c in cities if c != dep])

        data.append((
            pnr,
            ", ".join(pax_names_list),
            "",
            f"PS{random.randint(100, 999)}",
            dep, arr,
            random.choice(brands),
            ", ".join(pax_tickets_list),
            ", ".join(anc_list) if anc_list else "None",
            0
        ))

    cursor.executemany("INSERT INTO legacy_bookings VALUES (?,?,?,?,?,?,?,?,?,?)", data)
    conn.commit()
    conn.close()
    print("SQL база готова. Тепер очистіть MongoDB Compass (колекцію orders) і запускайте міграцію.")


if __name__ == "__main__":
    reset_and_seed()