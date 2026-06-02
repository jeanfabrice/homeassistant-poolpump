"""DataUpdateCoordinator for the Pool Pump integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class PoolPumpCoordinator(DataUpdateCoordinator):
    """Polls GET / and GET /healthz every SCAN_INTERVAL_SECONDS seconds."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        verify_ssl: bool,
        session: aiohttp.ClientSession,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self._host = host.rstrip("/")
        self._verify_ssl = verify_ssl
        self._session = session

    async def _async_update_data(self) -> dict:
        try:
            async with asyncio.timeout(10):
                snapshot = await self._fetch_snapshot()
                healthz = await self._fetch_healthz()
                return {"snapshot": snapshot, "healthz": healthz}
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"HTTP error communicating with poolpump: {err}") from err
        except TimeoutError as err:
            raise UpdateFailed("Timeout connecting to poolpump server") from err

    async def _fetch_snapshot(self) -> dict | None:
        """GET /. Returns None when server responds 500 (no Modbus telemetry yet)."""
        resp = await self._session.get(
            f"{self._host}/",
            ssl=self._verify_ssl,
        )
        if resp.status == 500:
            _LOGGER.debug("poolpump: no telemetry yet (HTTP 500)")
            return None
        resp.raise_for_status()
        return await resp.json()

    async def _fetch_healthz(self) -> dict:
        """GET /healthz. Degrades gracefully — always returns a dict."""
        try:
            resp = await self._session.get(
                f"{self._host}/healthz",
                ssl=self._verify_ssl,
            )
            resp.raise_for_status()
            return await resp.json()
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("poolpump: healthz fetch failed: %s", err)
            return {"connected": False, "queue_depth": 0}

    async def async_send_command(self, verb: str) -> dict:
        """POST / with a plain-text verb, then poll until the snapshot changes."""
        async with asyncio.timeout(10):
            resp = await self._session.post(
                f"{self._host}/",
                data=verb,
                headers={"Content-Type": "text/plain"},
                ssl=self._verify_ssl,
            )
            resp.raise_for_status()
            result = await resp.json()

        _LOGGER.debug("poolpump: command %r → resultCode=%s", verb, result.get("resultCode"))

        current = self.data or {}
        before = current.get("snapshot") or {}

        # The snapshot embedded in the POST response reflects the state before
        # Modbus applies the command. Poll GET / until the snapshot diverges
        # from the pre-command state, so the UI updates as soon as the pump
        # acknowledges the change (typically within 1–2 seconds).
        snapshot = await self._poll_until_changed(before)

        self.async_set_updated_data({
            "snapshot": snapshot,
            "healthz": current.get("healthz", {}),
        })

        return result

    async def _poll_until_changed(
        self,
        before: dict,
        *,
        attempts: int = 8,
        interval: float = 0.75,
    ) -> dict | None:
        """GET / repeatedly until the snapshot differs from before, or give up."""
        for i in range(attempts):
            await asyncio.sleep(interval)
            snapshot = await self._fetch_snapshot()
            if snapshot != before:
                _LOGGER.debug("poolpump: snapshot changed after %ds", int((i + 1) * interval))
                return snapshot
            _LOGGER.debug("poolpump: snapshot unchanged, retry %d/%d", i + 1, attempts)
        _LOGGER.debug("poolpump: snapshot did not change after %ds, using last fetch", int(attempts * interval))
        return snapshot
