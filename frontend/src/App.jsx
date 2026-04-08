import { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import { MapContainer, Polyline, TileLayer, useMap } from "react-leaflet";

const API_BASE = "http://localhost:8000";

const defaultWeights = {
  fuel: 1,
  maintenance: 1,
  driver: 1,
  facility: 1,
};

function FitRouteBounds({ routeCoords }) {
  const map = useMap();

  useEffect(() => {
    if (routeCoords.length > 1) {
      const bounds = L.latLngBounds(routeCoords);
      map.fitBounds(bounds, { padding: [40, 40] });
    }
  }, [map, routeCoords]);

  return null;
}

function NodeLayerManager({ coordinates, routePath }) {
  const map = useMap();
  const allNodesLayerRef = useRef(null);
  const routeNodesLayerRef = useRef(null);

  useEffect(() => {
    if (!allNodesLayerRef.current) {
      allNodesLayerRef.current = L.layerGroup().addTo(map);
    }
    if (!routeNodesLayerRef.current) {
      routeNodesLayerRef.current = L.layerGroup();
    }

    return () => {
      if (allNodesLayerRef.current && map.hasLayer(allNodesLayerRef.current)) {
        map.removeLayer(allNodesLayerRef.current);
      }
      if (routeNodesLayerRef.current && map.hasLayer(routeNodesLayerRef.current)) {
        map.removeLayer(routeNodesLayerRef.current);
      }
    };
  }, [map]);

  useEffect(() => {
    if (!allNodesLayerRef.current) return;

    allNodesLayerRef.current.clearLayers();
    Object.entries(coordinates).forEach(([nodeId, coords]) => {
      const marker = L.circleMarker(coords, {
        radius: 6,
        color: "#2563eb",
        fillColor: "#2563eb",
        fillOpacity: 0.9,
      });
      marker.nodeId = nodeId;
      marker.bindPopup(nodeId);
      marker.addTo(allNodesLayerRef.current);
    });
  }, [coordinates]);

  useEffect(() => {
    if (!allNodesLayerRef.current || !routeNodesLayerRef.current) return;

    if (routePath.length > 1) {
      if (map.hasLayer(allNodesLayerRef.current)) {
        map.removeLayer(allNodesLayerRef.current);
      }

      routeNodesLayerRef.current.clearLayers();
      routePath.forEach((nodeId) => {
        const coords = coordinates[nodeId];
        if (!coords) return;

        const marker = L.circleMarker(coords, {
          radius: 7,
          color: "#22c55e",
          fillColor: "#22c55e",
          fillOpacity: 1,
        });
        marker.bindPopup(nodeId);
        marker.addTo(routeNodesLayerRef.current);
      });

      if (!map.hasLayer(routeNodesLayerRef.current)) {
        routeNodesLayerRef.current.addTo(map);
      }
      return;
    }

    if (map.hasLayer(routeNodesLayerRef.current)) {
      map.removeLayer(routeNodesLayerRef.current);
    }
    if (!map.hasLayer(allNodesLayerRef.current)) {
      allNodesLayerRef.current.addTo(map);
    }
  }, [coordinates, map, routePath]);

  return null;
}

function App() {
  const [nodes, setNodes] = useState([]);
  const [coordinates, setCoordinates] = useState({});
  const [start, setStart] = useState("Warehouse");
  const [destination, setDestination] = useState("Destination");
  const [weights, setWeights] = useState(defaultWeights);
  const [routePath, setRoutePath] = useState([]);
  const [routeCoordinates, setRouteCoordinates] = useState([]);
  const [breakdown, setBreakdown] = useState([]);
  const [totalCost, setTotalCost] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadNodes = async () => {
      try {
        const res = await fetch(`${API_BASE}/nodes`);
        const data = await res.json();
        setNodes(data.nodes);
        setCoordinates(data.coordinates);
      } catch (err) {
        setError("Could not load map nodes from backend.");
      }
    };

    loadNodes();
  }, []);

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

    try {
      const res = await fetch(`${API_BASE}/route`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          start,
          destination,
          weights,
        }),
      });

      if (!res.ok) {
        const msg = await res.json();
        throw new Error(msg.detail || "Route request failed.");
      }

      const data = await res.json();
      setRoutePath(data.path);
      setRouteCoordinates(data.route_coordinates);
      setBreakdown(data.breakdown);
      setTotalCost(data.total_cost);
    } catch (err) {
      setRoutePath([]);
      setRouteCoordinates([]);
      setBreakdown([]);
      setTotalCost(null);
      setError(err.message || "Unexpected error.");
    }
  };

  const resetNodes = () => {
    setRoutePath([]);
    setRouteCoordinates([]);
  };

  return (
    <div className="h-screen w-screen p-4">
      <div className="mx-auto flex h-full max-w-7xl flex-col gap-4 lg:flex-row">
        <aside className="w-full rounded-2xl bg-white p-4 shadow-lg lg:w-80">
          <h1 className="mb-4 text-xl font-bold text-slate-800">Logistics Route Optimization</h1>

          <label className="mb-2 block text-sm font-semibold text-slate-700">Start</label>
          <select
            className="mb-3 w-full rounded-md border border-slate-300 p-2"
            value={start}
            onChange={(e) => setStart(e.target.value)}
          >
            {nodes.map((node) => (
              <option key={node} value={node}>
                {node}
              </option>
            ))}
          </select>

          <label className="mb-2 block text-sm font-semibold text-slate-700">Destination</label>
          <select
            className="mb-4 w-full rounded-md border border-slate-300 p-2"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
          >
            {nodes.map((node) => (
              <option key={node} value={node}>
                {node}
              </option>
            ))}
          </select>

          {["fuel", "maintenance", "driver", "facility"].map((key) => (
            <div key={key} className="mb-3">
              <label className="mb-1 block text-sm font-medium capitalize text-slate-700">
                {key}: {weights[key].toFixed(1)}
              </label>
              <input
                type="range"
                min="0"
                max="2"
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
              className="w-full rounded-lg bg-emerald-600 px-4 py-2 font-semibold text-white hover:bg-emerald-700"
            >
              Find Route
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
            <p className="mt-1 text-sm text-slate-900">{routePath.length ? routePath.join(" -> ") : "No route yet"}</p>
          </div>
        </aside>

        <main className="flex min-h-0 flex-1 flex-col gap-4">
          <div className="h-[50%] min-h-[300px] rounded-2xl border border-slate-200 bg-white p-2 shadow-lg">
            <MapContainer center={center} zoom={11} scrollWheelZoom className="rounded-xl">
              <TileLayer
                attribution="&copy; OpenStreetMap & CartoDB"
                subdomains="abcd"
                maxZoom={19}
                url="https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png"
              />
              {/* Optional light labels style:
              <TileLayer
                attribution="&copy; OpenStreetMap & CartoDB"
                subdomains="abcd"
                maxZoom={19}
                url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
              />
              Optional dark style:
              <TileLayer
                attribution="&copy; OpenStreetMap & CartoDB"
                subdomains="abcd"
                maxZoom={19}
                url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              />
              */}

              <NodeLayerManager coordinates={coordinates} routePath={routePath} />

              {routeCoordinates.length > 1 && (
                <>
                  <Polyline
                    positions={routeCoordinates}
                    pathOptions={{
                      color: "#000",
                      weight: 6,
                      opacity: 0.1,
                    }}
                  />
                  <Polyline
                    positions={routeCoordinates}
                    pathOptions={{
                      color: "#2563eb",
                      weight: 4,
                      opacity: 0.95,
                      lineJoin: "round",
                      lineCap: "round",
                      smoothFactor: 1.5,
                    }}
                  />
                  <FitRouteBounds routeCoords={routeCoordinates} />
                </>
              )}
            </MapContainer>
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-lg">
            <h2 className="mb-3 text-lg font-bold text-slate-800">Cost Breakdown</h2>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-slate-600">
                    <th className="py-2">Component</th>
                    <th className="py-2">Base</th>
                    <th className="py-2">Weight</th>
                    <th className="py-2">Weighted Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {breakdown.map((item) => (
                    <tr key={item.label} className="border-b border-slate-100">
                      <td className="py-2">{item.label}</td>
                      <td className="py-2">{item.base}</td>
                      <td className="py-2">{item.weight}</td>
                      <td className="py-2">INR {item.weighted_cost}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-3 text-base font-bold text-slate-900">
              TOTAL COST: {totalCost === null ? "-" : `INR ${totalCost}`}
            </p>
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
