"""imgw-mcp — MCP server for IMGW (Polish Meteorological Institute) public API.

Wraps https://danepubliczne.imgw.pl/api/data/ — the public data feed for
IMGW-PIB (Institute of Meteorology and Water Management). No auth, no
registration. Data flows only between your machine and IMGW.

Covers three feeds:
- synop: hourly weather observations from ~60 synoptic stations
- hydro: water level, flow rate, and warning thresholds at ~900 hydrological stations
- warnings: active meteorological warnings across Poland

Tools: get_weather, get_hydro, get_warnings, list_weather_stations,
list_hydro_stations.

Author: Bartosz Kuć <firma@bartosza.pl>
Repo:   https://github.com/bartosz-kuc/imgw-mcp
License: MIT
"""

import asyncio
import json
from typing import Any

import requests

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

BASE = "https://danepubliczne.imgw.pl/api/data"


def _get(path: str) -> Any:
    resp = requests.get(f"{BASE}/{path}", params={"format": "json"}, timeout=30)
    if resp.status_code == 404:
        try:
            return {"error": "Not found", "status": 404, "detail": resp.json()}
        except ValueError:
            return {"error": "Not found", "status": 404}
    resp.raise_for_status()
    return resp.json()


def _hydro_annotate(station: dict) -> dict:
    """Add alarm_status: normal / warning / alarm based on stan_wody vs. thresholds."""
    try:
        current = int(station.get("stan_wody") or 0)
        alarm = int(station.get("stan_alarmowy") or 0)
        warning = int(station.get("stan_ostrzegawczy") or 0)
    except (TypeError, ValueError):
        return station
    if alarm and current >= alarm:
        status = "alarm"
    elif warning and current >= warning:
        status = "warning"
    else:
        status = "normal"
    station = dict(station)
    station["alarm_status"] = status
    return station


server = Server("imgw")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_weather",
            description=(
                "Get current synoptic weather observations from IMGW. With no station: returns all ~60 stations. "
                "With station: returns just that one. Data updates ~hourly. Fields: temperature (°C), wind speed (m/s), "
                "wind direction (degrees), relative humidity (%), precipitation sum (mm), pressure (hPa)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "station": {"type": "string", "description": "Station name (case-insensitive, ASCII-fold — e.g. 'warszawa', 'krakow'). Omit to get all."},
                },
            },
        ),
        Tool(
            name="get_hydro",
            description=(
                "Get current hydrological readings from IMGW. Includes water level (stan_wody), flow rate, water temperature, "
                "and the alarm / warning threshold levels for the station. Server annotates each with `alarm_status` "
                "= normal / warning / alarm computed from current vs thresholds."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "station": {"type": "string", "description": "Station name (case-insensitive substring). Omit to get all ~900 stations."},
                    "river": {"type": "string", "description": "Filter by river name (case-insensitive substring)"},
                    "province": {"type": "string", "description": "Filter by voivodeship (e.g., 'mazowieckie')"},
                    "only_alerts": {"type": "boolean", "default": False, "description": "If true, only return stations in warning or alarm state"},
                    "limit": {"type": "integer", "default": 100, "description": "Max results (default 100 — full set is ~900)"},
                },
            },
        ),
        Tool(
            name="get_warnings",
            description=(
                "Get active IMGW meteorological warnings across Poland. Fields: nazwa_zdarzenia (event type — burze, mróz, "
                "upał, opady, wiatr, etc.), stopien (severity 1..3), prawdopodobienstwo (probability %), obowiazuje_od / _do, teren (affected area)."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="list_weather_stations",
            description="List synoptic station names available in the /synop feed. Useful for finding the right station name.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="list_hydro_stations",
            description="List hydrological station names, rivers, and provinces from the /hydro feed. Optional query filters. Used to find the right station name for get_hydro.",
            inputSchema={
                "type": "object",
                "properties": {
                    "province": {"type": "string", "description": "Optional voivodeship filter"},
                    "river": {"type": "string", "description": "Optional river filter"},
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    if name == "get_weather":
        station = (arguments.get("station") or "").strip()
        if station:
            # IMGW's per-station endpoint expects lowercase name without diacritics
            slug = station.lower().replace(" ", "-")
            data = _get(f"synop/station/{slug}")
        else:
            data = _get("synop")
        return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]

    if name == "get_hydro":
        data = _get("hydro")
        if not isinstance(data, list):
            return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]

        stations = [_hydro_annotate(s) for s in data]

        station_sub = (arguments.get("station") or "").strip().lower()
        river_sub = (arguments.get("river") or "").strip().lower()
        province_sub = (arguments.get("province") or "").strip().lower()
        only_alerts = bool(arguments.get("only_alerts", False))
        limit = int(arguments.get("limit", 100))

        filtered = []
        for s in stations:
            if station_sub and station_sub not in (s.get("stacja") or "").lower():
                continue
            if river_sub and river_sub not in (s.get("rzeka") or "").lower():
                continue
            if province_sub and province_sub not in (s.get("wojewodztwo") or "").lower():
                continue
            if only_alerts and s.get("alarm_status") not in ("warning", "alarm"):
                continue
            filtered.append(s)
            if len(filtered) >= limit:
                break

        return [TextContent(type="text", text=json.dumps({
            "total_available": len(stations),
            "returned": len(filtered),
            "results": filtered,
        }, ensure_ascii=False, indent=2))]

    if name == "get_warnings":
        data = _get("warningsMeteo")
        return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]

    if name == "list_weather_stations":
        data = _get("synop")
        if not isinstance(data, list):
            return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]
        stations = sorted({s.get("stacja") for s in data if s.get("stacja")})
        return [TextContent(type="text", text=json.dumps({"count": len(stations), "stations": stations}, ensure_ascii=False, indent=2))]

    if name == "list_hydro_stations":
        data = _get("hydro")
        if not isinstance(data, list):
            return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]
        province_sub = (arguments.get("province") or "").strip().lower()
        river_sub = (arguments.get("river") or "").strip().lower()
        out = []
        for s in data:
            if province_sub and province_sub not in (s.get("wojewodztwo") or "").lower():
                continue
            if river_sub and river_sub not in (s.get("rzeka") or "").lower():
                continue
            out.append({"stacja": s.get("stacja"), "rzeka": s.get("rzeka"), "wojewodztwo": s.get("wojewodztwo")})
        return [TextContent(type="text", text=json.dumps({"count": len(out), "stations": out}, ensure_ascii=False, indent=2))]

    raise ValueError(f"Unknown tool: {name}")


async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
