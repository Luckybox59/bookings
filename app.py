"""
GUI-приложение для управления бронированиями в ресторане.

Это приложение предоставляет интерфейс для управления пользователями, столами и бронированиями.
Оно использует tkinter для создания графического интерфейса.
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Any

from backend import (
    db,
    create_user,
    get_user_by_id,
    update_user,
    delete_user,
    create_table_rec,
    get_table,
    update_table_rec,
    delete_table,
    is_table_available,
    create_booking,
    get_booking,
    update_booking_times,
    set_booking_status,
    cancel_booking,
)
from models.users import User
from models.tables import Table
from models.booking import Booking


def parse_dt(s: str) -> datetime:
    """
    Парсит строку в объект datetime.

    Args:
        s: Строка с датой и временем в формате "YYYY-MM-DD HH:MM".

    Returns:
        Объект datetime.
    """
    return datetime.strptime(s.strip(), "%Y-%m-%d %H:%M")


class App(tk.Tk):
    """
    Основной класс приложения, который инициализирует главное окно и вкладки.
    """
    def __init__(self) -> None:
        super().__init__()
        self.title("Бронирование столов")
        self.geometry("1100x650")

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True)

        self.users_tab = UsersTab(nb)
        self.tables_tab = TablesTab(nb)
        self.bookings_tab = BookingsTab(nb)

        nb.add(self.users_tab, text="Пользователи")
        nb.add(self.tables_tab, text="Столы")
        nb.add(self.bookings_tab, text="Бронирования")


class UsersTab(ttk.Frame):
    """
    Вкладка для управления пользователями (создание, обновление, удаление, просмотр).
    """
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)

        form = ttk.Frame(self)
        form.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        self.var_email = tk.StringVar()
        self.var_full_name = tk.StringVar()
        self.var_phone = tk.StringVar()

        ttk.Label(form, text="Email").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_email, width=30).grid(row=0, column=1)
        ttk.Label(form, text="Полное имя").grid(row=1, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_full_name, width=30).grid(row=1, column=1)
        ttk.Label(form, text="Телефон").grid(row=2, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_phone, width=30).grid(row=2, column=1)

        btns = ttk.Frame(form)
        btns.grid(row=3, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(btns, text="Создать", command=self.on_create).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="Обновить", command=self.on_update).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="Удалить", command=self.on_delete).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="Обновить список", command=self.load).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="Очистить", command=self.clear_form).pack(side=tk.LEFT, padx=5)

        table_frame = ttk.Frame(self)
        table_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        cols = ("id", "email", "created_at", "updated_at")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols:
            header = {
                "id": "ID",
                "email": "Email",
                "created_at": "Создан",
                "updated_at": "Обновлён",
            }.get(c, c)
            self.tree.heading(c, text=header)
            self.tree.column(c, width=150 if c != "id" else 60, anchor="w")
        ysb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=ysb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self.on_pick)

        self._selected_id: int | None = None
        self.load()

    def load(self) -> None:
        """
        Загружает и отображает список пользователей в таблице.
        """
        for i in self.tree.get_children():
            self.tree.delete(i)
        with db.connect() as conn:
            rows = conn.fetchall("SELECT id,email,created_at,updated_at FROM users ORDER BY id DESC")
        for r in rows:
            if isinstance(r, dict):
                self.tree.insert("", tk.END, values=(r["id"], r["email"], r.get("created_at"), r.get("updated_at")))
            else:
                self.tree.insert("", tk.END, values=r)

    def on_pick(self, _evt=None) -> None:
        """
        Обработчик события выбора пользователя в таблице.
        Заполняет форму данными выбранного пользователя.
        """
        item = self.tree.selection()
        if not item:
            return
        vals = self.tree.item(item[0], "values")
        user_id = int(vals[0])
        u = get_user_by_id(user_id)
        if not u:
            return
        self._selected_id = user_id
        self.var_email.set(u.email)
        self.var_full_name.set(u.full_name or "")
        self.var_phone.set(u.phone or "")

    def clear_form(self) -> None:
        """
        Очищает поля формы и сбрасывает выбор.
        """
        self._selected_id = None
        self.var_email.set("")
        self.var_full_name.set("")
        self.var_phone.set("")

    def on_create(self) -> None:
        """
        Обработчик нажатия кнопки "Создать".
        Создает нового пользователя с данными из формы.
        """
        try:
            if not self.var_email.get().strip():
                messagebox.showerror("Ошибка", "Нужно указать Email")
                return
            u = User(
                id=None,
                email=self.var_email.get().strip(),
                full_name=self.var_full_name.get().strip() or None,
                phone=self.var_phone.get().strip() or None,
                created_at=None,
                updated_at=None,
            )
            new_id = create_user(u)
            messagebox.showinfo("Готово", f"Создан пользователь id={new_id}")
            self.load()
            self.clear_form()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def on_update(self) -> None:
        """
        Обработчик нажатия кнопки "Обновить".
        Обновляет данные выбранного пользователя.
        """
        if self._selected_id is None:
            messagebox.showerror("Ошибка", "Сначала выберите пользователя")
            return
        try:
            u = User(
                id=self._selected_id,
                email=self.var_email.get().strip(),
                full_name=self.var_full_name.get().strip() or None,
                phone=self.var_phone.get().strip() or None,
                created_at=None,
                updated_at=None,
            )
            n = update_user(u)
            messagebox.showinfo("Готово", f"Обновлено: {n}")
            self.load()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def on_delete(self) -> None:
        """
        Обработчик нажатия кнопки "Удалить".
        Удаляет выбранного пользователя.
        """
        if self._selected_id is None:
            messagebox.showerror("Ошибка", "Сначала выберите пользователя")
            return
        try:
            n = delete_user(self._selected_id)
            messagebox.showinfo("Готово", f"Удалено: {n}")
            self.load()
            self.clear_form()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))


class TablesTab(ttk.Frame):
    """
    Вкладка для управления столами.
    """
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)

        form = ttk.Frame(self)
        form.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        self.v_number = tk.StringVar()
        self.v_capacity = tk.StringVar()
        self.v_zone = tk.StringVar()
        self.v_status = tk.StringVar(value="Активен")
        self.v_notes = tk.StringVar()
        self._selected_id: int | None = None

        r = 0
        for label, var in (("Номер", self.v_number), ("Вместимость", self.v_capacity)):
            ttk.Label(form, text=label).grid(row=r, column=0, sticky="w")
            ttk.Entry(form, textvariable=var, width=30).grid(row=r, column=1)
            r += 1

        ttk.Label(form, text="Зона").grid(row=r, column=0, sticky="w")
        ttk.Combobox(form, textvariable=self.v_zone, values=["Основной зал", "У окна", "Терраса", "Бар", "VIP"], width=27).grid(row=r, column=1); r+=1
        ttk.Label(form, text="Статус").grid(row=r, column=0, sticky="w")
        ttk.Combobox(form, textvariable=self.v_status, values=["Активен", "Обслуживание", "Скрыт"], width=27, state="readonly").grid(row=r, column=1); r+=1
        ttk.Label(form, text="Заметки").grid(row=r, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.v_notes, width=30).grid(row=r, column=1); r+=1

        btns = ttk.Frame(form)
        btns.grid(row=r, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(btns, text="Создать", command=self.on_create).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="Обновить", command=self.on_update).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="Удалить", command=self.on_delete).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="Обновить список", command=self.load).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="Очистить", command=self.clear_form).pack(side=tk.LEFT, padx=5)

        table_frame = ttk.Frame(self)
        table_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        cols = ("id","number","capacity","zone","status","notes","created_at","updated_at")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols:
            header = {
                "id": "ID",
                "number": "Номер",
                "capacity": "Вместимость",
                "zone": "Зона",
                "status": "Статус",
                "notes": "Заметки",
                "created_at": "Создан",
                "updated_at": "Обновлён",
            }.get(c, c)
            self.tree.heading(c, text=header)
            self.tree.column(c, width=140 if c != "id" else 60, anchor="w")
        ysb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=ysb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self.on_pick)

        self.load()

    def load(self) -> None:
        """
        Загружает и отображает список столов в таблице.
        """
        for i in self.tree.get_children():
            self.tree.delete(i)
        with db.connect() as conn:
            rows = conn.fetchall("SELECT id,number,capacity,zone,status,notes,created_at,updated_at FROM tables ORDER BY id DESC")
        for r in rows:
            if isinstance(r, dict):
                self.tree.insert("", tk.END, values=(
                    r.get("id"), r.get("number"), r.get("capacity"), r.get("zone"), 
                    r.get("status"), r.get("notes"), r.get("created_at"), r.get("updated_at")
                ))
            else:
                self.tree.insert("", tk.END, values=r)

    def on_pick(self, _evt=None) -> None:
        """
        Обработчик события выбора стола в таблице.
        Заполняет форму данными выбранного стола.
        """
        item = self.tree.selection()
        if not item:
            return
        vals = self.tree.item(item[0], "values")
        table_id = int(vals[0])
        t = get_table(table_id)
        if not t:
            return
        self._selected_id = table_id
        self.v_number.set(str(t.number))
        self.v_capacity.set(str(t.capacity))
        self.v_zone.set(t.zone or "")
        self.v_status.set(t.status)
        self.v_notes.set(t.notes or "")

    def clear_form(self) -> None:
        """
        Очищает поля формы и сбрасывает выбор.
        """
        self._selected_id = None
        for v in (self.v_number, self.v_capacity, self.v_zone, self.v_notes):
            v.set("")
        self.v_status.set("Активен")

    def on_create(self) -> None:
        """
        Обработчик нажатия кнопки "Создать".
        Создает новый стол с данными из формы.
        """
        try:
            number = int(self.v_number.get())
            capacity = int(self.v_capacity.get())
            t = Table(
                id=None,
                number=number,
                capacity=capacity,
                zone=self.v_zone.get().strip() or None,
                status=self.v_status.get(),
                notes=self.v_notes.get().strip() or None,
                created_at=None,
                updated_at=None,
            )
            new_id = create_table_rec(t)
            messagebox.showinfo("Готово", f"Создан стол id={new_id}")
            self.load()
            self.clear_form()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def on_update(self) -> None:
        """
        Обработчик нажатия кнопки "Обновить".
        Обновляет данные выбранного стола.
        """
        if self._selected_id is None:
            messagebox.showerror("Ошибка", "Сначала выберите стол")
            return
        try:
            number = int(self.v_number.get())
            capacity = int(self.v_capacity.get())
            t = Table(
                id=self._selected_id,
                number=number,
                capacity=capacity,
                zone=self.v_zone.get().strip() or None,
                status=self.v_status.get(),
                notes=self.v_notes.get().strip() or None,
                created_at=None,
                updated_at=None,
            )
            n = update_table_rec(t)
            messagebox.showinfo("Готово", f"Обновлено: {n}")
            self.load()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def on_delete(self) -> None:
        """
        Обработчик нажатия кнопки "Удалить".
        Удаляет выбранный стол.
        """
        if self._selected_id is None:
            messagebox.showerror("Ошибка", "Сначала выберите стол")
            return
        try:
            n = delete_table(self._selected_id)
            messagebox.showinfo("Готово", f"Удалено: {n}")
            self.load()
            self.clear_form()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))


class BookingsTab(ttk.Frame):
    """
    Вкладка для управления бронированиями.
    """
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)

        form = ttk.Frame(self)
        form.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        self.v_user_id = tk.StringVar()
        self.v_table_id = tk.StringVar()
        self.v_starts = tk.StringVar()
        self.v_ends = tk.StringVar()
        self.v_guests = tk.StringVar()
        self.v_status = tk.StringVar(value="Ожидание")
        self.v_contact_name = tk.StringVar()
        self.v_contact_phone = tk.StringVar()
        self.v_notes = tk.StringVar()

        r = 0
        for label, var in (
            ("ID пользователя", self.v_user_id),
            ("ID стола", self.v_table_id),
            ("Начало (ГГГГ-ММ-ДД ЧЧ:ММ)", self.v_starts),
            ("Конец (ГГГГ-ММ-ДД ЧЧ:ММ)", self.v_ends),
            ("Гостей", self.v_guests),
            ("Статус", self.v_status),
            ("Контактное имя", self.v_contact_name),
            ("Контактный телефон", self.v_contact_phone),
            ("Заметки", self.v_notes),
        ):
            ttk.Label(form, text=label).grid(row=r, column=0, sticky="w")
            ttk.Entry(form, textvariable=var, width=32).grid(row=r, column=1)
            r += 1

        btns = ttk.Frame(form)
        btns.grid(row=r, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(btns, text="Создать", command=self.on_create).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="Изменить время", command=self.on_update_times).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="Изменить статус", command=self.on_set_status).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="Отменить", command=self.on_cancel).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="Обновить список", command=self.load).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="Очистить", command=self.clear_form).pack(side=tk.LEFT, padx=5)

        table_frame = ttk.Frame(self)
        table_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        cols = ("id","user_id","table_id","starts_at","ends_at","status","guest_count","created_at","updated_at")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols:
            header = {
                "id": "ID",
                "user_id": "Пользователь",
                "table_id": "Стол",
                "starts_at": "Начало",
                "ends_at": "Конец",
                "status": "Статус",
                "guest_count": "Гостей",
                "created_at": "Создан",
                "updated_at": "Обновлён",
            }.get(c, c)
            self.tree.heading(c, text=header)
            self.tree.column(c, width=150 if c not in ("id","user_id","table_id") else 80, anchor="w")
        ysb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=ysb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self.on_pick)

        self._selected_id: int | None = None
        self.load()

    def load(self) -> None:
        """
        Загружает и отображает список бронирований в таблице.
        """
        for i in self.tree.get_children():
            self.tree.delete(i)
        with db.connect() as conn:
            rows = conn.fetchall(
                "SELECT id,user_id,table_id,starts_at,ends_at,status,guest_count,created_at,updated_at FROM bookings ORDER BY id DESC"
            )
        for r in rows:
            if isinstance(r, dict):
                self.tree.insert("", tk.END, values=(
                    r.get("id"), r.get("user_id"), r.get("table_id"), r.get("starts_at"),
                    r.get("ends_at"), r.get("status"), r.get("guest_count"),
                    r.get("created_at"), r.get("updated_at")
                ))
            else:
                self.tree.insert("", tk.END, values=r)

    def on_pick(self, _evt=None) -> None:
        """
        Обработчик события выбора бронирования в таблице.
        Заполняет форму данными выбранного бронирования.
        """
        item = self.tree.selection()
        if not item:
            return
        vals = self.tree.item(item[0], "values")
        self._selected_id = int(vals[0])
        bk = get_booking(self._selected_id)
        if not bk:
            return
        self.v_user_id.set(str(bk.user_id))
        self.v_table_id.set(str(bk.table_id))
        self.v_starts.set(bk.starts_at.strftime("%Y-%m-%d %H:%M"))
        self.v_ends.set(bk.ends_at.strftime("%Y-%m-%d %H:%M"))
        self.v_guests.set(str(bk.guest_count))
        self.v_status.set(bk.status)
        self.v_contact_name.set(bk.contact_name or "")
        self.v_contact_phone.set(bk.contact_phone or "")
        self.v_notes.set(bk.notes or "")

    def clear_form(self) -> None:
        """
        Очищает поля формы и сбрасывает выбор.
        """
        self._selected_id = None
        for v in (
            self.v_user_id,
            self.v_table_id,
            self.v_starts,
            self.v_ends,
            self.v_guests,
            self.v_status,
            self.v_contact_name,
            self.v_contact_phone,
            self.v_notes,
        ):
            v.set("")
        self.v_status.set("Ожидание")

    def on_create(self) -> None:
        """
        Обработчик нажатия кнопки "Создать".
        Создает новое бронирование с данными из формы.
        """
        try:
            b = Booking(
                id=None,
                user_id=int(self.v_user_id.get()),
                table_id=int(self.v_table_id.get()),
                starts_at=parse_dt(self.v_starts.get()),
                ends_at=parse_dt(self.v_ends.get()),
                guest_count=int(self.v_guests.get()),
                status=self.v_status.get() or "Ожидание",
                contact_name=self.v_contact_name.get().strip() or None,
                contact_phone=self.v_contact_phone.get().strip() or None,
                notes=self.v_notes.get().strip() or None,
                created_at=None,
                updated_at=None,
            )
            new_id = create_booking(b)
            messagebox.showinfo("Готово", f"Создано бронирование id={new_id}")
            self.load()
            self.clear_form()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def on_update_times(self) -> None:
        """
        Обработчик нажатия кнопки "Изменить время".
        Обновляет время и количество гостей для выбранного бронирования.
        """
        if self._selected_id is None:
            messagebox.showerror("Ошибка", "Сначала выберите бронирование")
            return
        try:
            starts = parse_dt(self.v_starts.get())
            ends = parse_dt(self.v_ends.get())
            guests = int(self.v_guests.get())
            n = update_booking_times(self._selected_id, starts, ends, guests)
            messagebox.showinfo("Готово", f"Обновлено: {n}")
            self.load()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def on_set_status(self) -> None:
        """
        Обработчик нажатия кнопки "Изменить статус".
        Устанавливает новый статус для выбранного бронирования.
        """
        if self._selected_id is None:
            messagebox.showerror("Ошибка", "Сначала выберите бронирование")
            return
        try:
            st = (self.v_status.get() or "pending").strip()
            n = set_booking_status(self._selected_id, st)
            messagebox.showinfo("Готово", f"Статус изменён: {n}")
            self.load()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def on_cancel(self) -> None:
        """
        Обработчик нажатия кнопки "Отменить".
        Отменяет выбранное бронирование.
        """
        if self._selected_id is None:
            messagebox.showerror("Ошибка", "Сначала выберите бронирование")
            return
        try:
            n = cancel_booking(self._selected_id, None)
            messagebox.showinfo("Готово", f"Отменено: {n}")
            self.load()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))


if __name__ == "__main__":
    try:
        from backend import create_tables
        create_tables()
    except Exception:
        pass
    App().mainloop()