"""Control panel GUI for managing AI agents and their tasks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
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

        # data containers
        self.agents: list[AIAgent] = [AIAgent("Researcher-1"), AIAgent("Researcher-2")]
        self.tasks: list[Task] = []
        self._task_counter = 1

        top_frame = ttk.Frame(master)
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
        self.agent_combo = ttk.Combobox(
            task_frame,
            values=[a.name for a in self.agents],
            state="readonly",
            width=16,
        )
        self.agent_combo.current(0)
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
        self.agent_select = ttk.Combobox(
            agent_frame, values=[a.name for a in self.agents], state="readonly", width=14
        )
        self.agent_select.current(0)
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
        self.tree = ttk.Treeview(master, columns=columns, show="headings", height=8)
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
        status = ttk.Label(master, textvariable=self.status_var, relief="sunken", anchor="w")
        status.pack(fill="x", side="bottom")

        # populate with example data
        self.add_task("Write report", "Analyst", "Researcher-1", 1, auto=True)
        self.add_task("Conduct research", "Analyst", "Researcher-1", 1, auto=True)
        self.add_task("Design UI", "Analyst", "Researcher-1", 1, auto=True)
        self.add_task("Analyze data", "Researcher-2", "Researcher-2", 1, auto=True)

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
