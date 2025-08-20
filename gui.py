import tkinter as tk
from tkinter import messagebox
from agent import AIAgent


class AgentGUI:
    """Tkinter-based GUI to manage a list of AI agents."""

    def __init__(self, master: tk.Tk):
        self.master = master
        self.master.title("AI Agent Manager")
        self.agents: list[AIAgent] = []

        self.name_entry = tk.Entry(master)
        self.name_entry.pack(padx=5, pady=5)

        add_button = tk.Button(master, text="Add Agent", command=self.add_agent)
        add_button.pack(padx=5, pady=5)

        self.listbox = tk.Listbox(master, width=40)
        self.listbox.pack(padx=5, pady=5)

        btn_frame = tk.Frame(master)
        btn_frame.pack(padx=5, pady=5)

        start_button = tk.Button(btn_frame, text="Start", command=self.start_agent)
        start_button.grid(row=0, column=0, padx=2)

        stop_button = tk.Button(btn_frame, text="Stop", command=self.stop_agent)
        stop_button.grid(row=0, column=1, padx=2)

        remove_button = tk.Button(btn_frame, text="Remove", command=self.remove_agent)
        remove_button.grid(row=0, column=2, padx=2)

    def add_agent(self) -> None:
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Input Error", "Agent name cannot be empty")
            return
        agent = AIAgent(name)
        self.agents.append(agent)
        self.refresh_list()
        self.name_entry.delete(0, tk.END)

    def get_selected_agent(self) -> AIAgent | None:
        index = self.listbox.curselection()
        if not index:
            messagebox.showwarning("Selection Error", "No agent selected")
            return None
        return self.agents[index[0]]

    def start_agent(self) -> None:
        agent = self.get_selected_agent()
        if agent is not None:
            agent.start()
            self.refresh_list()

    def stop_agent(self) -> None:
        agent = self.get_selected_agent()
        if agent is not None:
            agent.stop()
            self.refresh_list()

    def remove_agent(self) -> None:
        index = self.listbox.curselection()
        if not index:
            messagebox.showwarning("Selection Error", "No agent selected")
            return
        self.agents.pop(index[0])
        self.refresh_list()

    def refresh_list(self) -> None:
        self.listbox.delete(0, tk.END)
        for agent in self.agents:
            self.listbox.insert(tk.END, f"{agent.name} ({agent.status})")


def main() -> None:
    root = tk.Tk()
    AgentGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
