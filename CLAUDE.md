# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Home Assistant HACS custom component for the **Acquasource i-Series** pool heat pump. It communicates with the [poolpump server](https://github.com/jeanfabrice/poolpump) — a Ruby/Rack process that bridges HTTP to the pump's Modbus TCP interface — running on the local network (default port 8090).

There are no tests, no build system, and no linter config in this repo. The component is pure Python loaded directly by Home Assistant.

## Development setup

Install the component into a local HA dev instance by symlinking or copying:

```bash
cp -r custom_components/poolpump ~/.homeassistant/custom_components/poolpump
```

Enable debug logging in `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.poolpump: debug
```

Regenerate `logo.png` / `icon.png` from the source SVG (requires `cairosvg`):

```bash
pip install cairosvg
python3 -c "
import cairosvg
cairosvg.svg2png(url='custom_components/poolpump/images/logo.svg',
                 write_to='custom_components/poolpump/brand/logo.png',
                 output_width=256, output_height=256)
"
```

## Releasing

The release workflow is fully automated via `.github/workflows/release.yml`.

**Stable release:**
```bash
git tag v0.x.y && git push origin v0.x.y
```

**Beta release (not shown by default in HACS):**
```bash
git tag v0.x.y-beta1 && git push origin v0.x.y-beta1
```

The workflow will:
1. Extract the version from the tag and update `manifest.json` automatically (committed back to `main`)
2. Create a GitHub release with auto-generated release notes
3. Mark it as pre-release if the tag contains `-beta`, `-rc`, or `-alpha`

Note: since HA 2026.3, brand images are served from `custom_components/poolpump/brand/` via the local brands API — no need to attach them as release assets.

## Architecture

All entities share a single `PoolPumpCoordinator` (a `DataUpdateCoordinator`) created in `__init__.py` at config-entry setup time. It polls two endpoints every 30 seconds:

- `GET /` → `snapshot` dict (20 fields) or `None` if the server returns HTTP 500 (Modbus module not yet connected)
- `GET /healthz` → `healthz` dict (`connected`, `queue_depth`)

The coordinator stores `{"snapshot": dict|None, "healthz": dict}` as its `.data`.

**Command flow:** entity action methods call `coordinator.async_send_command(verb)` which POSTs a plain-text verb to `/`. The POST response does not include a snapshot (`resultCode` is always 0), so the coordinator immediately re-fetches `GET /` and injects the result via `async_set_updated_data()` to refresh the UI without waiting for the next poll.

**`available` contract:** all entities return `False` when `snapshot is None` (server reachable but no Modbus telemetry yet). The climate entity additionally checks `snapshot.get("SWITCHED_ON") is not None` — use `is not None`, not truthiness, because `0` (pump off) is a valid value.

## Key mappings

**HVAC modes** (`STATUS_MODE` values: 1=heat, 2=auto, 4=cool):

| `SWITCHED_ON` | `STATUS_MODE` | HA `HVACMode` | POST command |
|---|---|---|---|
| 0 | — | `OFF` | `off` |
| 1 | 1 | `HEAT` | `setmode heat` |
| 1 | 2 | `AUTO` | `setmode auto` |
| 1 | 4 | `COOL` | `setmode cool` |

Switching from `OFF` to any active mode sends `on` first, then `setmode X`.

**Preset modes** (`BOOST`/`SILENCE` snapshot fields):

| `BOOST` | `SILENCE` | Preset | POST command |
|---|---|---|---|
| 0 | 0 | `auto` | `mode-auto` |
| 1 | 0 | `boost` | `mode-boost` |
| 0 | 1 | `silent` | `mode-silent` |

**Temperature:** use `set-target N` (not `settemp N`) — `settemp` has side effects (turns pump on, forces heat mode). Range: 15–32°C.

## API reference (poolpump server)

| Method | Path | Notes |
|---|---|---|
| `GET` | `/` | Snapshot JSON; HTTP 500 = no telemetry |
| `POST` | `/` | Plain-text verb; response `{resultCode, result, ...}` — no snapshot |
| `GET` | `/healthz` | Always 200; `{connected, queue_depth}` |

Valid POST verbs: `on`, `off`, `setmode heat\|auto\|cool`, `mode-boost`, `mode-silent`, `mode-auto`, `set-target N`.
