import sqlite3
import time
import random
import string
import re
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pymongo import MongoClient

# ==========================================
# 1. ПІДКЛЮЧЕННЯ БАЗ
# ==========================================
sql_conn = sqlite3.connect('legacy_airlines.db')
sql_cursor = sql_conn.cursor()
mongo_client = MongoClient('mongodb://localhost:27017/')
nosql_col = mongo_client['oms_database']['orders']


# ==========================================
# 2. РУЧНІ АЛГОРИТМИ ГЕНЕРАЦІЇ
# ==========================================
class IDGenerator:
    CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    @staticmethod
    def generate_6_char_code() -> str:
        timestamp = int(time.time_ns())
        code = ""
        temp_val = timestamp
        for _ in range(6):
            index = temp_val % len(IDGenerator.CHARS)
            code = IDGenerator.CHARS[index] + code
            temp_val //= len(IDGenerator.CHARS)
        return code

    @staticmethod
    def generate_13_digit() -> str:
        return ''.join(random.choices(string.digits, k=13))


# ==========================================
# 3. ІНТЕРФЕЙС ТА ЛОГІКА
# ==========================================
class OMSMasterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OMS: ONE Order Transition System")
        self.root.geometry("1050x900")
        self.root.configure(bg="#ffffff")

        # Налаштування стилів
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=[15, 8])
        self.style.configure("TFrame", background="#ffffff")
        self.style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#1a73e8", background="#ffffff")
        self.style.configure("Action.TButton", font=("Segoe UI", 10, "bold"), padding=10)

        # Дані
        self.cities = ["LONDON", "PARIS", "NEW YORK", "KYIV", "ROME", "BERLIN", "TOKYO", "WARSAW", "DUBAI", "MADRID"]
        self.airlines = ["SkyHigh", "LowCostAir", "GlobalWings", "EuroJet", "Oceanic", "FlyDirect"]
        self.ancillary_options = [
            "Baggage 23kg", "Baggage 32kg", "VIP Lounge", "Fast Track",
            "Extra Legroom", "Wi-Fi Standard", "Wi-Fi Premium",
            "Meal: Vegan", "Meal: Kosher", "Meal: Low Salt",
            "Priority Boarding", "Travel Insurance", "Pet in Cabin"
        ]

        # Вкладки
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        self.tab_search = ttk.Frame(self.notebook)
        self.tab_migrate = ttk.Frame(self.notebook)
        self.tab_create = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_search, text=' 🔍 ПОШУК ')
        self.notebook.add(self.tab_migrate, text=' 🔄 МІГРАЦІЯ ')
        self.notebook.add(self.tab_create, text=' ➕ НОВЕ БРОНЮВАННЯ ')

        self.build_search_tab()
        self.build_migrate_tab()
        self.build_create_tab()

    # ------------------------------------------
    # Вкладка 1: ПОШУК (Універсальний)
    # ------------------------------------------
    def build_search_tab(self):
        main_frame = ttk.Frame(self.tab_search, padding=30)
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="Пошук у гібридній архітектурі (PNR / Order ID)", style="Header.TLabel").pack(
            pady=(0, 20))

        search_bar = ttk.Frame(main_frame)
        search_bar.pack(fill="x", pady=10)

        self.search_entry = ttk.Entry(search_bar, font=("Consolas", 14), width=20)
        self.search_entry.pack(side="left", padx=(0, 10))
        ttk.Button(search_bar, text="ЗНАЙТИ", command=self.do_search).pack(side="left")

        self.res_search = scrolledtext.ScrolledText(main_frame, height=35, font=("Consolas", 10), bg="#1e1e1e",
                                                    fg="#00ff00")
        self.res_search.pack(fill="both", expand=True, pady=10)

    def do_search(self):
        query = self.search_entry.get().strip().upper()
        if len(query) != 6:
            messagebox.showwarning("Помилка", "Код має містити 6 символів.")
            return

        doc = nosql_col.find_one({"$or": [{"order_id": query}, {"legacy_pnr": query}]})
        self.res_search.config(state="normal")
        self.res_search.delete(1.0, tk.END)

        if doc:
            content = f"--- [ ЗНАЙДЕНО В ONE ORDER (NoSQL) ] ---\n\n"
            content += f"ORDER ID: {doc.get('order_id')}\nLEGACY PNR: {doc.get('legacy_pnr')}\n"
            content += f"BRAND: {doc.get('brand')} | ROUTE: {doc['flight']['route']}\n"
            content += "-" * 55 + "\n"

            # Блок безпечного виводу пасажирів
            for p in doc.get('passengers', []):
                # Намагаємось знайти 'ticket', якщо його немає — 'ticket_13_digit'
                ticket_num = p.get('ticket') or p.get('ticket_13_digit') or "N/A"

                content += f"ПАСАЖИР: {p.get('name', 'N/A')}\n"
                content += f"   Квиток: {ticket_num}\n"
                content += f"   Послуги:\n"

                ancs = p.get('ancillaries', [])
                if ancs:
                    for a in ancs:
                        # Використовуємо .get для кожної властивості послуги
                        emd = a.get('emd_code') or a.get('emd') or "N/A"
                        srv = a.get('service_name') or a.get('service') or "Опція"
                        content += f"     > [EMD {emd}] {srv}\n"
                else:
                    content += "     > Немає додаткових послуг\n"

            self.res_search.insert(tk.END, content)
        else:
            # Логіка пошуку в SQL (залишається як була)
            sql_cursor.execute("SELECT * FROM legacy_bookings WHERE pnr_code = ?", (query,))
            row = sql_cursor.fetchone()
            if row:
                content = f"--- [ ЗНАЙДЕНО В LEGACY SYSTEM (SQL) ] ---\n\nPNR: {row[0]}\nІм'я: {row[1]}"
                self.res_search.insert(tk.END, content)
            else:
                self.res_search.insert(tk.END, ">>> ЗАПИС НЕ ЗНАЙДЕНО.")

        self.res_search.config(state="disabled")

    # ------------------------------------------
    # Вкладка 2: МІГРАЦІЯ (Перетворення PNR)
    # ------------------------------------------
    def build_migrate_tab(self):
        main_frame = ttk.Frame(self.tab_migrate, padding=30)
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="Інструмент міграції PNR -> ONE Order", style="Header.TLabel").pack(pady=(0, 20))

        mig_bar = ttk.Frame(main_frame)
        mig_bar.pack(fill="x", pady=10)

        self.mig_entry = ttk.Entry(mig_bar, font=("Consolas", 14), width=15)
        self.mig_entry.pack(side="left", padx=(0, 10))
        ttk.Button(mig_bar, text="ПОЧАТИ МІГРАЦІЮ", command=self.do_migrate).pack(side="left")

        self.res_mig = scrolledtext.ScrolledText(main_frame, height=20, font=("Consolas", 10), bg="#ffffff")
        self.res_mig.pack(fill="both", expand=True, pady=10)

    def do_migrate(self):
        pnr = self.mig_entry.get().strip().upper()
        sql_cursor.execute("SELECT * FROM legacy_bookings WHERE pnr_code = ?", (pnr,))
        row = sql_cursor.fetchone()

        self.res_mig.config(state="normal");
        self.res_mig.delete(1.0, tk.END)
        if not row: self.res_mig.insert(tk.END, "❌ Помилка: PNR не знайдено."); self.res_mig.config(
            state="disabled"); return
        if row[9]: self.res_mig.insert(tk.END, "ℹ️ Цей запис вже мігрований."); self.res_mig.config(
            state="disabled"); return

        new_id = IDGenerator.generate_6_char_code()

        # Розбір допок зі старого формату (текст) у масив NoSQL
        anc_list = []
        if row[8] != "None":
            for item in row[8].split(", "):
                parts = item.split(":")
                if len(parts) == 2: anc_list.append({"emd": parts[0], "service": parts[1]})

        doc = {
            "order_id": new_id, "legacy_pnr": row[0],
            "passengers": [{"name": f"{row[1]} {row[2]}", "ticket": row[7], "ancillaries": anc_list}],
            "flight": {"number": row[3], "route": f"{row[4]} -> {row[5]}"},
            "brand": row[6]
        }
        nosql_col.insert_one(doc)
        sql_cursor.execute("UPDATE legacy_bookings SET migrated = 1 WHERE pnr_code = ?", (pnr,))
        sql_conn.commit()

        self.res_mig.insert(tk.END, f"✅ УСПІХ!\n\nPNR {pnr} перетворено на Order {new_id}.\nДані записані в MongoDB.")
        self.res_mig.config(state="disabled")

    # ------------------------------------------
    # Вкладка 3: НОВЕ БРОНЮВАННЯ (З індивідуальними послугами)
    # ------------------------------------------
    def build_create_tab(self):
        self.canvas = tk.Canvas(self.tab_create, bg="#ffffff", highlightthickness=0)
        self.scroll_y = ttk.Scrollbar(self.tab_create, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = ttk.Frame(self.canvas, padding=20)

        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scroll_y.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scroll_y.pack(side="right", fill="y")

        ttk.Label(self.scroll_frame, text="Створення нового роздрібного замовлення", style="Header.TLabel").pack(
            pady=(0, 20))

        # Блок рейсу
        route_frame = ttk.LabelFrame(self.scroll_frame, text=" Деталі перельоту ", padding=15)
        route_frame.pack(fill="x", pady=10)

        ttk.Label(route_frame, text="FROM:").grid(row=0, column=0, padx=5, pady=5)
        self.cb_from = ttk.Combobox(route_frame, values=self.cities, state="readonly");
        self.cb_from.grid(row=0, column=1, padx=5)

        ttk.Label(route_frame, text="TO:").grid(row=0, column=2, padx=5, pady=5)
        self.cb_to = ttk.Combobox(route_frame, values=self.cities, state="readonly");
        self.cb_to.grid(row=0, column=3, padx=5)

        ttk.Label(route_frame, text="FLIGHT:").grid(row=1, column=0, padx=5, pady=5)
        self.ent_flight = ttk.Entry(route_frame);
        self.ent_flight.grid(row=1, column=1, padx=5)

        ttk.Label(route_frame, text="AIRLINE:").grid(row=1, column=2, padx=5, pady=5)
        self.cb_brand = ttk.Combobox(route_frame, values=self.airlines, state="readonly");
        self.cb_brand.grid(row=1, column=3, padx=5)
        self.cb_brand.set(self.airlines[0])

        ttk.Label(route_frame, text="PASSENGERS:").grid(row=2, column=0, padx=5, pady=5)
        self.pax_count_var = tk.StringVar(value="1")
        self.cb_pax_count = ttk.Combobox(route_frame, textvariable=self.pax_count_var, values=["1", "2", "3", "4"],
                                         state="readonly", width=5)
        self.cb_pax_count.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        self.cb_pax_count.bind("<<ComboboxSelected>>", lambda e: self.refresh_pax_ui())

        self.pax_container = ttk.Frame(self.scroll_frame)
        self.pax_container.pack(fill="x", pady=10)
        self.pax_entries = []
        self.refresh_pax_ui()

        ttk.Button(self.scroll_frame, text="ПІДТВЕРДИТИ ТА СИНХРОНІЗУВАТИ", command=self.do_create).pack(pady=20)
        self.res_create = tk.Text(self.scroll_frame, height=8, font=("Consolas", 10))
        self.res_create.pack(fill="x")

    def refresh_pax_ui(self):
        for w in self.pax_container.winfo_children(): w.destroy()
        self.pax_entries = []
        for i in range(int(self.pax_count_var.get())):
            f = ttk.LabelFrame(self.pax_container, text=f" Пасажир #{i + 1} ", padding=10)
            f.pack(fill="x", pady=5)
            ttk.Label(f, text="Name:").grid(row=0, column=0)
            fn = ttk.Entry(f);
            fn.grid(row=0, column=1, padx=5)
            ttk.Label(f, text="Surname:").grid(row=0, column=2)
            ln = ttk.Entry(f);
            ln.grid(row=0, column=3, padx=5)
            ttk.Label(f, text="Services:").grid(row=0, column=4, padx=5)
            lb = tk.Listbox(f, selectmode=tk.MULTIPLE, height=3, exportselection=0)
            for o in self.ancillary_options: lb.insert(tk.END, o)
            lb.grid(row=0, column=5, padx=5)
            self.pax_entries.append({'fn': fn, 'ln': ln, 'anc': lb})

    def do_create(self):
        flight = self.ent_flight.get().strip().upper()
        c_from, c_to = self.cb_from.get(), self.cb_to.get()
        if not (re.match(r'^[A-Z]{2}\d{1,4}$', flight) and c_from and c_to and c_from != c_to):
            messagebox.showerror("Error", "Invalid Route or Flight format!");
            return

        modern_id = IDGenerator.generate_6_char_code()
        legacy_pnr = IDGenerator.generate_6_char_code()
        pax_docs, sql_names, sql_tkts, sql_anc = [], [], [], []

        for p in self.pax_entries:
            fn, ln = p['fn'].get().strip().upper(), p['ln'].get().strip().upper()
            if not (fn.isalpha() and ln.isalpha()): messagebox.showerror("Error",
                                                                         "Names must be Latin letters!"); return

            tkt = IDGenerator.generate_13_digit();
            p_anc = []
            for idx in p['anc'].curselection():
                name = p['anc'].get(idx);
                emd = IDGenerator.generate_13_digit()
                p_anc.append({"emd": emd, "service": name});
                sql_anc.append(f"{emd}:{name}")

            pax_docs.append({"name": f"{fn} {ln}", "ticket": tkt, "ancillaries": p_anc})
            sql_names.append(f"{fn} {ln}");
            sql_tkts.append(tkt)

        sql_cursor.execute("INSERT INTO legacy_bookings VALUES (?,?,?,?,?,?,?,?,?,?)",
                           (legacy_pnr, ", ".join(sql_names), "", flight, c_from, c_to, self.cb_brand.get(),
                            ", ".join(sql_tkts), ", ".join(sql_anc) if sql_anc else "None", 1))
        sql_conn.commit()

        nosql_col.insert_one({"order_id": modern_id, "legacy_pnr": legacy_pnr, "passengers": pax_docs,
                              "flight": {"number": flight, "route": f"{c_from} -> {c_to}"},
                              "brand": self.cb_brand.get()})

        self.res_create.delete(1.0, tk.END);
        self.res_create.insert(tk.END, f"✅ SUCCESS!\nOrder ID: {modern_id}\nLegacy PNR: {legacy_pnr}")
        messagebox.showinfo("Done", "Order Created Successfully!")


if __name__ == "__main__":
    root = tk.Tk();
    OMSMasterApp(root).root.mainloop()