from pathlib import Path
import sys
import uuid
import threading
import time
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))
from old import compute_route, optimizer, positions  # noqa: E402

app = FastAPI(title="Logistics Route Optimization API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- CONSTANTS ---------------- #

SECONDS_PER_UNIT = 3   # distance unit → seconds (tune as needed)
MAX_VEHICLES = 5
MAX_DRIVERS  = 5


# ---------------- RESOURCE MANAGER ---------------- #

class ResourceManager:
    def __init__(self):
        self._lock     = threading.Lock()
        self.vehicles  = MAX_VEHICLES
        self.drivers   = MAX_DRIVERS

    def allocate(self) -> bool:
        with self._lock:
            if self.vehicles > 0 and self.drivers > 0:
                self.vehicles -= 1
                self.drivers  -= 1
                return True
            return False

    def release(self):
        with self._lock:
            self.vehicles = min(self.vehicles + 1, MAX_VEHICLES)
            self.drivers  = min(self.drivers  + 1, MAX_DRIVERS)

    def status(self) -> dict:
        with self._lock:
            return {"vehicles": self.vehicles, "drivers": self.drivers}


resources = ResourceManager()


# ---------------- TRIP STORE ---------------- #

# trip_id -> trip dict
active_trips: Dict[str, dict] = {}
trips_lock = threading.Lock()


def _start_trip_timer(trip_id: str, total_seconds: int):
    """Background thread that counts down and releases resources when done."""
    end_time = time.time() + total_seconds
    while True:
        remaining = end_time - time.time()
        with trips_lock:
            if trip_id not in active_trips:
                break
            if remaining <= 0:
                active_trips[trip_id]["remaining_seconds"] = 0
                active_trips[trip_id]["status"] = "completed"
                break
            active_trips[trip_id]["remaining_seconds"] = int(remaining)
        time.sleep(1)

    # Release resources and mark done
    resources.release()
    # Keep the completed entry briefly so the frontend can show "Done"
    time.sleep(3)
    with trips_lock:
        active_trips.pop(trip_id, None)


# ---------------- PYDANTIC MODELS ---------------- #

class Weights(BaseModel):
    fuel:        float = Field(default=1.0, ge=0)
    maintenance: float = Field(default=1.0, ge=0)
    driver:      float = Field(default=1.0, ge=0)
    facility:    float = Field(default=1.0, ge=0)


class RouteRequest(BaseModel):
    start:       str
    destination: str
    weights:     Weights


class CostItem(BaseModel):
    label:         str
    base:          float
    weight:        float
    weighted_cost: float


class RouteResponse(BaseModel):
    path:              List[str]
    breakdown:         List[CostItem]
    total_cost:        float
    route_coordinates: List[List[float]]
    trip_id:           str          # new — returned so frontend can track this trip
    total_seconds:     int          # new — total timer duration


class TripStatus(BaseModel):
    trip_id:          str
    path:             List[str]
    total_seconds:    int
    remaining_seconds: int
    status:           str           # "active" | "completed"


class ResourceStatus(BaseModel):
    vehicles: int
    drivers:  int
    max_vehicles: int
    max_drivers:  int


# ---------------- HELPERS ---------------- #

def _to_lat_lng(x: int, y: int) -> List[float]:
    base_lat, base_lng = 28.6139, 77.2090
    lat = base_lat + ((350 - y) * 0.0012)
    lng = base_lng + (x * 0.0012)
    return [round(lat, 6), round(lng, 6)]


def _all_node_coordinates() -> Dict[str, List[float]]:
    return {node: _to_lat_lng(*xy) for node, xy in positions.items()}


def _path_distance(path: List[str]) -> int:
    return sum(
        optimizer.graph[path[i]][path[i + 1]]
        for i in range(len(path) - 1)
    )


# ---------------- ROUTES ---------------- #

@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/nodes")
def get_nodes() -> Dict[str, object]:
    return {
        "nodes":       list(optimizer.graph.keys()),
        "coordinates": _all_node_coordinates(),
    }


@app.get("/resources", response_model=ResourceStatus)
def get_resources() -> ResourceStatus:
    s = resources.status()
    return ResourceStatus(
        vehicles=s["vehicles"],
        drivers=s["drivers"],
        max_vehicles=MAX_VEHICLES,
        max_drivers=MAX_DRIVERS,
    )


@app.get("/trips/active", response_model=List[TripStatus])
def get_active_trips() -> List[TripStatus]:
    with trips_lock:
        return [
            TripStatus(
                trip_id=t["trip_id"],
                path=t["path"],
                total_seconds=t["total_seconds"],
                remaining_seconds=t["remaining_seconds"],
                status=t["status"],
            )
            for t in active_trips.values()
        ]


@app.post("/route", response_model=RouteResponse)
def get_route(payload: RouteRequest) -> RouteResponse:
    # Check resource availability first
    if not resources.allocate():
        raise HTTPException(
            status_code=503,
            detail="No vehicles or drivers available. Please wait for an active trip to complete."
        )

    result = compute_route(
        payload.start, payload.destination, payload.weights.model_dump()
    )

    if result["error"]:
        resources.release()   # give back what we just took
        raise HTTPException(status_code=400, detail=result["error"])

    path           = result["path"]
    total_distance = _path_distance(path)
    total_seconds  = total_distance * SECONDS_PER_UNIT
    trip_id        = str(uuid.uuid4())

    # Register trip
    with trips_lock:
        active_trips[trip_id] = {
            "trip_id":           trip_id,
            "path":              path,
            "total_seconds":     total_seconds,
            "remaining_seconds": total_seconds,
            "status":            "active",
        }

    # Start background countdown thread
    t = threading.Thread(
        target=_start_trip_timer,
        args=(trip_id, total_seconds),
        daemon=True,
    )
    t.start()

    route_coordinates = [_to_lat_lng(*positions[node]) for node in path]

    return RouteResponse(
        path=path,
        breakdown=result["breakdown"],
        total_cost=result["total_cost"],
        route_coordinates=route_coordinates,
        trip_id=trip_id,
        total_seconds=total_seconds,
    )