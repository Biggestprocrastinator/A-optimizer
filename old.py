from heapq import heappush, heappop
import time
import datetime


class SimpleVar:
    def __init__(self, value=1.0):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


# Default non-GUI weights; replaced by tkinter DoubleVar in GUI mode.
w_fuel = SimpleVar(1.0)
w_maint = SimpleVar(1.0)
w_driver = SimpleVar(1.0)
w_facility = SimpleVar(1.0)


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
            "Destination": {}
        }

        self.make_bidirectional()

        self.heuristic = {
            "Warehouse": 14, "Market": 12, "School": 11, "Library": 10,
            "Mall": 8, "Hospital": 7, "Park": 6, "Office": 5,
            "Garden": 4, "Stadium": 3, "Station": 2,
            "Airport": 2, "Destination": 0
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
        g_cost = {node: float('inf') for node in self.graph}
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
                    w_fuel.get() * fuel +
                    w_maint.get() * maintenance +
                    w_driver.get() * driver +
                    w_facility.get() * facility
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

positions = {
    "Warehouse": (80, 200),
    "Market": (180, 120),
    "School": (180, 300),
    "Library": (300, 320),
    "Mall": (300, 120),
    "Hospital": (300, 200),
    "Park": (420, 180),
    "Office": (420, 80),
    "Garden": (520, 220),
    "Stadium": (600, 280),
    "Station": (680, 200),
    "Airport": (520, 60),
    "Destination": (760, 180)
}


def set_weights(weights):
    w_fuel.set(float(weights.get("fuel", 1.0)))
    w_maint.set(float(weights.get("maintenance", 1.0)))
    w_driver.set(float(weights.get("driver", 1.0)))
    w_facility.set(float(weights.get("facility", 1.0)))


def _build_cost_breakdown(path):
    total_fuel = total_maint = total_driver = total_facility = 0

    for i in range(len(path) - 1):
        d = optimizer.graph[path[i]][path[i + 1]]
        total_fuel += d * 12
        total_maint += d * 6
        total_driver += d * 8
        total_facility += 30

    breakdown = [
        {
            "label": "Fuel",
            "base": total_fuel,
            "weight": float(w_fuel.get()),
            "weighted_cost": int(w_fuel.get() * total_fuel)
        },
        {
            "label": "Maintenance",
            "base": total_maint,
            "weight": float(w_maint.get()),
            "weighted_cost": int(w_maint.get() * total_maint)
        },
        {
            "label": "Driver",
            "base": total_driver,
            "weight": float(w_driver.get()),
            "weighted_cost": int(w_driver.get() * total_driver)
        },
        {
            "label": "Facility",
            "base": total_facility,
            "weight": float(w_facility.get()),
            "weighted_cost": int(w_facility.get() * total_facility)
        }
    ]

    total_cost = int(sum(item["weighted_cost"] for item in breakdown))
    return breakdown, total_cost


def compute_route(start, destination, weights):
    if start not in optimizer.graph or destination not in optimizer.graph:
        return {"path": None, "breakdown": [], "total_cost": None, "error": "Invalid node"}

    set_weights(weights)
    path, _ = optimizer.a_star(start, destination)

    if not path:
        return {"path": None, "breakdown": [], "total_cost": None, "error": "No route found"}

    breakdown, total_cost = _build_cost_breakdown(path)

    return {
        "path": path,
        "breakdown": breakdown,
        "total_cost": total_cost,
        "error": None
    }


def launch_gui():
    import tkinter as tk

    global w_fuel, w_maint, w_driver, w_facility

    root = tk.Tk()

    w_fuel = tk.DoubleVar(root, value=1.0)
    w_maint = tk.DoubleVar(root, value=1.0)
    w_driver = tk.DoubleVar(root, value=1.0)
    w_facility = tk.DoubleVar(root, value=1.0)

    root.title("AI Logistics Optimization System")
    root.geometry("1100x750")
    root.configure(bg="#eef2f7")

    tk.Label(root, text="AI Logistics Route Optimization", font=("Arial", 20, "bold"), bg="#eef2f7").pack(pady=10)

    canvas = tk.Canvas(root, width=850, height=350, bg="white")
    canvas.pack()

    def draw_graph():

        canvas.delete("all")
        drawn_edges = set()

        for node in optimizer.graph:
            x1, y1 = positions[node]
            for neighbor in optimizer.graph[node]:
                edge_key = tuple(sorted((node, neighbor)))
                if edge_key in drawn_edges:
                    continue
                drawn_edges.add(edge_key)
                x2, y2 = positions[neighbor]
                canvas.create_line(x1, y1, x2, y2, fill="#bbbbbb")

        for node in positions:
            x, y = positions[node]
            canvas.create_oval(x - 18, y - 18, x + 18, y + 18, fill="#3498db")
            canvas.create_text(x, y, text=node, fill="white", font=("Arial", 9, "bold"))

    draw_graph()

    truck = None

    def animate_truck(path):
        nonlocal truck

        for i in range(len(path) - 1):

            x1, y1 = positions[path[i]]
            x2, y2 = positions[path[i + 1]]

            for t in range(20):

                xt = x1 + (x2 - x1) * t / 20
                yt = y1 + (y2 - y1) * t / 20

                if truck:
                    canvas.delete(truck)

                truck = canvas.create_rectangle(xt - 6, yt - 6, xt + 6, yt + 6, fill="red")

                root.update()
                time.sleep(0.02)

    def show_history():

        win = tk.Toplevel(root)
        win.title("Trip History")
        win.geometry("500x400")

        text = tk.Text(win)
        text.pack(fill="both", expand=True)

        for trip in trip_history:
            text.insert(tk.END, trip + "\n\n")

    def run_optimizer():

        if resources.vehicles <= 0 or resources.drivers <= 0:
            route_label.config(text="No resources available")
            return

        start = start_var.get()
        goal = goal_var.get()

        draw_graph()

        path, _ = optimizer.a_star(start, goal)

        if not path:
            route_label.config(text="No route found")
            return

        for i in range(len(path) - 1):
            x1, y1 = positions[path[i]]
            x2, y2 = positions[path[i + 1]]
            canvas.create_line(x1, y1, x2, y2, fill="red", width=4)

        route_label.config(text=" -> ".join(path))

        resources.allocate()

        vehicle_label.config(text=f"Vehicles Left: {resources.vehicles}")
        driver_label.config(text=f"Drivers Left: {resources.drivers}")

        breakdown, weighted_total = _build_cost_breakdown(path)

        cost_text.config(text=f"""
Cost Breakdown:

Fuel: {breakdown[0]['base']} x {round(breakdown[0]['weight'], 1)} = INR {breakdown[0]['weighted_cost']}
Maintenance: {breakdown[1]['base']} x {round(breakdown[1]['weight'], 1)} = INR {breakdown[1]['weighted_cost']}
Driver: {breakdown[2]['base']} x {round(breakdown[2]['weight'], 1)} = INR {breakdown[2]['weighted_cost']}
Facility: {breakdown[3]['base']} x {round(breakdown[3]['weight'], 1)} = INR {breakdown[3]['weighted_cost']}

--------------------------------
TOTAL COST: INR {weighted_total}
""")

        trip_history.append(f"{datetime.datetime.now()} | {' -> '.join(path)} | INR {weighted_total}")

        animate_truck(path)

    frame = tk.Frame(root, bg="#eef2f7")
    frame.pack(pady=10)

    nodes = list(positions.keys())

    start_var = tk.StringVar(value="Warehouse")
    goal_var = tk.StringVar(value="Destination")

    tk.OptionMenu(frame, start_var, *nodes).grid(row=0, column=0, padx=5)
    tk.OptionMenu(frame, goal_var, *nodes).grid(row=0, column=1, padx=5)

    tk.Button(root, text="Find Route", command=run_optimizer, bg="#27ae60", fg="white").pack(pady=5)

    tk.Button(root, text="History", command=show_history, bg="#2980b9", fg="white").pack()

    cost_text = tk.Label(root, text="", justify="left", font=("Arial", 11), bg="#eef2f7")
    cost_text.pack(pady=10)

    side_frame = tk.Frame(root, bg="#eef2f7")
    side_frame.place(x=910, y=100)

    tk.Label(side_frame, text="Weights", font=("Arial", 12, "bold"), bg="#eef2f7").pack()

    tk.Scale(side_frame, label="Fuel", from_=0, to=1, resolution=0.1, orient="horizontal", variable=w_fuel, length=150).pack()

    tk.Scale(side_frame, label="Maintenance", from_=0, to=1, resolution=0.1, orient="horizontal", variable=w_maint, length=150).pack()

    tk.Scale(side_frame, label="Driver", from_=0, to=1, resolution=0.1, orient="horizontal", variable=w_driver, length=150).pack()

    tk.Scale(side_frame, label="Facility", from_=0, to=1, resolution=0.1, orient="horizontal", variable=w_facility, length=150).pack()

    route_label = tk.Label(root, text="", bg="#eef2f7", font=("Arial", 12))
    route_label.pack()

    vehicle_label = tk.Label(root, text="Vehicles Left: 5", bg="#eef2f7")
    vehicle_label.pack()

    driver_label = tk.Label(root, text="Drivers Left: 5", bg="#eef2f7")
    driver_label.pack()

    root.mainloop()


if __name__ == "__main__":
    launch_gui()
