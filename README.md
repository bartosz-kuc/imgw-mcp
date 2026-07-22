# imgw-mcp

Local MCP server for **IMGW-PIB** (Polish Institute of Meteorology and Water Management) public data feed — current weather, hydrological readings, and active meteorological warnings across Poland.

Part of the [honest-mcp family](https://github.com/bartosz-kuc?tab=repositories) of small, auditable, local-first MCP servers.

## Why

Anyone in Poland who watches river levels (flood-plain landlord, kayaker, farmer), plans outdoor work, or just wants a native alternative to yr.no or the ECMWF apps can hand IMGW's raw feed to their AI in one line. No API key. No rate limit worth worrying about.

## Features

Five tools:

- `get_weather` — current synoptic observations. Whole country (~60 stations) or one station.
- `get_hydro` — hydrological readings. Water level, flow, water temperature, alarm/warning thresholds. Server annotates each with computed `alarm_status` (normal / warning / alarm).
- `get_warnings` — active IMGW meteorological warnings (storms, frost, heat, precipitation, wind) with severity and validity window.
- `list_weather_stations` — station-name index for `get_weather`.
- `list_hydro_stations` — station index with rivers and provinces, filterable, for `get_hydro`.

## Data source

- Endpoint: [danepubliczne.imgw.pl/api/data](https://danepubliczne.imgw.pl/api/data/) — IMGW public data feed
- No API key
- Refresh: synop hourly, hydro every ~20 minutes, warnings whenever a new one is issued

## Requirements

- Python 3.10+

## Setup

```bash
git clone https://github.com/bartosz-kuc/imgw-mcp.git
cd imgw-mcp
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

Register with Claude Code:

```bash
claude mcp add imgw /absolute/path/to/venv/bin/python /absolute/path/to/server.py
```

Claude Desktop `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "imgw": {
      "command": "/absolute/path/to/venv/bin/python",
      "args": ["/absolute/path/to/server.py"]
    }
  }
}
```

## Example usage

> "What's the temperature in Warsaw right now?"

`get_weather(station="warszawa")` → single-station JSON with temperature, wind, humidity, precipitation, pressure.

> "Any active storm warnings?"

`get_warnings()` → list of active warnings, filter yourself by `nazwa_zdarzenia`.

> "Any rivers in Mazowieckie above alarm level?"

`get_hydro(province="mazowieckie", only_alerts=true)` → just stations where current level ≥ alarm threshold.

## Data flow

```
Your AI client
     ↕  MCP stdio
This server (Python, on your machine)
     ↕  HTTPS
danepubliczne.imgw.pl
```

No cloud middle. No telemetry.

## Author

**Bartosz Kuć** — Warsaw-based developer, JDG owner running [skanfirmy.pl](https://skanfirmy.pl).

- GitHub: https://github.com/bartosz-kuc

- Email: firma@bartosza.pl

## Consulting

Available for consulting on Polish tax and business integrations (KSeF, GUS/NFZ/GIOŚ APIs, mBank data), MCP server design, and AI-assisted tooling for JDGs and small teams. See **[skanfirmy.pl/uslugi](https://skanfirmy.pl/uslugi)** for productized packages (audit 3k PLN, setup 8-15k PLN, retainer 2-4k PLN/mo), or reach out via email.

## License

MIT — see [LICENSE](LICENSE).

## Related

- Part of the honest-mcp family — see the [family index](https://github.com/bartosz-kuc?tab=repositories).
