from pathlib import Path
import sys
from typing import Dict, List

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


class Weights(BaseModel):
    fuel: float = Field(default=1.0, ge=0)
    maintenance: float = Field(default=1.0, ge=0)
    driver: float = Field(default=1.0, ge=0)
    facility: float = Field(default=1.0, ge=0)


class RouteRequest(BaseModel):
    start: str
    destination: str
    weights: Weights


class CostItem(BaseModel):
    label: str
    base: float
    weight: float
    weighted_cost: float


class RouteResponse(BaseModel):
    path: List[str]
    breakdown: List[CostItem]
    total_cost: float
    route_coordinates: List[List[float]]


def _to_lat_lng(x: int, y: int) -> List[float]:
    # Converts canvas points to map coordinates around Delhi.
    base_lat, base_lng = 28.6139, 77.2090
    lat = base_lat + ((350 - y) * 0.0012)
    lng = base_lng + (x * 0.0012)
    return [round(lat, 6), round(lng, 6)]


def _all_node_coordinates() -> Dict[str, List[float]]:
    return {node: _to_lat_lng(*xy) for node, xy in positions.items()}


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/nodes")
def get_nodes() -> Dict[str, object]:
    return {
        "nodes": list(optimizer.graph.keys()),
        "coordinates": _all_node_coordinates(),
    }


@app.post("/route", response_model=RouteResponse)
def get_route(payload: RouteRequest) -> RouteResponse:
    result = compute_route(payload.start, payload.destination, payload.weights.model_dump())

    if result["error"]:
        raise HTTPException(status_code=400, detail=result["error"])

    path = result["path"]
    route_coordinates = [_to_lat_lng(*positions[node]) for node in path]

    return RouteResponse(
        path=path,
        breakdown=result["breakdown"],
        total_cost=result["total_cost"],
        route_coordinates=route_coordinates,
    )
