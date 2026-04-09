import { useEffect, useMemo, useState, useCallback } from "react";
import L from "leaflet";
import { CircleMarker, MapContainer, Polyline, Tooltip, useMap } from "react-leaflet";

const API_BASE = "http://localhost:8000";

const defaultWeights = {
  fuel: 1,
  maintenance: 1,
  driver: 1,
  facility: 1,
};

const nodeStyles = {
  Warehouse: { fillColor: "#0f766e", color: "#0f766e", label: "Warehouse" },
  Destination: { fillColor: "#dc2626", color: "#dc2626", label: "Destination" },
};

function getNodeStyle(nodeId, isRouteNode) {
  if (isRouteNode) {
    return {
      fillColor: "#2563eb",
      color: "#ffffff",
      radius: 8,
      weight: 3,
      fillOpacity: 1,
    };
  }

  const variant = nodeStyles[nodeId];
  if (variant) {
    return {
      ...variant,
      radius: 8,
      weight: 2,
      fillOpacity: 0.95,
    };
  }

  return {
    fillColor: "#1d4ed8",
    color: "#dbeafe",
    radius: 8,
    weight: 2,
    fillOpacity: 0.92,
  };
}

function FitGraphBounds({ coordinates, routeCoords }) {
  const map = useMap();

  useEffect(() => {
    const activePoints = routeCoords.length > 1 ? routeCoords : Object.values(coordinates);
    if (activePoints.length === 0) return;

    const bounds = L.latLngBounds(activePoints);
    map.fitBounds(bounds, { padding: [36, 36], maxZoom: 13 });
  }, [coordinates, map, routeCoords]);

  return null;
}

function GraphBackdrop({ edges }) {
  return (
    <>
      {edges.map((edge) => (
        <Polyline
          key={`${edge.start}-${edge.end}-glow`}
          positions={edge.coordinates}
          pathOptions={{
            color: "#cbd5e1",
            weight: 12,
            opacity: 0.18,
            lineCap: "round",
            lineJoin: "round",
          }}
        />
      ))}
      {edges.map((edge) => (
        <Polyline
          key={`${edge.start}-${edge.end}`}
          positions={edge.coordinates}
          pathOptions={{
            color: "#64748b",
            weight: 4,
            opacity: 0.75,
            lineCap: "round",
            lineJoin: "round",
          }}
        />
      ))}
    </>
  );
}

function NodeMarkers({ coordinates, routePath }) {
  const routeNodeSet = useMemo(() => new Set(routePath), [routePath]);

  return Object.entries(coordinates).map(([nodeId, coords]) => {
    const isRouteNode = routeNodeSet.has(nodeId);
    const style = getNodeStyle(nodeId, isRouteNode);

    return (
      <CircleMarker key={nodeId} center={coords} pathOptions={style} radius={style.radius}>
        <Tooltip direction="top" offset={[0, -8]} permanent>
          <span className="map-node-label">{style.label || nodeId}</span>
        </Tooltip>
      </CircleMarker>
    );
  });
}

function TimerBar({ trip }) {
  const pct = trip.total_seconds > 0
    ? Math.max(0, trip.remaining_seconds / trip.total_seconds)
    : 0;

  const mins = Math.floor(trip.remaining_seconds / 60);
  const secs = trip.remaining_seconds % 60;
  const timeStr = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  const isDone = trip.status === "completed";

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
      <p className="mb-1 truncate font-medium text-slate-700">
        {trip.path.join(" -> ")}
      </p>

      <div className="mb-1 h-2 w-full overflow-hidden rounded-full bg-slate-200">
        <div
          className={`h-2 rounded-full transition-all duration-1000 ${isDone ? "bg-emerald-500" : "bg-blue-500"}`}
          style={{ width: `${(1 - pct) * 100}%` }}
        />
      </div>

      <div className="flex items-center justify-between">
        <span className={`text-xs font-semibold ${isDone ? "text-emerald-600" : "text-blue-600"}`}>
          {isDone ? "Completed" : `${timeStr} remaining`}
        </span>
        <span className="text-xs text-slate-400">
          dist: {Math.round(trip.total_seconds / 3)} units
        </span>
      </div>
    </div>
  );
}

function ResourceDots({ used, max, color }) {
  return (
    <div className="flex flex-wrap gap-1">
      {Array.from({ length: max }).map((_, i) => (
        <span
          key={i}
          className={`inline-block h-3 w-3 rounded-full ${i < (max - used) ? color : "bg-slate-200"}`}
        />
      ))}
    </div>
  );
}

function App() {
  const [nodes, setNodes] = useState([]);
  const [coordinates, setCoordinates] = useState({});
  const [edges, setEdges] = useState([]);
  const [start, setStart] = useState("Warehouse");
  const [destination, setDestination] = useState("Destination");
  const [weights, setWeights] = useState(defaultWeights);
  const [routePath, setRoutePath] = useState([]);
  const [routeCoordinates, setRouteCoordinates] = useState([]);
  const [breakdown, setBreakdown] = useState([]);
  const [routeSegments, setRouteSegments] = useState([]);
  const [totalCost, setTotalCost] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [resources, setResources] = useState({ vehicles: 5, drivers: 5, max_vehicles: 5, max_drivers: 5 });
  const [activeTrips, setActiveTrips] = useState([]);

  useEffect(() => {
    const loadNodes = async () => {
      try {
        const res = await fetch(`${API_BASE}/nodes`);
        const data = await res.json();
        setNodes(data.nodes);
        setCoordinates(data.coordinates);
        setEdges(data.edges || []);
      } catch {
        setError("Could not load map nodes from backend.");
      }
    };
    loadNodes();
  }, []);

  const pollStatus = useCallback(async () => {
    try {
      const [rRes, tRes] = await Promise.all([
        fetch(`${API_BASE}/resources`),
        fetch(`${API_BASE}/trips/active`),
      ]);
      setResources(await rRes.json());
      setActiveTrips(await tRes.json());
    } catch {
      // Ignore transient polling failures.
    }
  }, []);

  useEffect(() => {
    pollStatus();
    const id = setInterval(pollStatus, 1000);
    return () => clearInterval(id);
  }, [pollStatus]);

  const center = useMemo(() => {
    const values = Object.values(coordinates);
    if (values.length === 0) return [28.65, 77.45];
    const avgLat = values.reduce((sum, [lat]) => sum + lat, 0) / values.length;
    const avgLng = values.reduce((sum, [, lng]) => sum + lng, 0) / values.length;
    return [avgLat, avgLng];
  }, [coordinates]);

  const handleWeightChange = (key, value) => {
    setWeights((prev) => ({ ...prev, [key]: Number(value) }));
  };

  const findRoute = async () => {
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/route`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ start, destination, weights }),
      });

      if (!res.ok) {
        const msg = await res.json();
        throw new Error(msg.detail || "Route request failed.");
      }

      const data = await res.json();
      setRoutePath(data.path);
      setRouteCoordinates(data.route_coordinates);
      setBreakdown(data.breakdown);
      setRouteSegments(data.segments || []);
      setTotalCost(data.total_cost);
      setShowDetails(false);
    } catch (err) {
      setRoutePath([]);
      setRouteCoordinates([]);
      setBreakdown([]);
      setRouteSegments([]);
      setTotalCost(null);
      setShowDetails(false);
      setError(err.message || "Unexpected error.");
    } finally {
      setLoading(false);
    }
  };

  const resetNodes = async () => {
    setError("");
    try {
      const res = await fetch(`${API_BASE}/reset`, { method: "POST" });
      if (!res.ok) {
        throw new Error("Reset request failed.");
      }

      const data = await res.json();
      setResources(data);
      setActiveTrips([]);
    } catch (err) {
      setError(err.message || "Could not reset the system.");
    }

    setStart("Warehouse");
    setDestination("Destination");
    setWeights(defaultWeights);
    setRoutePath([]);
    setRouteCoordinates([]);
    setBreakdown([]);
    setRouteSegments([]);
    setTotalCost(null);
    setShowDetails(false);
  };

  const noResources = resources.vehicles === 0 || resources.drivers === 0;

  return (
    <div className="h-screen w-screen p-4">
      <div className="mx-auto flex h-full max-w-7xl flex-col gap-4 lg:flex-row">
        <aside className="flex w-full flex-col gap-4 lg:w-80">
          <div className="rounded-2xl bg-white p-4 shadow-lg">
            <h1 className="mb-4 text-xl font-bold text-slate-800">Logistics Route Optimization</h1>

            <label className="mb-2 block text-sm font-semibold text-slate-700">Start</label>
            <select
              className="mb-3 w-full rounded-md border border-slate-300 p-2"
              value={start}
              onChange={(e) => setStart(e.target.value)}
            >
              {nodes.map((node) => <option key={node} value={node}>{node}</option>)}
            </select>

            <label className="mb-2 block text-sm font-semibold text-slate-700">Destination</label>
            <select
              className="mb-4 w-full rounded-md border border-slate-300 p-2"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
            >
              {nodes.map((node) => <option key={node} value={node}>{node}</option>)}
            </select>

            {["fuel", "maintenance", "driver", "facility"].map((key) => (
              <div key={key} className="mb-3">
                <label className="mb-1 block text-sm font-medium capitalize text-slate-700">
                  {key}: {weights[key].toFixed(1)}
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={weights[key]}
                  onChange={(e) => handleWeightChange(key, e.target.value)}
                  className="w-full"
                />
              </div>
            ))}

            <div className="mt-2 flex gap-2">
              <button
                onClick={findRoute}
                disabled={loading || noResources}
                className="w-full rounded-lg bg-emerald-600 px-4 py-2 font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? "Finding..." : "Find Route"}
              </button>
              <button
                onClick={resetNodes}
                className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2 font-semibold text-slate-700 hover:bg-slate-50"
              >
                Reset
              </button>
            </div>

            {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

            <div className="mt-4 rounded-lg border border-slate-200 p-3">
              <p className="text-sm font-semibold text-slate-700">Route Path</p>
              <p className="mt-1 text-sm text-slate-900">
                {routePath.length ? routePath.join(" -> ") : "No route yet"}
              </p>
            </div>
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-lg">
            <h2 className="mb-3 text-base font-bold text-slate-800">Resources</h2>
            <div className="mb-3">
              <div className="mb-1 flex items-center justify-between">
                <span className="text-sm font-medium text-slate-700">Vehicles</span>
                <span className="text-sm font-semibold text-slate-900">
                  {resources.vehicles} / {resources.max_vehicles}
                </span>
              </div>
              <ResourceDots used={resources.max_vehicles - resources.vehicles} max={resources.max_vehicles} color="bg-blue-500" />
            </div>
            <div>
              <div className="mb-1 flex items-center justify-between">
                <span className="text-sm font-medium text-slate-700">Drivers</span>
                <span className="text-sm font-semibold text-slate-900">
                  {resources.drivers} / {resources.max_drivers}
                </span>
              </div>
              <ResourceDots used={resources.max_drivers - resources.drivers} max={resources.max_drivers} color="bg-violet-500" />
            </div>
            {noResources && (
              <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-xs font-semibold text-red-600">
                All resources in use, wait for a trip to complete.
              </p>
            )}
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-lg">
            <h2 className="mb-3 text-base font-bold text-slate-800">
              Active Trips
              {activeTrips.length > 0 && (
                <span className="ml-2 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700">
                  {activeTrips.length}
                </span>
              )}
            </h2>
            {activeTrips.length === 0 ? (
              <p className="text-sm text-slate-400">No active trips.</p>
            ) : (
              <div className="flex flex-col gap-2">
                {activeTrips.map((trip) => (
                  <TimerBar key={trip.trip_id} trip={trip} />
                ))}
              </div>
            )}
          </div>
        </aside>

        <main className="flex min-h-0 flex-1 flex-col gap-4">
          <div className="network-shell h-[55%] min-h-[300px] rounded-2xl border border-slate-200 bg-white p-2 shadow-lg">
            <div className="network-map h-full w-full overflow-hidden rounded-xl">
              <div className="network-map__chrome">
                <span className="network-map__badge">Custom route network</span>
                {/* <span className="network-map__hint">Your graph nodes and connections</span> */}
              </div>
              <MapContainer
                center={center}
                zoom={11}
                zoomControl={false}
                attributionControl={false}
                scrollWheelZoom
                className="h-full w-full rounded-xl"
              >
                <GraphBackdrop edges={edges} />
                <NodeMarkers coordinates={coordinates} routePath={routePath} />
                {routeCoordinates.length > 1 && (
                  <>
                    <Polyline
                      positions={routeCoordinates}
                      pathOptions={{ color: "#0f172a", weight: 11, opacity: 0.14, lineJoin: "round", lineCap: "round" }}
                    />
                    <Polyline
                      positions={routeCoordinates}
                      pathOptions={{ color: "#22c55e", weight: 7, opacity: 0.25, lineJoin: "round", lineCap: "round" }}
                    />
                    <Polyline
                      positions={routeCoordinates}
                      pathOptions={{ color: "#2563eb", weight: 4, opacity: 0.98, lineJoin: "round", lineCap: "round" }}
                    />
                  </>
                )}
                <FitGraphBounds coordinates={coordinates} routeCoords={routeCoordinates} />
              </MapContainer>
            </div>
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-lg">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold text-slate-800">Chosen Route Details</h2>
                <p className="text-sm text-slate-500">
                  Inspect distance and per-segment cost only when needed.
                </p>
              </div>
              <button
                onClick={() => setShowDetails((prev) => !prev)}
                disabled={routeSegments.length === 0}
                className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {showDetails ? "Hide Details" : "Details"}
              </button>
            </div>

            {routeSegments.length === 0 ? (
              <p className="text-sm text-slate-400">Find a route to view segment-wise details.</p>
            ) : showDetails ? (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 text-left text-slate-600">
                        <th className="py-2 pr-3">Segment</th>
                        <th className="py-2 pr-3">Distance</th>
                        <th className="py-2 pr-3">Fuel</th>
                        <th className="py-2 pr-3">Maintenance</th>
                        <th className="py-2 pr-3">Driver</th>
                        <th className="py-2 pr-3">Facility</th>
                        <th className="py-2">Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {routeSegments.map((segment) => (
                        <tr
                          key={`${segment.from_node}-${segment.to_node}`}
                          className="border-b border-slate-100"
                        >
                          <td className="py-2 pr-3 font-medium text-slate-800">
                            {segment.from_node} -> {segment.to_node}
                          </td>
                          <td className="py-2 pr-3">{segment.distance}</td>
                          <td className="py-2 pr-3">INR {segment.fuel_cost}</td>
                          <td className="py-2 pr-3">INR {segment.maintenance_cost}</td>
                          <td className="py-2 pr-3">INR {segment.driver_cost}</td>
                          <td className="py-2 pr-3">INR {segment.facility_cost}</td>
                          <td className="py-2 font-semibold text-slate-900">INR {segment.segment_total}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="mt-4 flex flex-wrap gap-4 border-t border-slate-100 pt-4 text-sm">
                  {breakdown.map((item) => (
                    <div key={item.label} className="rounded-lg bg-slate-50 px-3 py-2 text-slate-700">
                      <span className="font-semibold text-slate-900">{item.label}:</span> INR {item.weighted_cost}
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p className="text-sm text-slate-500">Click the Details button to open the chosen route table.</p>
            )}

            <p className="mt-4 text-base font-bold text-slate-900">
              TOTAL COST: {totalCost === null ? "-" : `INR ${totalCost}`}
            </p>
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
