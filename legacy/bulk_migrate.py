import sqlite3
import time
from pymongo import MongoClient


class IDGenerator:
    @staticmethod
    def generate_6():
        timestamp = int(time.time_ns())
        chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        code = ""
        temp = timestamp
        for _ in range(6):
            code = chars[temp % 36] + code
            temp //= 36
        return code


def migrate():
    sql_conn = sqlite3.connect('legacy_airlines.db')
    cursor = sql_conn.cursor()

    mongo_col = MongoClient('mongodb://localhost:27017/')['oms_database']['orders']

    cursor.execute("SELECT * FROM legacy_bookings WHERE migrated = 0")
    rows = cursor.fetchall()
    print(f"Міграція {len(rows)} записів...")

    for row in rows:
        names = row[1].split(", ")
        tickets = row[7].split(", ")

        # Формуємо масив пасажирів
        pax_docs = []
        for i in range(len(names)):
            pax_docs.append({
                "name": names[i],
                "ticket_13_digit": tickets[i] if i < len(tickets) else "N/A"
            })

        # Парсимо допки
        anc_docs = []
        if row[8] != "None":
            for item in row[8].split(", "):
                if ":" in item:
                    emd, name = item.split(":")
                    anc_docs.append({"emd_code": emd, "service_name": name})

        doc = {
            "order_id": IDGenerator.generate_6(),
            "legacy_pnr": row[0],
            "passengers": pax_docs,
            "flight": {"number": row[3], "route": f"{row[4]} -> {row[5]}"},
            "brand": row[6],
            "brand_specific": {"ancillaries": anc_docs}
        }

        mongo_col.insert_one(doc)
        cursor.execute("UPDATE legacy_bookings SET migrated = 1 WHERE pnr_code = ?", (row[0],))

    sql_conn.commit()
    print("Успіх! Всі дані перенесено.")


if __name__ == "__main__":
    migrate()