"""Control panel GUI for managing AI agents and their tasks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import json
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


class ControlPanel:
    """Tkinter-based GUI emulating the provided mockup."""

    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self.master.title("Agents – Control Panel")

        self.load_config()

        # data containers
        self.agents: list[AIAgent] = [AIAgent("Researcher-1"), AIAgent("Researcher-2")]
        self.tasks: list[Task] = []
        self._task_counter = 1

        self.notebook = ttk.Notebook(master)
        self.notebook.pack(fill="both", expand=True)

        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Панель")
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

        ttk.Label(task_frame, text="Роль").grid(row=0, column=2, sticky="w")
        self.role_entry = ttk.Entry(task_frame, width=15)
        self.role_entry.grid(row=0, column=3, padx=5, pady=2)

        ttk.Label(task_frame, text="Агент").grid(row=1, column=0, sticky="w")
        self.agent_combo = ttk.Combobox(task_frame, state="readonly", width=16)
        self.agent_combo.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(task_frame, text="Приоритет").grid(row=1, column=2, sticky="w")
        self.prio_spin = ttk.Spinbox(task_frame, from_=1, to=10, width=5)
        self.prio_spin.set(1)
        self.prio_spin.grid(row=1, column=3, padx=5, pady=2)

        add_task = ttk.Button(task_frame, text="Добавить задачу", command=self.add_task)
        add_task.grid(row=2, column=0, columnspan=4, pady=5)

        # ----- agent control -----
        agent_frame = ttk.LabelFrame(top_frame, text="Agent")
        agent_frame.pack(side="right", fill="y")

        ttk.Label(agent_frame, text="Имя").grid(row=0, column=0, sticky="w")
        self.agent_select = ttk.Combobox(agent_frame, state="readonly", width=14)
        self.agent_select.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(agent_frame, text="Count").grid(row=1, column=0, sticky="w")
        self.count_spin = ttk.Spinbox(agent_frame, from_=1, to=5, width=5)
        self.count_spin.set(1)
        self.count_spin.grid(row=1, column=1, padx=5, pady=2)

        start_btn = ttk.Button(agent_frame, text="Старт", command=self.start_agent)
        start_btn.grid(row=2, column=0, padx=5, pady=(5, 0), sticky="ew")

        stop_btn = ttk.Button(agent_frame, text="Стоп выбранный", command=self.stop_agent)
        stop_btn.grid(row=2, column=1, padx=5, pady=(5, 0), sticky="ew")

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
            self.tree.heading(cid, text=text)
            self.tree.column(cid, width=80, anchor="center")
        self.tree.column("title", width=150)
        self.tree.column("role", width=120)
        self.tree.column("agent", width=120)
        self.tree.column("updated", width=110)
        self.tree.column("start", width=80)

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
        ttk.Button(manage_frame, text="Добавить", command=self.create_agent).grid(row=0, column=2, padx=5)

        ttk.Button(manage_frame, text="Удалить", command=self.delete_agent).grid(row=1, column=2, padx=5, pady=2)

        ttk.Label(manage_frame, text="Промт").grid(row=2, column=0, sticky="nw")
        self.prompt_text = tk.Text(manage_frame, width=40, height=5)
        self.prompt_text.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        self.mode_var = tk.StringVar(value="local")
        mode_frame = ttk.Frame(manage_frame)
        mode_frame.grid(row=3, column=1, columnspan=2, pady=5, sticky="w")
        ttk.Radiobutton(mode_frame, text="Локальный", variable=self.mode_var, value="local").pack(side="left")
        ttk.Radiobutton(mode_frame, text="Облачный", variable=self.mode_var, value="cloud").pack(side="left")

        ttk.Button(manage_frame, text="Сохранить", command=self.save_agent_settings).grid(row=4, column=1, pady=5, sticky="w")

    def _build_settings_tab(self) -> None:
        frame = ttk.Frame(self.settings_tab)
        frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(frame, text="OpenAI API Key").grid(row=0, column=0, sticky="w")
        self.api_key_var = tk.StringVar(value=self.config.get("openai_key", ""))
        self.api_key_entry = ttk.Entry(frame, textvariable=self.api_key_var, width=40, show="*")
        self.api_key_entry.grid(row=0, column=1, padx=5, pady=2, columnspan=2, sticky="w")
        ttk.Button(frame, text="Удалить ключ", command=self.delete_key).grid(row=0, column=3, padx=5)

        ttk.Label(frame, text="Ollama порт").grid(row=1, column=0, sticky="w")
        self.ollama_port_var = tk.StringVar(value=str(self.config.get("ollama_port", "")))
        ttk.Entry(frame, textvariable=self.ollama_port_var, width=10).grid(row=1, column=1, padx=5, pady=2, sticky="w")

        ttk.Button(frame, text="Сохранить", command=self.save_settings).grid(row=2, column=1, pady=5, sticky="w")

    # ------------------------------------------------------------------
    # utility methods
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
        if not name:
            return
        self.agents.append(AIAgent(name))
        self.new_agent_entry.delete(0, tk.END)
        self._refresh_agent_lists()
        self.status_var.set(f"Агент {name} создан")

    def delete_agent(self) -> None:
        selection = self.agent_listbox.curselection()
        if not selection:
            return
        name = self.agent_listbox.get(selection[0])
        agent = self._find_agent(name)
        if agent:
            self.agents.remove(agent)
            self.tasks = [t for t in self.tasks if t.agent != name]
            self.refresh_table()
        self._refresh_agent_lists()
        self.status_var.set(f"Агент {name} удален")

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

    def save_agent_settings(self) -> None:
        selection = self.agent_listbox.curselection()
        if not selection:
            return
        name = self.agent_listbox.get(selection[0])
        agent = self._find_agent(name)
        if agent:
            agent.prompt = self.prompt_text.get("1.0", tk.END).strip()
            agent.mode = self.mode_var.get()
            self.status_var.set(f"Настройки агента {name} сохранены")

    def save_settings(self) -> None:
        self.config["openai_key"] = self.api_key_var.get().strip()
        self.config["ollama_port"] = self.ollama_port_var.get().strip()
        self.save_config()
        self.status_var.set("Настройки сохранены")

    def delete_key(self) -> None:
        self.api_key_var.set("")
        self.config["openai_key"] = ""
        self.save_config()
        self.status_var.set("Ключ удален")

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
            self.status_var.set(f"Агент {name} остановлен")

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
