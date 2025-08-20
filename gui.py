"""Control panel GUI for managing AI agents and their tasks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import json
import re
import tkinter as tk
from tkinter import ttk, messagebox

from agent import AIAgent


@dataclass
class Task:
    """Simple representation of a task assigned to an agent."""

    id: int
    title: str
    role: str
    agent: str
    priority: int
    cpu: float = 0.0
    ram: int = 0
    status: str = "Pending"
    created: datetime = datetime.now()
    updated: datetime = datetime.now()


class ToolTip:
    """Simple tooltip shown after a short delay."""

    def __init__(self, widget: tk.Widget, text: str, delay: int = 3000) -> None:
        self.widget = widget
        self.text = text
        self.delay = delay
        self._id: str | None = None
        self.tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._unschedule)

    def _schedule(self, _event: tk.Event) -> None:
        self._unschedule()
        self._id = self.widget.after(self.delay, self._show)

    def _unschedule(self, _event: tk.Event | None = None) -> None:
        if self._id:
            self.widget.after_cancel(self._id)
            self._id = None
        if self.tip:
            self.tip.destroy()
            self.tip = None

    def _show(self) -> None:
        if self.tip:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 10
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.geometry(f"+{x}+{y}")
        label = ttk.Label(self.tip, text=self.text, relief="solid", borderwidth=1, background="#ffffe0")
        label.pack(ipadx=4, ipady=2)


class ControlPanel:
    """Tkinter-based GUI emulating the provided mockup."""

    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self.master.title("Agents – Control Panel")

        self.load_config()
        self.agents: list[AIAgent] = []
        self.load_agents()

        # data containers
        self.tasks: list[Task] = []
        self._task_counter = 1
        self._sort_dirs: dict[str, bool] = {}

        self.notebook = ttk.Notebook(master)
        self.notebook.pack(fill="both", expand=True)

        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Список задач")
        self._build_main_tab()

        self.agents_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.agents_tab, text="Агенты")
        self._build_agents_tab()

        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_tab, text="Настройки")
        self._build_settings_tab()

        self._refresh_agent_lists()

        # populate with example data
        self.add_task("Write report", "Analyst", "Researcher-1", 1, auto=True)
        self.add_task("Conduct research", "Analyst", "Researcher-1", 1, auto=True)
        self.add_task("Design UI", "Analyst", "Researcher-1", 1, auto=True)
        self.add_task("Analyze data", "Researcher-2", "Researcher-2", 1, auto=True)

    def _build_main_tab(self) -> None:
        top_frame = ttk.Frame(self.main_tab)
        top_frame.pack(fill="x", padx=10, pady=10)

        # ----- task creation -----
        task_frame = ttk.LabelFrame(top_frame, text="Tasks")
        task_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ttk.Label(task_frame, text="Заголовок").grid(row=0, column=0, sticky="w")
        self.title_entry = ttk.Entry(task_frame, width=18)
        self.title_entry.grid(row=0, column=1, padx=5, pady=2)
        ToolTip(self.title_entry, "Введите заголовок задачи")

        ttk.Label(task_frame, text="Роль").grid(row=0, column=2, sticky="w")
        self.role_entry = ttk.Entry(task_frame, width=15)
        self.role_entry.grid(row=0, column=3, padx=5, pady=2)
        ToolTip(self.role_entry, "Роль для задачи")

        ttk.Label(task_frame, text="Агент").grid(row=1, column=0, sticky="w")
        self.agent_combo = ttk.Combobox(task_frame, state="readonly", width=16)
        self.agent_combo.grid(row=1, column=1, padx=5, pady=2)
        ToolTip(self.agent_combo, "Выберите агента")

        ttk.Label(task_frame, text="Приоритет").grid(row=1, column=2, sticky="w")
        self.prio_spin = ttk.Spinbox(task_frame, from_=1, to=10, width=5)
        self.prio_spin.set(1)
        self.prio_spin.grid(row=1, column=3, padx=5, pady=2)
        ToolTip(self.prio_spin, "Приоритет задачи")

        add_task = ttk.Button(task_frame, text="Добавить задачу", command=self.add_task)
        add_task.grid(row=2, column=0, columnspan=4, pady=5)
        ToolTip(add_task, "Добавить задачу в список")

        # ----- agent control -----
        agent_frame = ttk.LabelFrame(top_frame, text="Agent")
        agent_frame.pack(side="right", fill="y")

        ttk.Label(agent_frame, text="Имя").grid(row=0, column=0, sticky="w")
        self.agent_select = ttk.Combobox(agent_frame, state="readonly", width=14)
        self.agent_select.grid(row=0, column=1, padx=5, pady=2)
        ToolTip(self.agent_select, "Выберите агента")

        start_btn = ttk.Button(agent_frame, text="Старт", command=self.start_agent)
        start_btn.grid(row=1, column=0, padx=5, pady=(5, 0), sticky="ew")
        ToolTip(start_btn, "Запустить агента")

        stop_btn = ttk.Button(agent_frame, text="Стоп выбранный", command=self.stop_agent)
        stop_btn.grid(row=1, column=1, padx=5, pady=(5, 0), sticky="ew")
        ToolTip(stop_btn, "Остановить выбранного агента")

        # ----- task table -----
        columns = (
            "id",
            "title",
            "role",
            "agent",
            "cpu",
            "ram",
            "status",
            "updated",
            "start",
        )
        self.tree = ttk.Treeview(self.main_tab, columns=columns, show="headings", height=8)
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        headings = {
            "id": "ID",
            "title": "Заголовок",
            "role": "Роль",
            "agent": "Агент",
            "cpu": "CPU%",
            "ram": "RAM MB",
            "status": "Статус",
            "updated": "Обновлено",
            "start": "Старт",
        }
        for cid, text in headings.items():
            self.tree.heading(cid, text=text, command=lambda c=cid: self.sort_tasks(c))
            self.tree.column(cid, width=80, anchor="center")
        self.tree.column("title", width=150)
        self.tree.column("role", width=120)
        self.tree.column("agent", width=120)
        self.tree.column("updated", width=110)
        self.tree.column("start", width=80)

        del_btn = ttk.Button(self.main_tab, text="Удалить выбранное", command=self.delete_task)
        del_btn.pack(padx=10, pady=(0, 10), anchor="e")
        ToolTip(del_btn, "Удалить выбранные задачи")

        # ----- status bar -----
        self.status_var = tk.StringVar(value="Готово")
        status = ttk.Label(self.main_tab, textvariable=self.status_var, relief="sunken", anchor="w")
        status.pack(fill="x", side="bottom")

    def _build_agents_tab(self) -> None:
        list_frame = ttk.Frame(self.agents_tab)
        list_frame.pack(side="left", fill="y", padx=10, pady=10)

        self.agent_listbox = tk.Listbox(list_frame, height=8)
        self.agent_listbox.pack(side="left", fill="y")
        self.agent_listbox.bind("<<ListboxSelect>>", self.on_agent_select)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.agent_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.agent_listbox.config(yscrollcommand=scrollbar.set)

        manage_frame = ttk.Frame(self.agents_tab)
        manage_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        ttk.Label(manage_frame, text="Имя").grid(row=0, column=0, sticky="w")
        self.new_agent_entry = ttk.Entry(manage_frame, width=20)
        self.new_agent_entry.grid(row=0, column=1, padx=5, pady=2)
        ToolTip(self.new_agent_entry, "Имя нового агента")
        ttk.Button(manage_frame, text="Добавить", command=self.create_agent).grid(row=0, column=2, padx=5)

        ttk.Label(manage_frame, text="Роль").grid(row=1, column=0, sticky="w")
        self.agent_role_entry = ttk.Entry(manage_frame, width=20)
        self.agent_role_entry.grid(row=1, column=1, padx=5, pady=2)
        ToolTip(self.agent_role_entry, "Роль агента")
        ttk.Button(manage_frame, text="Удалить", command=self.delete_agent).grid(row=1, column=2, padx=5, pady=2)

        ttk.Label(manage_frame, text="Промт").grid(row=2, column=0, sticky="nw")
        self.prompt_text = tk.Text(manage_frame, width=40, height=5)
        self.prompt_text.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        ToolTip(self.prompt_text, "Промт для агента")

        self.mode_var = tk.StringVar(value="local")
        mode_frame = ttk.Frame(manage_frame)
        mode_frame.grid(row=3, column=1, columnspan=2, pady=5, sticky="w")
        ttk.Radiobutton(mode_frame, text="Локальный", variable=self.mode_var, value="local").pack(side="left")
        ttk.Radiobutton(mode_frame, text="Облачный", variable=self.mode_var, value="cloud").pack(side="left")

        save_btn = ttk.Button(manage_frame, text="Сохранить", command=self.save_agent_settings)
        save_btn.grid(row=4, column=1, pady=5, sticky="w")
        ToolTip(save_btn, "Сохранить настройки агента")

    def _build_settings_tab(self) -> None:
        frame = ttk.Frame(self.settings_tab)
        frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(frame, text="OpenAI API Key").grid(row=0, column=0, sticky="w")
        self.api_key_var = tk.StringVar(value=self.config.get("openai_key", ""))
        self.api_key_entry = ttk.Entry(frame, textvariable=self.api_key_var, width=40, show="*")
        self.api_key_entry.grid(row=0, column=1, padx=5, pady=2, sticky="w")
        ToolTip(self.api_key_entry, "OpenAI API ключ")
        self.show_key = False
        self.show_btn = ttk.Button(frame, text="Показать", command=self.toggle_key_visibility)
        self.show_btn.grid(row=0, column=2, padx=5)
        paste_btn = ttk.Button(frame, text="Вставить", command=self.paste_key)
        paste_btn.grid(row=0, column=3, padx=5)
        ToolTip(paste_btn, "Вставить ключ из буфера")
        ttk.Button(frame, text="Удалить ключ", command=self.delete_key).grid(row=0, column=4, padx=5)

        ttk.Label(frame, text="Ollama порт").grid(row=1, column=0, sticky="w")
        self.ollama_port_var = tk.StringVar(value=str(self.config.get("ollama_port", "")))
        ttk.Entry(frame, textvariable=self.ollama_port_var, width=10).grid(row=1, column=1, padx=5, pady=2, sticky="w")

        ttk.Button(frame, text="Сохранить", command=self.save_settings).grid(row=2, column=1, pady=5, sticky="w")

    # ------------------------------------------------------------------
    # utility methods
    def _valid_api_key(self, key: str) -> bool:
        """Validate OpenAI API key format."""
        return bool(re.fullmatch(r"sk-[A-Za-z0-9]{32,}", key))

    def _valid_port(self, port: str) -> bool:
        """Validate that the string is a valid TCP port."""
        return port.isdigit() and 1 <= int(port) <= 65535

    def _relative(self, dt: datetime) -> str:
        diff = datetime.now() - dt
        if diff < timedelta(minutes=1):
            return "Just now"
        if diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() // 60)
            return f"{minutes} min ago"
        return dt.strftime("%H:%M")

    def _find_agent(self, name: str) -> AIAgent | None:
        for agent in self.agents:
            if agent.name == name:
                return agent
        return None

    def _refresh_agent_lists(self) -> None:
        names = [a.name for a in self.agents]
        self.agent_combo["values"] = names
        self.agent_select["values"] = names
        if names:
            self.agent_combo.current(0)
            self.agent_select.current(0)
        self.agent_listbox.delete(0, tk.END)
        for name in names:
            self.agent_listbox.insert(tk.END, name)

    def create_agent(self) -> None:
        name = self.new_agent_entry.get().strip()
        role = self.agent_role_entry.get().strip()
        if not name:
            return
        self.agents.append(AIAgent(name, role=role))
        self.new_agent_entry.delete(0, tk.END)
        self.agent_role_entry.delete(0, tk.END)
        self._refresh_agent_lists()
        self.save_agents()
        self.status_var.set(f"Агент {name} создан")

    def delete_agent(self) -> None:
        selection = self.agent_listbox.curselection()
        if not selection:
            return
        name = self.agent_listbox.get(selection[0])
        if not messagebox.askyesno("Удалить агента", f"Удалить агента {name}?"):
            return
        agent = self._find_agent(name)
        if agent:
            self.agents.remove(agent)
            self.tasks = [t for t in self.tasks if t.agent != name]
            self.refresh_table()
        self._refresh_agent_lists()
        self.save_agents()
        self.status_var.set(f"Агент {name} удален")
        messagebox.showinfo("Агенты", f"Агент {name} удален")

    def on_agent_select(self, event: tk.Event) -> None:
        selection = self.agent_listbox.curselection()
        if not selection:
            return
        name = self.agent_listbox.get(selection[0])
        agent = self._find_agent(name)
        if agent:
            self.prompt_text.delete("1.0", tk.END)
            self.prompt_text.insert("1.0", agent.prompt)
            self.mode_var.set(agent.mode)
            self.agent_role_entry.delete(0, tk.END)
            self.agent_role_entry.insert(0, agent.role)

    def save_agent_settings(self) -> None:
        selection = self.agent_listbox.curselection()
        if not selection:
            messagebox.showwarning("Агенты", "Выберите агента")
            return
        name = self.agent_listbox.get(selection[0])
        agent = self._find_agent(name)
        if agent:
            prompt = self.prompt_text.get("1.0", tk.END).strip()
            if not prompt:
                messagebox.showerror("Агенты", "Промт не может быть пустым")
                return
            if not messagebox.askyesno("Сохранить агента", f"Сохранить изменения для {name}?"):
                return
            agent.prompt = prompt
            agent.role = self.agent_role_entry.get().strip()
            agent.mode = self.mode_var.get()
            self.save_agents()
            self._refresh_agent_lists()
            self.status_var.set(f"Настройки агента {name} сохранены")
            messagebox.showinfo("Агенты", f"Настройки агента {name} сохранены")

    def save_settings(self) -> None:
        if not messagebox.askyesno("Сохранить настройки", "Сохранить ключ и порт?"):
            return
        key = self.api_key_var.get().strip()
        port = self.ollama_port_var.get().strip()

        if key and not self._valid_api_key(key):
            messagebox.showerror("Настройки", "Некорректный OpenAI API ключ")
            return

        if not self._valid_port(port):
            messagebox.showerror("Настройки", "Некорректный порт Ollama")
            return

        self.config["openai_key"] = key
        self.config["ollama_port"] = port
        self.save_config()
        self.status_var.set("Настройки сохранены")
        messagebox.showinfo("Настройки", "Настройки сохранены")

    def delete_key(self) -> None:
        if not messagebox.askyesno("Удалить ключ", "Удалить API ключ?"):
            return
        self.api_key_var.set("")
        self.config["openai_key"] = ""
        self.save_config()
        self.status_var.set("Ключ удален")
        messagebox.showinfo("Настройки", "Ключ удален")

    def paste_key(self) -> None:
        try:
            key = self.master.clipboard_get().strip()
        except tk.TclError:
            messagebox.showerror("Настройки", "Буфер обмена пуст")
            return
        self.api_key_var.set(key)

    def toggle_key_visibility(self) -> None:
        self.show_key = not self.show_key
        if self.show_key:
            self.api_key_entry.config(show="")
            self.show_btn.config(text="Скрыть")
        else:
            self.api_key_entry.config(show="*")
            self.show_btn.config(text="Показать")

    def load_config(self) -> None:
        path = Path("config.json")
        if path.exists():
            try:
                self.config = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                self.config = {"openai_key": "", "ollama_port": "11434"}
        else:
            self.config = {"openai_key": "", "ollama_port": "11434"}

    def save_config(self) -> None:
        path = Path("config.json")
        path.write_text(json.dumps(self.config, indent=2), encoding="utf-8")

    def load_agents(self) -> None:
        path = Path("agents.json")
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self.agents = [AIAgent(**item) for item in data]
                return
            except Exception:
                pass
        self.agents = [AIAgent("Researcher-1"), AIAgent("Researcher-2")]
        self.save_agents()

    def save_agents(self) -> None:
        path = Path("agents.json")
        data = [agent.__dict__ for agent in self.agents]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # actions
    def add_task(
        self,
        title: str | None = None,
        role: str | None = None,
        agent_name: str | None = None,
        prio: int | None = None,
        *,
        auto: bool = False,
    ) -> None:
        """Add a task to the table."""

        if not auto:
            title = self.title_entry.get().strip()
            role = self.role_entry.get().strip()
            agent_name = self.agent_combo.get()
            prio = int(self.prio_spin.get())
            if not title or not role:
                messagebox.showwarning("Ошибка ввода", "Заполните заголовок и роль")
                return

        task = Task(
            id=self._task_counter,
            title=title or "",
            role=role or "",
            agent=agent_name or "",
            priority=prio or 1,
        )
        self.tasks.append(task)
        self._task_counter += 1
        self.refresh_table()
        if not auto:
            self.title_entry.delete(0, tk.END)
            self.role_entry.delete(0, tk.END)
            self.status_var.set(f"Задача '{task.title}' добавлена")

    def start_agent(self) -> None:
        name = self.agent_select.get()
        agent = self._find_agent(name)
        if agent:
            agent.start()
            for task in self.tasks:
                if task.agent == name and task.status == "Pending":
                    task.status = "In Progress"
                    task.updated = datetime.now()
            self.refresh_table()
            self.save_agents()
            self.status_var.set(f"Агент {name} запущен")

    def stop_agent(self) -> None:
        name = self.agent_select.get()
        agent = self._find_agent(name)
        if agent:
            agent.stop()
            for task in self.tasks:
                if task.agent == name and task.status == "In Progress":
                    task.status = "Stopped"
                    task.updated = datetime.now()
            self.refresh_table()
            self.save_agents()
            self.status_var.set(f"Агент {name} остановлен")

    def delete_task(self) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        if not messagebox.askyesno("Удалить задачу", "Удалить выбранные задачи?"):
            return
        ids = {int(self.tree.item(item, "values")[0]) for item in selected}
        self.tasks = [t for t in self.tasks if t.id not in ids]
        self.refresh_table()
        self.status_var.set("Задача удалена")

    def sort_tasks(self, column: str) -> None:
        mapping = {
            "id": "id",
            "title": "title",
            "role": "role",
            "agent": "agent",
            "cpu": "cpu",
            "ram": "ram",
            "status": "status",
            "updated": "updated",
            "start": "created",
        }
        attr = mapping[column]
        reverse = self._sort_dirs.get(column, False)
        self.tasks.sort(key=lambda t: getattr(t, attr), reverse=reverse)
        self._sort_dirs[column] = not reverse
        self.refresh_table()

    def refresh_table(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for task in self.tasks:
            self.tree.insert(
                "",
                "end",
                values=(
                    task.id,
                    task.title,
                    task.role,
                    task.agent,
                    f"{task.cpu:.1f}",
                    task.ram,
                    task.status,
                    self._relative(task.updated),
                    task.created.strftime("%H:%M"),
                ),
            )


def main() -> None:
    root = tk.Tk()
    ControlPanel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
