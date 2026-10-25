"""Tonie library persistence and safety tests without Home Assistant installed."""
import asyncio
import base64
import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest


class FakeStore:
    saved = {}

    def __init__(self, hass, version, key):
        self.key = key

    async def async_load(self):
        return copy.deepcopy(self.saved.get(self.key))

    async def async_save(self, value):
        self.saved[self.key] = copy.deepcopy(value)


events = []
modules = {
    "homeassistant": types.ModuleType("homeassistant"),
    "homeassistant.helpers": types.ModuleType("homeassistant.helpers"),
    "homeassistant.helpers.storage": types.ModuleType("homeassistant.helpers.storage"),
    "homeassistant.helpers.dispatcher": types.ModuleType("homeassistant.helpers.dispatcher"),
    "library_unit_pkg": types.ModuleType("library_unit_pkg"),
    "library_unit_pkg.const": types.ModuleType("library_unit_pkg.const"),
}
modules["homeassistant.helpers.storage"].Store = FakeStore
modules["homeassistant.helpers.dispatcher"].async_dispatcher_send = lambda hass, name, id: events.append((name, id))
modules["library_unit_pkg.const"].DOMAIN = "teddycloud_homeassistant"
sys.modules.update(modules)

path = Path(__file__).resolve().parents[1] / "custom_components" / "teddycloud_homeassistant" / "library.py"
spec = importlib.util.spec_from_file_location("library_unit_pkg.library", path)
library_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = library_module
spec.loader.exec_module(library_module)


class TestLibrary(unittest.TestCase):
    def setUp(self):
        FakeStore.saved = {}
        events.clear()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.hass = types.SimpleNamespace(
            config=types.SimpleNamespace(
                path=lambda *parts: str(Path(self.temp.name).joinpath(*parts))
            )
        )

    async def load(self):
        item = library_module.TonieLibrary(self.hass)
        await item.async_load()
        return item

    def test_collect_edit_delete_and_rediscover(self):
        async def run():
            lib = await self.load()
            await lib.async_seen("box1", "123456", title="Mein Hörspiel")
            self.assertEqual(lib.public_entries()[0]["title"], "Mein Hörspiel")
            await lib.async_metadata("123456", title="Aktueller Katalogtitel",duration=1800)
            await lib.async_edit("123456", title="Mein Titel", duration_seconds=2100,
                                 image="https://example.test/image.jpg")
            self.assertEqual(lib.public_entries()[0]["title"], "Mein Titel")
            self.assertEqual(lib.custom_metadata("123456")["duration_seconds"], 2100)
            self.assertEqual(lib.public_entries()[0]["image"], "https://example.test/image.jpg")
            # Library survives Home Assistant restart.
            lib = await self.load()
            self.assertEqual(len(lib.public_entries()), 1)
            await lib.async_delete("123456")
            self.assertEqual(lib.public_entries(), [])
            await lib.async_metadata("123456", title="Should not resurrect")
            self.assertEqual(lib.public_entries(), [])
            # New HA startup gets a retained/unchanged ID: stay deleted.
            lib = await self.load()
            await lib.async_seen("box1", "123456", title="Still old content")
            self.assertEqual(lib.public_entries(), [])
            # Physically removing and replacing the same figure recovers it.
            lib.box_cleared("box1")
            await lib.async_seen("box1", "123456", title="Back again")
            self.assertEqual(len(lib.public_entries()), 1)
            self.assertEqual(lib.public_entries()[0]["title"], "Back again")
        asyncio.run(run())

    def test_suppressed_id_recovers_after_another_figure(self):
        async def run():
            lib = await self.load()
            await lib.async_seen("box1", "first")
            await lib.async_delete("first")
            await lib.async_seen("box1", "another")
            await lib.async_seen("box1", "first")
            self.assertEqual(len(lib.public_entries()), 2)
            # Repeat the same MQTT state must not increase visits.
            await lib.async_seen("box1", "first")
            self.assertEqual(next(e for e in lib.public_entries() if e["audio_id"] == "first")["times_seen"],1)
        asyncio.run(run())

    def test_safe_image_upload_and_validation(self):
        async def run():
            lib = await self.load()
            image = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
            encoded = "data:image/png;base64," + base64.b64encode(image).decode()
            item = await lib.async_edit("3456", title="Foto", image_data=encoded)
            self.assertTrue(item["image"].startswith("/local/teddycloud_homeassistant/library/3456.png"))
            disk = Path(self.temp.name) / "www/teddycloud_homeassistant/library/3456.png"
            self.assertEqual(disk.read_bytes(), image)
            for invalid in (
                "data:image/svg+xml;base64," + base64.b64encode(b"<svg/>").decode(),
                "data:image/png;base64,AA==",
                "data:image/png;base64,not base64",
            ):
                with self.assertRaises(ValueError):
                    await lib.async_edit("3456", image_data=invalid)
            with self.assertRaises(ValueError):
                await lib.async_edit("../oops", title="bad")
            with self.assertRaises(ValueError):
                await lib.async_edit("3456", image="javascript:alert(1)")
            with self.assertRaises(ValueError):
                await lib.async_edit("3456", duration_seconds=1000000)
            await lib.async_delete("3456")
            self.assertFalse(disk.exists())
        asyncio.run(run())

    def test_separate_boxes_share_one_library(self):
        async def run():
            lib = await self.load()
            await lib.async_seen("boxA", "42", title="Gemeinsam")
            await lib.async_seen("boxB", "42")
            self.assertEqual(len(lib.public_entries()), 1)
            self.assertEqual(lib.public_entries()[0]["times_seen"], 2)
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
