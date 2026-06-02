# Pool Pump — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![HA version](https://img.shields.io/badge/Home%20Assistant-2024.1.0%2B-blue.svg)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A Home Assistant custom component to control a pool heat pump via the [poolpump](https://github.com/thomaswitt/poolpump) server. Any heat pump supported by that server (Modbus TCP interface) can be controlled through this integration.

---

## Prerequisites

- A pool heat pump with a Modbus TCP interface, supported by the poolpump server
- The [poolpump](https://github.com/thomaswitt/poolpump) server running on your local network (default port: `8090`)
- Home Assistant 2024.1.0 or later

## Installation via HACS

1. Open **HACS** → **Integrations** → click the **⋮** menu → **Custom repositories**
2. Add `https://github.com/jeanfabrice/homeassistant-poolpump` as type **Integration**
3. Search for **Pool Pump** and click **Download**
4. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **Pool Pump**
3. Enter the URL of your poolpump server (e.g. `http://192.168.1.42:8090`)
4. Optionally toggle SSL certificate verification (enabled by default)

The integration will validate the connection before saving.

## Entities

### Climate

| Entity | Description |
|--------|-------------|
| `climate.pool_pump` | Main control entity: HVAC mode, preset, and target temperature |

**HVAC modes:** `off`, `heat`, `auto`, `cool`

**Preset modes:**

| Preset | Description |
|--------|-------------|
| `auto` | Normal operation |
| `boost` | Maximum compressor output |
| `silent` | Reduced noise / reduced compressor speed |

**Temperature:** 15 °C – 32 °C (1 °C steps)

### Sensors

| Entity | Unit | Description |
|--------|------|-------------|
| `sensor.pool_pump_inlet_water_temperature` | °C | Water temperature at pump inlet |
| `sensor.pool_pump_outlet_water_temperature` | °C | Water temperature at pump outlet |
| `sensor.pool_pump_ambient_temperature` | °C | Ambient air temperature |
| `sensor.pool_pump_compressor_frequency` | Hz | Compressor operating frequency |
| `sensor.pool_pump_compressor_load` | % | Compressor load |
| `sensor.pool_pump_ac_voltage` | V | AC supply voltage |
| `sensor.pool_pump_motor_current` | A | Motor current draw |
| `sensor.pool_pump_dc_link_voltage` | V | DC link voltage |
| `sensor.pool_pump_dc_link_current` | A | DC link current |
| `sensor.pool_pump_max_input_power` | W | Factory-rated maximum input power (diagnostic) |

### Binary Sensors

| Entity | Class | Description |
|--------|-------|-------------|
| `binary_sensor.pool_pump_water_pump` | Running | Whether the circulation pump is running |
| `binary_sensor.pool_pump_module_connected` | Connectivity | Whether the Modbus module is connected (diagnostic) |

## Troubleshooting

**Entities show as unavailable**

- Check that the poolpump server is reachable at the configured URL
- If the server is reachable but entities are still unavailable, the Modbus module may not be connected yet — wait a few seconds and check the `module_connected` binary sensor

**Enable debug logging**

Add the following to your `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.poolpump: debug
```

---

## Credits

This integration is built on top of the [poolpump](https://github.com/thomaswitt/poolpump) server created by **Thomas Witt**, which bridges HTTP to the Modbus TCP interface of pool heat pumps. His original work and write-up are described in the article [How to free a pool heat pump from an unencrypted Chinese server](https://thomas-witt.com/blog/how-to-free-a-pool-heat-pump-from-an-unencrypted-chinese-server/).

This Home Assistant plugin was entirely written with [Claude](https://claude.ai) by Anthropic.

## License

[MIT](LICENSE)
