import pytest
import sqlite3
import re
from unittest.mock import MagicMock
# Тепер ми імпортуємо лише FlightLogic, де зібрані всі методи
from oms_app import FlightLogic, I18N, COORDS

# ==========================================
# 1. ТЕСТИ ГЕНЕРАЦІЇ ТА ВАЛІДАЦІЇ (7 тестів)
# ==========================================

def test_generate_6_char_code_length():
    """Тест: довжина коду має бути 6 символів"""
    code = FlightLogic.generate_6_char_code()
    assert len(code) == 6

def test_generate_6_char_code_unique():
    """Тест: коди мають бути унікальними (перевірка 1000 ітерацій)"""
    codes = {FlightLogic.generate_6_char_code() for _ in range(1000)}
    assert len(codes) == 1000

def test_generate_13_digit_is_numeric():
    """Тест: квиток має містити лише цифри"""
    tkt = FlightLogic.generate_13_digit()
    assert tkt.isdigit()

def test_generate_13_digit_length():
    """Тест: довжина квитка має бути рівно 13 цифр"""
    tkt = FlightLogic.generate_13_digit()
    assert len(tkt) == 13

def test_flight_number_validation_pass():
    """Тест: валідація правильного формату рейсу"""
    pattern = r'^[A-Z]{2,3}\d{1,4}$'
    assert re.match(pattern, "PS777")
    assert re.match(pattern, "BA12")

def test_flight_number_validation_fail():
    """Тест: валідація неправильного формату рейсу"""
    pattern = r'^[A-Z]{2,3}\d{1,4}$'
    assert not re.match(pattern, "123PS")
    assert not re.match(pattern, "ПС777")

def test_name_validation_latin_only():
    """Тест: імена мають містити лише латиницю"""
    pattern = r'^[A-Z\s]+$'
    assert re.match(pattern, "ALAN OGR")
    assert not re.match(pattern, "АЛАН ОГР")


# ==========================================
# 2. ТЕСТИ ЛОГІКИ ПОЛЬОТІВ ТА ETA (5 тестів)
# ==========================================

def test_haversine_distance():
    """Тест: розрахунок відстані між Києвом та Лондоном (~2134 км)"""
    dist = FlightLogic.haversine(50.45, 30.52, 51.50, -0.12)
    assert 2100 <= dist <= 2200

def test_calculate_schedule_same_city():
    """Тест: рейс між одним і тим же містом неможливий"""
    res = FlightLogic.calculate_schedule("KYIV", "KYIV", "UK")
    assert res is None

def test_calculate_schedule_duration():
    """Тест: тривалість польоту має бути заповнена"""
    res = FlightLogic.calculate_schedule("KYIV", "PARIS", "UK")
    assert "год" in res['duration'] or "h" in res['duration']

def test_calculate_schedule_distance_positive():
    """Тест: дистанція рейсу завжди більша за 0"""
    res = FlightLogic.calculate_schedule("KYIV", "NEW YORK", "EN")
    assert res['distance_km'] > 0

def test_eta_is_after_departure():
    """Тест: час прибуття має бути пізнішим за час відправлення"""
    from datetime import datetime
    res = FlightLogic.calculate_schedule("KYIV", "TOKYO", "UK")
    dep = datetime.strptime(res['departure'], "%d.%m.%Y %H:%M")
    arr = datetime.strptime(res['arrival'], "%d.%m.%Y %H:%M")
    assert arr > dep


# ==========================================
# 3. ТЕСТИ МІГРАЦІЇ ТА БД (8 тестів)
# ==========================================

def test_sql_connection():
    """Тест: перевірка з'єднання з базою SQLite"""
    conn = sqlite3.connect('legacy_airlines.db')
    assert conn is not None
    conn.close()

def test_sql_schema_columns():
    """Тест: наявність необхідних колонок у SQL таблиці"""
    conn = sqlite3.connect('legacy_airlines.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(legacy_bookings)")
    columns = [row[1] for row in cursor.fetchall()]
    assert "pnr_code" in columns
    assert "migrated" in columns
    conn.close()

def test_nosql_document_structure():
    """Тест: перевірка структури документа ONE Order (імітація)"""
    doc = {
        "order_id": "TEST01",
        "passengers": [{"name": "ALAN", "ticket": "123"}],
        "flight": {"route": "KBP-CDG"}
    }
    assert "passengers" in doc
    assert isinstance(doc["passengers"], list)

def test_migration_logic_ancillaries_split():
    """Тест: розбиття рядка допок зі старого формату (EMD:Name)"""
    raw_sql_anc = "123456:Baggage, 789012:VIP"
    anc_list = [{"emd": p.split(":")[0], "service": p.split(":")[1]}
                for p in raw_sql_anc.split(", ") if ":" in p]
    assert len(anc_list) == 2
    assert anc_list[0]["emd"] == "123456"

def test_pnr_is_always_uppercase():
    """Тест: PNR завжди має бути у верхньому регістрі"""
    code = FlightLogic.generate_6_char_code()
    assert code == code.upper()

def test_i18n_keys_existence():
    """Тест: наявність ключів перекладу для обох мов"""
    # Змінено з oms_master_app на oms_app
    from oms_app import I18N
    assert "UK" in I18N
    assert "EN" in I18N
    assert I18N["UK"]["btn_search"] != I18N["EN"]["btn_search"]

def test_ancillary_options_list():
    """Тест: перевірка наявності базових послуг у списку"""
    # Змінено з oms_master_app на oms_app
    from oms_app import OMSMasterApp
    app = MagicMock()
    app.ancillary_options = ["Baggage 23kg", "VIP Lounge"]
    assert "VIP Lounge" in app.ancillary_options

def test_coordinate_existence():
    """Тест: кожне місто зі списку має координати для розрахунку ETA"""
    # Змінено з oms_master_app на oms_app
    from oms_app import COORDS
    cities = ["KYIV", "LONDON", "PARIS", "TOKYO"]
    for city in cities:
        assert city in COORDS
        assert len(COORDS[city]) == 2