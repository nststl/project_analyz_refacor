import sqlite3
import time
import random
import string
import re
import math
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pymongo import MongoClient

# ==========================================
# 1. СЛОВНИКИ ЛОКАЛІЗАЦІЇ (i18n)
# ==========================================
I18N = {
    'UK': {
        'title': "Система OMS: Перехід на ONE Order",
        'tab_search': "🔍 ПОШУК ЗАМОВЛЕНЬ",
        'tab_mig': "🔄 МІГРАЦІЯ БАЗИ",
        'tab_create': "➕ НОВЕ БРОНЮВАННЯ",
        'search_hdr': "Інтелектуальний пошук (за PNR або Order ID)",
        'btn_search': "ЗНАЙТИ",
        'mig_hdr': "Модуль міграції: Legacy PNR ➔ ONE Order",
        'btn_mig': "РОЗПОЧАТИ МІГРАЦІЮ",
        'create_hdr': "Створення роздрібного замовлення",
        'frame_route': " Деталі маршруту та перельоту ",
        'lbl_from': "Звідки:",
        'lbl_to': "Куди:",
        'lbl_flight': "Рейс (PS777):",
        'lbl_brand': "Авіакомпанія:",
        'lbl_pax': "Пасажирів:",
        'btn_create': "СТВОРИТИ ТА СИНХРОНІЗУВАТИ",
        'lbl_fname': "Ім'я (ENG):",
        'lbl_lname': "Прізвище (ENG):",
        'lbl_anc': "Дод. послуги:",
        'pax_title': " Пасажир #",
        'err_route': "Перевірте міста та формат рейсу!",
        'err_name': "Імена повинні містити лише англійські літери!",
        'err_not_found': "Запис не знайдено.",
        'msg_success': "Замовлення успішно створено!",
        'h': "год", 'm': "хв"
    },
    'EN': {
        'title': "OMS: ONE Order Transition System",
        'tab_search': "🔍 ORDER SEARCH",
        'tab_mig': "🔄 DATABASE MIGRATION",
        'tab_create': "➕ NEW BOOKING",
        'search_hdr': "Smart Search (by PNR or Order ID)",
        'btn_search': "FIND ORDER",
        'mig_hdr': "Migration Module: Legacy PNR ➔ ONE Order",
        'btn_mig': "START MIGRATION",
        'create_hdr': "Create Retail Booking",
        'frame_route': " Flight & Route Details ",
        'lbl_from': "From:",
        'lbl_to': "To:",
        'lbl_flight': "Flight (PS777):",
        'lbl_brand': "Airline:",
        'lbl_pax': "Passengers:",
        'btn_create': "CREATE & SYNC BOOKING",
        'lbl_fname': "First Name:",
        'lbl_lname': "Last Name:",
        'lbl_anc': "Ancillaries:",
        'pax_title': " Passenger #",
        'err_route': "Check route and flight format!",
        'err_name': "Names must contain English letters only!",
        'err_not_found': "Record not found.",
        'msg_success': "Order created successfully!",
        'h': "h", 'm': "m"
    }
}

# ==========================================
# 2. АЛГОРИТМИ ТА РЕАЛІСТИЧНА ФІЗИКА ПОЛЬОТІВ
# ==========================================
COORDS = {
    "LONDON": (51.5074, -0.1278), "PARIS": (48.8566, 2.3522),
    "NEW YORK": (40.7128, -74.0060), "KYIV": (50.4501, 30.5234),
    "ROME": (41.9028, 12.4964), "BERLIN": (52.5200, 13.4050),
    "TOKYO": (35.6762, 139.6503), "WARSAW": (52.2297, 21.0122),
    "DUBAI": (25.2048, 55.2708), "MADRID": (40.4168, -3.7038)
}


class FlightLogic:
    @staticmethod
    def generate_6_char_code():
        return ''.join(random.choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=6))

    @staticmethod
    def generate_13_digit():
        return ''.join(random.choices(string.digits, k=13))

    @staticmethod
    def haversine(lat1, lon1, lat2, lon2):
        """Розрахунок дистанції між координатами в кілометрах"""
        R = 6371
        dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(
            dlon / 2) ** 2
        return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

    @staticmethod
    def calculate_schedule(city_from, city_to, lang):
        if city_from == city_to: return None

        # Відстань + Середня швидкість 800 км/год + 45 хв на зліт/посадку
        distance = FlightLogic.haversine(*COORDS[city_from], *COORDS[city_to])
        total_hours = (distance / 800) + 0.75

        h, m = int(total_hours), int((total_hours - int(total_hours)) * 60)
        dur_str = f"{h} {I18N[lang]['h']} {m} {I18N[lang]['m']}"

        # Випадковий час відправлення в найближчі 30 днів
        dep_time = datetime.now() + timedelta(days=random.randint(1, 30))
        dep_time = dep_time.replace(hour=random.randint(6, 23), minute=random.choice([0, 15, 30, 45]))
        arr_time = dep_time + timedelta(hours=h, minutes=m)

        return {
            "departure": dep_time.strftime("%d.%m.%Y %H:%M"),
            "arrival": arr_time.strftime("%d.%m.%Y %H:%M"),
            "duration": dur_str,
            "distance_km": int(distance)
        }


# ==========================================
# 3. ІНТЕРФЕЙС (GUI)
# ==========================================
class OMSMasterApp:
    def __init__(self, root):
        self.root = root
        self.lang = 'UK'
        self.root.geometry("1100x850")
        self.root.configure(bg="#ffffff")
        self.translatable_widgets = []  # Для миттєвої локалізації

        # Підключення БД
        self.sql_conn = sqlite3.connect('legacy_airlines.db')
        self.sql_cursor = self.sql_conn.cursor()
        self.nosql_col = MongoClient('mongodb://localhost:27017/')['oms_database']['orders']

        self.cities = list(COORDS.keys())
        self.airlines = ["SkyHigh", "LowCostAir", "GlobalWings", "EuroJet"]
        self.ancillary_options = ["Baggage 23kg", "Baggage 32kg", "VIP Lounge", "Fast Track", "Extra Legroom", "Wi-Fi"]

        # Стилі
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=[15, 8])
        self.style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#1a73e8", background="#ffffff")

        # Верхня панель (Перемикач мов)
        top_bar = tk.Frame(self.root, bg="#f8f9fa", height=40)
        top_bar.pack(fill="x", side="top")

        self.lbl_title = tk.Label(top_bar, font=("Segoe UI", 12, "bold"), bg="#f8f9fa", fg="#5f6368")
        self.lbl_title.pack(side="left", padx=15, pady=5)
        self.translatable_widgets.append((self.lbl_title, 'text', 'title'))

        lang_frame = tk.Frame(top_bar, bg="#f8f9fa")
        lang_frame.pack(side="right", padx=15, pady=5)
        tk.Label(lang_frame, text="🌍", bg="#f8f9fa").pack(side="left")
        self.lang_var = tk.StringVar(value="UK")
        ttk.Radiobutton(lang_frame, text="УКР", value="UK", variable=self.lang_var, command=self.switch_lang).pack(
            side="left", padx=5)
        ttk.Radiobutton(lang_frame, text="ENG", value="EN", variable=self.lang_var, command=self.switch_lang).pack(
            side="left", padx=5)

        # Вкладки
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        self.tab_search, self.tab_migrate, self.tab_create = ttk.Frame(self.notebook), ttk.Frame(
            self.notebook), ttk.Frame(self.notebook)
        self.notebook.add(self.tab_search, text='')
        self.notebook.add(self.tab_migrate, text='')
        self.notebook.add(self.tab_create, text='')

        self.build_search_tab()
        self.build_migrate_tab()
        self.build_create_tab()

        self.apply_translations()  # Ініціалізація мови

    def switch_lang(self):
        self.lang = self.lang_var.get()
        self.apply_translations()
        self.refresh_pax_ui()  # Перемалювати пасажирів під нову мову

    def apply_translations(self):
        dict_l = I18N[self.lang]
        for widget, attr, key in self.translatable_widgets:
            if attr == 'text': widget.config(text=dict_l[key])

        self.notebook.tab(self.tab_search, text=dict_l['tab_search'])
        self.notebook.tab(self.tab_migrate, text=dict_l['tab_mig'])
        self.notebook.tab(self.tab_create, text=dict_l['tab_create'])

    def register_widget(self, widget, attr, key):
        self.translatable_widgets.append((widget, attr, key))
        return widget

    # --- ВКЛАДКА: ПОШУК ---
    def build_search_tab(self):
        frame = ttk.Frame(self.tab_search, padding=20)
        frame.pack(fill="both", expand=True)
        self.register_widget(ttk.Label(frame, style="Header.TLabel"), 'text', 'search_hdr').pack(pady=(0, 15))

        bar = ttk.Frame(frame);
        bar.pack(fill="x", pady=5)
        self.search_entry = ttk.Entry(bar, font=("Consolas", 14), width=20);
        self.search_entry.pack(side="left", padx=10)
        btn = self.register_widget(ttk.Button(bar, command=self.do_search), 'text', 'btn_search')
        btn.pack(side="left")

        self.res_search = scrolledtext.ScrolledText(frame, font=("Consolas", 10), bg="#1e1e1e", fg="#00ff00");
        self.res_search.pack(fill="both", expand=True, pady=10)

    def do_search(self):
        q = self.search_entry.get().strip().upper()
        doc = self.nosql_col.find_one({"$or": [{"order_id": q}, {"legacy_pnr": q}]})
        self.res_search.config(state="normal");
        self.res_search.delete(1.0, tk.END)

        if doc:
            # 1. Основна інформація
            txt = f"=== [ ONE ORDER (MongoDB) ] ===\n"
            txt += f"ORDER ID: {doc['order_id']} | PNR: {doc['legacy_pnr']}\n"

            # 2. Бренд та Маршрут (повернув номер рейсу та авіакомпанію)
            brand = doc.get('brand', 'N/A')
            route = doc['flight']['route']
            flight_num = doc['flight']['number']
            txt += f"BRAND: {brand} | ROUTE: {route} ({flight_num})\n"

            # 3. Розширені фізичні дані (якщо вони були згенеровані)
            if 'departure_time' in doc['flight']:
                txt += f"DISTANCE: {doc['flight'].get('distance_km', 'N/A')} km\n"
                txt += f"DEP: {doc['flight']['departure_time']} | ETA: {doc['flight']['arrival_time']} | DURATION: {doc['flight']['duration']}\n"

            txt += "=" * 60 + "\n"

            # 4. Пасажири та послуги
            for p in doc.get('passengers', []):
                txt += f"PAX: {p['name']} (TKT: {p.get('ticket_13_digit', p.get('ticket', 'N/A'))})\n"
                for a in p.get('ancillaries', []):
                    txt += f"  - [{a.get('emd_code', a.get('emd'))}] {a.get('service_name', a.get('service'))}\n"

            self.res_search.insert(tk.END, txt)
        else:
            self.res_search.insert(tk.END, I18N[self.lang]['err_not_found'])

        self.res_search.config(state="disabled")

    # --- ВКЛАДКА: МІГРАЦІЯ ---
    def build_migrate_tab(self):
        frame = ttk.Frame(self.tab_migrate, padding=20)
        frame.pack(fill="both", expand=True)
        self.register_widget(ttk.Label(frame, style="Header.TLabel"), 'text', 'mig_hdr').pack(pady=(0, 15))

        bar = ttk.Frame(frame);
        bar.pack(fill="x", pady=5)
        self.mig_entry = ttk.Entry(bar, font=("Consolas", 14), width=15);
        self.mig_entry.pack(side="left", padx=10)
        self.register_widget(ttk.Button(bar, command=self.do_migrate), 'text', 'btn_mig').pack(side="left")

        self.res_mig = scrolledtext.ScrolledText(frame, font=("Consolas", 10), bg="#ffffff");
        self.res_mig.pack(fill="both", expand=True, pady=10)

    def do_migrate(self):
        pnr = self.mig_entry.get().strip().upper()
        self.sql_cursor.execute("SELECT * FROM legacy_bookings WHERE pnr_code = ?", (pnr,))
        row = self.sql_cursor.fetchone()
        self.res_mig.config(state="normal");
        self.res_mig.delete(1.0, tk.END)

        if not row: self.res_mig.insert(tk.END, "Error: Not Found"); return

        new_id = FlightLogic.generate_6_char_code()
        sched = FlightLogic.calculate_schedule(row[4], row[5], self.lang)

        anc_list = [{"emd": p.split(":")[0], "service": p.split(":")[1]} for p in row[8].split(", ") if ":" in p] if \
        row[8] != "None" else []
        doc = {
            "order_id": new_id, "legacy_pnr": row[0],
            "passengers": [{"name": f"{row[1]} {row[2]}", "ticket": row[7], "ancillaries": anc_list}],
            "flight": {"number": row[3], "route": f"{row[4]} -> {row[5]}", "departure_time": sched['departure'],
                       "arrival_time": sched['arrival'], "duration": sched['duration'],
                       "distance_km": sched['distance_km']},
            "brand": row[6]
        }
        self.nosql_col.insert_one(doc)
        self.sql_cursor.execute("UPDATE legacy_bookings SET migrated = 1 WHERE pnr_code = ?", (pnr,))
        self.sql_conn.commit()
        self.res_mig.insert(tk.END, f"SUCCESS! MIGRATED: {pnr} -> {new_id}")
        self.res_mig.config(state="disabled")

    # --- ВКЛАДКА: СТВОРЕННЯ ---
    def build_create_tab(self):
        canvas = tk.Canvas(self.tab_create, bg="#ffffff", highlightthickness=0)
        scroll = ttk.Scrollbar(self.tab_create, orient="vertical", command=canvas.yview)
        self.scrl_frame = ttk.Frame(canvas, padding=20)
        self.scrl_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scrl_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True);
        scroll.pack(side="right", fill="y")

        self.register_widget(ttk.Label(self.scrl_frame, style="Header.TLabel"), 'text', 'create_hdr').pack(pady=(0, 15))

        rt_fr = self.register_widget(ttk.LabelFrame(self.scrl_frame, padding=15), 'text', 'frame_route')
        rt_fr.pack(fill="x", pady=5)

        self.register_widget(ttk.Label(rt_fr), 'text', 'lbl_from').grid(row=0, column=0, padx=5, sticky="e")
        self.cb_from = ttk.Combobox(rt_fr, values=self.cities, state="readonly");
        self.cb_from.grid(row=0, column=1, padx=5)

        self.register_widget(ttk.Label(rt_fr), 'text', 'lbl_to').grid(row=0, column=2, padx=5, sticky="e")
        self.cb_to = ttk.Combobox(rt_fr, values=self.cities, state="readonly");
        self.cb_to.grid(row=0, column=3, padx=5)

        self.register_widget(ttk.Label(rt_fr), 'text', 'lbl_flight').grid(row=1, column=0, padx=5, sticky="e")
        self.ent_flight = ttk.Entry(rt_fr);
        self.ent_flight.grid(row=1, column=1, padx=5)

        self.register_widget(ttk.Label(rt_fr), 'text', 'lbl_pax').grid(row=1, column=2, padx=5, sticky="e")
        self.pax_var = tk.StringVar(value="1")
        self.cb_pax = ttk.Combobox(rt_fr, textvariable=self.pax_var, values=["1", "2", "3", "4", "5"], state="readonly",
                                   width=5)
        self.cb_pax.grid(row=1, column=3, padx=5, sticky="w")
        self.cb_pax.bind("<<ComboboxSelected>>", lambda e: self.refresh_pax_ui())

        self.pax_container = ttk.Frame(self.scrl_frame);
        self.pax_container.pack(fill="x", pady=10)
        self.pax_entries = []
        self.refresh_pax_ui()

        self.register_widget(ttk.Button(self.scrl_frame, command=self.do_create, style="Action.TButton"), 'text',
                             'btn_create').pack(pady=15)
        self.res_create = tk.Text(self.scrl_frame, height=6, font=("Consolas", 10));
        self.res_create.pack(fill="x")

    def refresh_pax_ui(self):
        for w in self.pax_container.winfo_children(): w.destroy()
        self.pax_entries = []
        for i in range(int(self.pax_var.get())):
            f = ttk.LabelFrame(self.pax_container, text=f"{I18N[self.lang]['pax_title']}{i + 1}", padding=10)
            f.pack(fill="x", pady=5)

            tk.Label(f, text=I18N[self.lang]['lbl_fname'], bg="#ffffff").grid(row=0, column=0, sticky="e")
            fn = ttk.Entry(f);
            fn.grid(row=0, column=1, padx=5)

            tk.Label(f, text=I18N[self.lang]['lbl_lname'], bg="#ffffff").grid(row=0, column=2, sticky="e")
            ln = ttk.Entry(f);
            ln.grid(row=0, column=3, padx=5)

            tk.Label(f, text=I18N[self.lang]['lbl_anc'], bg="#ffffff").grid(row=0, column=4, sticky="e")
            lb = tk.Listbox(f, selectmode=tk.MULTIPLE, height=3, exportselection=0, font=("Segoe UI", 9))
            for o in self.ancillary_options: lb.insert(tk.END, o)
            lb.grid(row=0, column=5, padx=5)

            self.pax_entries.append({'fn': fn, 'ln': ln, 'anc': lb})

    def do_create(self):
        flight, c_from, c_to = self.ent_flight.get().strip().upper(), self.cb_from.get(), self.cb_to.get()
        if not (re.match(r'^[A-Z]{2,3}\d{1,4}$', flight) and c_from and c_to and c_from != c_to):
            messagebox.showerror("Error", I18N[self.lang]['err_route']);
            return

        modern_id, legacy_pnr = FlightLogic.generate_6_char_code(), FlightLogic.generate_6_char_code()
        sched = FlightLogic.calculate_schedule(c_from, c_to, self.lang)
        pax_docs, sql_n, sql_t, sql_a = [], [], [], []

        for p in self.pax_entries:
            fn, ln = p['fn'].get().strip().upper(), p['ln'].get().strip().upper()
            if not (re.match(r'^[A-Z\s]+$', fn) and re.match(r'^[A-Z\s]+$', ln)):
                messagebox.showerror("Error", I18N[self.lang]['err_name']);
                return

            tkt, p_anc = FlightLogic.generate_13_digit(), []
            for idx in p['anc'].curselection():
                name = p['anc'].get(idx)
                emd = FlightLogic.generate_13_digit()
                p_anc.append({"emd": emd, "service": name});
                sql_a.append(f"{emd}:{name}")
            pax_docs.append({"name": f"{fn} {ln}", "ticket": tkt, "ancillaries": p_anc})
            sql_n.append(f"{fn} {ln}");
            sql_t.append(tkt)

        self.sql_cursor.execute("INSERT INTO legacy_bookings VALUES (?,?,?,?,?,?,?,?,?,?)",
                                (legacy_pnr, ", ".join(sql_n), "", flight, c_from, c_to, "SkyHigh", ", ".join(sql_t),
                                 ", ".join(sql_a) if sql_a else "None", 1))
        self.sql_conn.commit()

        self.nosql_col.insert_one({
            "order_id": modern_id, "legacy_pnr": legacy_pnr, "passengers": pax_docs, "brand": "SkyHigh",
            "flight": {"number": flight, "route": f"{c_from} -> {c_to}", "departure_time": sched['departure'],
                       "arrival_time": sched['arrival'], "duration": sched['duration'],
                       "distance_km": sched['distance_km']}
        })

        self.res_create.delete(1.0, tk.END)
        self.res_create.insert(tk.END,
                               f"{I18N[self.lang]['msg_success']}\nOrder ID: {modern_id} | Legacy PNR: {legacy_pnr}\nDEP: {sched['departure']} | ETA: {sched['arrival']} | Duration: {sched['duration']}")


if __name__ == "__main__":
    root = tk.Tk();
    OMSMasterApp(root).root.mainloop()