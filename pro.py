import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont
from heapq import heappush, heappop
import time
import datetime

# ---------------- DESIGN TOKENS ---------------- #
BG = "#f8fafc"
CARD_BG = "#ffffff"
PRIMARY = "#2563eb"
SECONDARY = "#64748b"
ACCENT = "#22c55e"
DANGER = "#ef4444"
NAV_BG = "#1f2937"
NODE_BLUE = "#3b82f6"
EDGE_COLOR = "#cbd5f5"

TITLE_FONT = ("Segoe UI", 16, "bold")
SECTION_FONT = ("Segoe UI", 12, "bold")
BODY_FONT = ("Segoe UI", 10)

# ---------------- CREATE ROOT ---------------- #
root = tk.Tk()
root.title("AI Logistics Optimization Dashboard")
root.geometry("1280x780")
root.minsize(1120, 700)
root.configure(bg=BG)

# ---------------- WEIGHTS ---------------- #
w_fuel = tk.DoubleVar(root, value=1.0)
w_maint = tk.DoubleVar(root, value=1.0)
w_driver = tk.DoubleVar(root, value=1.0)
w_facility = tk.DoubleVar(root, value=1.0)

# ---------------- OPTIMIZER ---------------- #
class LogisticsOptimizer:
    def __init__(self):
        self.graph = {
            "Warehouse": {"Market": 4, "School": 6},
            "Market": {"Mall": 3, "Hospital": 5},
            "School": {"Library": 3},
            "Library": {"Park": 4},
            "Mall": {"Park": 2, "Office": 6},
            "Hospital": {"Office": 4},
            "Park": {"Garden": 3},
            "Office": {"Airport": 5},
            "Garden": {"Stadium": 4},
            "Stadium": {"Station": 3},
            "Station": {"Destination": 4},
            "Airport": {"Destination": 6},
            "Destination": {},
        }

        self.make_bidirectional()

        self.heuristic = {
            "Warehouse": 14,
            "Market": 12,
            "School": 11,
            "Library": 10,
            "Mall": 8,
            "Hospital": 7,
            "Park": 6,
            "Office": 5,
            "Garden": 4,
            "Stadium": 3,
            "Station": 2,
            "Airport": 2,
            "Destination": 0,
        }

    def make_bidirectional(self):
        for node in list(self.graph.keys()):
            for neighbor, cost in self.graph[node].items():
                if neighbor not in self.graph:
                    self.graph[neighbor] = {}
                if node not in self.graph[neighbor]:
                    self.graph[neighbor][node] = cost

    def a_star(self, start, goal):
        open_list = []
        heappush(open_list, (0, start))

        came_from = {}
        g_cost = {node: float("inf") for node in self.graph}
        g_cost[start] = 0

        while open_list:
            _, current = heappop(open_list)

            if current == goal:
                return self.reconstruct_path(came_from, start, goal), g_cost[goal]

            for neighbor, distance in self.graph[current].items():
                fuel = distance * 12
                maintenance = distance * 6
                driver = distance * 8
                facility = 30

                cost = (
                    w_fuel.get() * fuel
                    + w_maint.get() * maintenance
                    + w_driver.get() * driver
                    + w_facility.get() * facility
                )

                new_cost = g_cost[current] + cost

                if new_cost < g_cost[neighbor]:
                    came_from[neighbor] = current
                    g_cost[neighbor] = new_cost

                    f_cost = new_cost + self.heuristic[neighbor] * 10
                    heappush(open_list, (f_cost, neighbor))

        return None, None

    def reconstruct_path(self, came_from, start, goal):
        path = []
        node = goal

        while node != start:
            path.append(node)
            node = came_from[node]

        path.append(start)
        path.reverse()

        return path


# ---------------- RESOURCE ---------------- #
class ResourceManager:
    def __init__(self):
        self.vehicles = 5
        self.drivers = 5

    def allocate(self):
        if self.vehicles > 0 and self.drivers > 0:
            self.vehicles -= 1
            self.drivers -= 1
            return True

        return False


optimizer = LogisticsOptimizer()
resources = ResourceManager()
trip_history = []

# ---------------- POSITIONS ---------------- #
positions = {
    "Warehouse": (85, 180),
    "Market": (220, 100),
    "School": (220, 300),
    "Library": (380, 325),
    "Mall": (380, 100),
    "Hospital": (380, 180),
    "Park": (560, 145),
    "Office": (560, 55),
    "Garden": (715, 210),
    "Stadium": (835, 275),
    "Station": (955, 200),
    "Airport": (715, 45),
    "Destination": (1020, 180),
}

# ---------------- GLOBAL WIDGETS ---------------- #
canvas = None
route_label = None
vehicle_label = None
driver_label = None
fuel_val = None
maint_val = None
driver_val = None
facility_val = None
total_val = None
status_value_label = None

start_var = tk.StringVar(value="Warehouse")
goal_var = tk.StringVar(value="Destination")

start_combo = None
goal_combo = None

weight_value_labels = {}
truck = None


# ---------------- STYLES ---------------- #
def setup_styles():
    style = ttk.Style()
    style.theme_use("clam")

    style.configure(
        "App.TCombobox",
        fieldbackground="#ffffff",
        background="#ffffff",
        foreground="#0f172a",
        bordercolor="#cbd5e1",
        lightcolor="#cbd5e1",
        darkcolor="#cbd5e1",
        padding=6,
    )

    style.configure(
        "App.Horizontal.TScale",
        background=CARD_BG,
        troughcolor="#e2e8f0",
    )


# ---------------- UI HELPERS ---------------- #
def apply_button_hover(button, normal_bg, hover_bg):
    def on_enter(_event):
        button.configure(bg=hover_bg)

    def on_leave(_event):
        button.configure(bg=normal_bg)

    button.bind("<Enter>", on_enter)
    button.bind("<Leave>", on_leave)


def create_action_button(parent, text, command, bg=PRIMARY, active_bg="#1d4ed8"):
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        font=BODY_FONT,
        bg=bg,
        fg="white",
        activebackground=active_bg,
        activeforeground="white",
        relief="flat",
        bd=0,
        padx=14,
        pady=8,
        cursor="hand2",
    )
    apply_button_hover(btn, bg, active_bg)
    return btn


def create_card(parent, title):
    outer = tk.Frame(parent, bg="#e5e7eb")
    outer.pack(fill="both", expand=True, padx=0, pady=0)

    inner = tk.Frame(outer, bg=CARD_BG)
    inner.pack(fill="both", expand=True, padx=0, pady=0)

    if title:
        tk.Label(
            inner,
            text=title,
            font=SECTION_FONT,
            bg=CARD_BG,
            fg="#0f172a",
            anchor="w",
        ).pack(anchor="w", padx=0, pady=0)

    content = tk.Frame(inner, bg=CARD_BG)
    content.pack(fill="both", expand=True)

    return content


def set_status(text, color=SECONDARY):
    status_value_label.configure(text=text, fg=color)


# ---------------- NAVBAR ---------------- #
def create_navbar(parent):
    global status_value_label

    nav = tk.Frame(parent, bg=NAV_BG, height=58)
    nav.pack(fill="x")
    nav.pack_propagate(False)

    left = tk.Frame(nav, bg=NAV_BG)
    left.pack(side="left", fill="y", padx=18)

    title = tk.Label(
        left,
        text="AI Logistics Route Optimization",
        font=TITLE_FONT,
        bg=NAV_BG,
        fg="white",
    )
    title.pack(anchor="w", pady=13)

    right = tk.Frame(nav, bg=NAV_BG)
    right.pack(side="right", fill="y", padx=18)

    subtitle = tk.Label(
        right,
        text="System Status:",
        font=BODY_FONT,
        bg=NAV_BG,
        fg="#cbd5e1",
    )
    subtitle.pack(side="left", pady=16, padx=(0, 8))

    status_value_label = tk.Label(
        right,
        text="Ready",
        font=("Segoe UI", 10, "bold"),
        bg=NAV_BG,
        fg=ACCENT,
    )
    status_value_label.pack(side="left", pady=16)


# ---------------- GRAPH SECTION ---------------- #
def draw_graph():
    canvas.delete("all")
    node_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")

    drawn_edges = set()
    for node, neighbors in optimizer.graph.items():
        x1, y1 = positions[node]
        for neighbor in neighbors:
            edge_key = tuple(sorted((node, neighbor)))
            if edge_key in drawn_edges:
                continue
            drawn_edges.add(edge_key)
            x2, y2 = positions[neighbor]
            canvas.create_line(x1, y1, x2, y2, fill=EDGE_COLOR, width=1.5)

    for node, (x, y) in positions.items():
        text_w = node_font.measure(node)
        text_h = node_font.metrics("linespace")

        half_w = int(text_w / 2) + 14
        half_h = int(text_h / 2) + 8
        cap_r = half_h

        left = x - half_w
        right = x + half_w
        top = y - half_h
        bottom = y + half_h

        canvas.create_rectangle(
            left + cap_r,
            top,
            right - cap_r,
            bottom,
            fill=NODE_BLUE,
            outline="",
        )
        canvas.create_oval(
            left,
            top,
            left + 2 * cap_r,
            bottom,
            fill=NODE_BLUE,
            outline="",
        )
        canvas.create_oval(
            right - 2 * cap_r,
            top,
            right,
            bottom,
            fill=NODE_BLUE,
            outline="",
        )

        canvas.create_text(x, y, text=node, fill="white", font=node_font)


def draw_route(path):
    for i in range(len(path) - 1):
        x1, y1 = positions[path[i]]
        x2, y2 = positions[path[i + 1]]
        canvas.create_line(x1, y1, x2, y2, fill=DANGER, width=4, capstyle="round")


def create_graph_section(parent):
    global canvas

    graph_body = create_card(parent, "Network Graph")

    canvas = tk.Canvas(
        graph_body,
        width=1080,
        height=420,
        bg="#f8fafc",
        highlightthickness=0,
        bd=0,
    )
    canvas.pack(fill="both", expand=True)

    draw_graph()


def create_bottom_section(left_container):
    global route_label, vehicle_label, driver_label
    global fuel_val, maint_val, driver_val, facility_val, total_val

    bottom_frame = tk.Frame(left_container, bg=BG)
    bottom_frame.pack(fill="x", padx=0, pady=0)

    route_label = tk.Label(
        bottom_frame,
        text="Route: -",
        font=BODY_FONT,
        bg=BG,
        fg="#0f172a",
        anchor="w",
        justify="left",
    )
    route_label.pack(fill="x", padx=0, pady=0)

    cost_card = create_card(bottom_frame, "")
    cost_card.pack(fill="x", padx=0, pady=0)
    cost_card.grid_columnconfigure(0, weight=0)
    cost_card.grid_columnconfigure(1, weight=1)

    title_label = tk.Label(
        cost_card,
        text="COST BREAKDOWN",
        font=("Segoe UI", 11, "bold"),
        bg="white",
        fg="#0f172a",
        anchor="nw",
        justify="left",
    )
    title_label.grid(row=0, column=0, rowspan=6, sticky="nw", padx=0, pady=0)

    fuel_val = tk.Label(cost_card, text="Fuel: 0 × 1.0 = ₹0", anchor="w", bg="white", fg="#334155")
    maint_val = tk.Label(cost_card, text="Maintenance: 0 × 1.0 = ₹0", anchor="w", bg="white", fg="#334155")
    driver_val = tk.Label(cost_card, text="Driver: 0 × 1.0 = ₹0", anchor="w", bg="white", fg="#334155")
    facility_val = tk.Label(cost_card, text="Facility: 0 × 1.0 = ₹0", anchor="w", bg="white", fg="#334155")

    fuel_val.grid(row=0, column=1, sticky="w", padx=5, pady=0)
    maint_val.grid(row=1, column=1, sticky="w", padx=5, pady=0)
    driver_val.grid(row=2, column=1, sticky="w", padx=5, pady=0)
    facility_val.grid(row=3, column=1, sticky="w", padx=5, pady=0)

    sep = tk.Label(cost_card, text="-----------------------------", bg="white", fg="#334155")
    sep.grid(row=4, column=1, sticky="w", padx=5, pady=0)

    total_val = tk.Label(
        cost_card,
        text="TOTAL: ₹0",
        font=("Segoe UI", 10, "bold"),
        bg="white",
        fg="#0f172a",
    )
    total_val.grid(row=5, column=1, sticky="w", padx=5, pady=0)

    stats_card = create_card(bottom_frame, "Stats")

    vehicle_label = tk.Label(
        stats_card,
        text="Vehicles Left: 5",
        font=BODY_FONT,
        bg=CARD_BG,
        fg="#0f172a",
    )
    vehicle_label.pack(anchor="w", padx=10)

    driver_label = tk.Label(
        stats_card,
        text="Drivers Left: 5",
        font=BODY_FONT,
        bg=CARD_BG,
        fg="#0f172a",
    )
    driver_label.pack(anchor="w", padx=10)


# ---------------- HISTORY ---------------- #
def show_history():
    win = tk.Toplevel(root)
    win.title("Trip History")
    win.geometry("620x460")
    win.configure(bg=BG)

    container = tk.Frame(win, bg=BG)
    container.pack(fill="both", expand=True, padx=16, pady=16)

    body = create_card(container, "Trip History")

    text = tk.Text(
        body,
        font=BODY_FONT,
        bg="#f8fafc",
        fg="#0f172a",
        relief="flat",
        highlightthickness=0,
        wrap="word",
        padx=10,
        pady=10,
    )
    text.pack(fill="both", expand=True)

    if not trip_history:
        text.insert(tk.END, "No trips recorded yet.")
    else:
        for trip in trip_history:
            text.insert(tk.END, trip + "\n\n")

    text.config(state="disabled")


# ---------------- TRUCK ---------------- #
def animate_truck(path):
    global truck

    if truck:
        canvas.delete(truck)
        truck = None

    start_x, start_y = positions[path[0]]
    truck = canvas.create_rectangle(
        start_x - 6,
        start_y - 6,
        start_x + 6,
        start_y + 6,
        fill=DANGER,
        outline="#991b1b",
    )

    for i in range(len(path) - 1):
        x1, y1 = positions[path[i]]
        x2, y2 = positions[path[i + 1]]

        steps = 28
        for t in range(1, steps + 1):
            xt = x1 + (x2 - x1) * t / steps
            yt = y1 + (y2 - y1) * t / steps
            canvas.coords(truck, xt - 6, yt - 6, xt + 6, yt + 6)
            root.update_idletasks()
            root.update()
            time.sleep(0.014)


# ---------------- MAIN ---------------- #
def run_optimizer():
    if resources.vehicles <= 0 or resources.drivers <= 0:
        set_status("No Resources", DANGER)
        route_label.config(text="Route: No resources available", fg=DANGER)
        return

    start = start_var.get()
    goal = goal_var.get()

    draw_graph()

    path, _ = optimizer.a_star(start, goal)

    if not path:
        set_status("No Route", DANGER)
        route_label.config(text="Route: No route found", fg=DANGER)
        return

    draw_route(path)

    route_label.config(text="Route: " + " -> ".join(path), fg="#0f172a")

    resources.allocate()

    vehicle_label.config(text=f"Vehicles Left: {resources.vehicles}")
    driver_label.config(text=f"Drivers Left: {resources.drivers}")

    total_fuel = total_maint = total_driver = total_facility = 0

    for i in range(len(path) - 1):
        d = optimizer.graph[path[i]][path[i + 1]]
        total_fuel += d * 12
        total_maint += d * 6
        total_driver += d * 8
        total_facility += 30

    weighted_total = (
        w_fuel.get() * total_fuel
        + w_maint.get() * total_maint
        + w_driver.get() * total_driver
        + w_facility.get() * total_facility
    )

    fuel_val.config(text=f"Fuel: {total_fuel} × {w_fuel.get():.1f} = ₹{int(w_fuel.get()*total_fuel)}")
    maint_val.config(text=f"Maintenance: {total_maint} × {w_maint.get():.1f} = ₹{int(w_maint.get()*total_maint)}")
    driver_val.config(text=f"Driver: {total_driver} × {w_driver.get():.1f} = ₹{int(w_driver.get()*total_driver)}")
    facility_val.config(
        text=f"Facility: {total_facility} × {w_facility.get():.1f} = ₹{int(w_facility.get()*total_facility)}"
    )
    total_val.config(text=f"TOTAL: ₹{int(weighted_total)}")

    trip_history.append(
        f"{datetime.datetime.now()} | {' -> '.join(path)} | INR {int(weighted_total)}"
    )

    set_status("Route Found", ACCENT)
    animate_truck(path)


# ---------------- SIDEBAR ---------------- #
def add_weight_row(parent, label_text, variable):
    row = tk.Frame(parent, bg=CARD_BG)
    row.pack(fill="x", pady=(2, 10))

    top = tk.Frame(row, bg=CARD_BG)
    top.pack(fill="x")

    tk.Label(top, text=label_text, font=BODY_FONT, bg=CARD_BG, fg="#334155").pack(
        side="left"
    )

    val_label = tk.Label(
        top,
        text=f"{variable.get():.1f}",
        font=BODY_FONT,
        bg=CARD_BG,
        fg=SECONDARY,
    )
    val_label.pack(side="right")

    def on_slide(value):
        val_label.config(text=f"{float(value):.1f}")

    slider = ttk.Scale(
        row,
        from_=0,
        to=1,
        variable=variable,
        command=on_slide,
        style="App.Horizontal.TScale",
    )
    slider.pack(fill="x", pady=(6, 0))

    weight_value_labels[label_text] = val_label


def create_sidebar(parent):
    global start_combo, goal_combo

    weights_body = create_card(parent, "Weights")

    add_weight_row(weights_body, "Fuel", w_fuel)
    add_weight_row(weights_body, "Maintenance", w_maint)
    add_weight_row(weights_body, "Driver", w_driver)
    add_weight_row(weights_body, "Facility", w_facility)

    controls_body = create_card(parent, "Controls")

    nodes = list(positions.keys())

    tk.Label(controls_body, text="Start Node", font=BODY_FONT, bg=CARD_BG, fg=SECONDARY).pack(
        anchor="w"
    )
    start_combo = ttk.Combobox(
        controls_body,
        textvariable=start_var,
        values=nodes,
        state="readonly",
        style="App.TCombobox",
    )
    start_combo.pack(fill="x", pady=(4, 10))

    tk.Label(controls_body, text="Destination", font=BODY_FONT, bg=CARD_BG, fg=SECONDARY).pack(
        anchor="w"
    )
    goal_combo = ttk.Combobox(
        controls_body,
        textvariable=goal_var,
        values=nodes,
        state="readonly",
        style="App.TCombobox",
    )
    goal_combo.pack(fill="x", pady=(4, 12))

    find_btn = create_action_button(controls_body, "Find Route", run_optimizer, bg=PRIMARY)
    find_btn.pack(fill="x", pady=(0, 8))

    history_btn = create_action_button(
        controls_body,
        "History",
        show_history,
        bg="#0ea5e9",
        active_bg="#0284c7",
    )
    history_btn.pack(fill="x")


# ---------------- APP BUILD ---------------- #
def build_ui():
    setup_styles()
    create_navbar(root)

    main_container = tk.Frame(root, bg=BG)
    main_container.pack(fill="both", expand=True, padx=18, pady=18)

    left_container = tk.Frame(main_container, bg=BG)
    left_container.pack(side="left", fill="both", expand=True, padx=0, pady=0)

    right_sidebar = tk.Frame(main_container, bg=BG, width=360)
    right_sidebar.pack(side="right", fill="y")
    right_sidebar.pack_propagate(False)

    create_graph_section(left_container)
    create_bottom_section(left_container)
    create_sidebar(right_sidebar)


build_ui()
root.mainloop()

