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
modules["library_unit_pkg.const"].CONF_BOX_COLOR = "box_color"
modules["library_unit_pkg.const"].CONF_BOX_NAME = "box_name"
modules["library_unit_pkg.const"].DEFAULT_COLOR = "#8f77c7"
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
            await lib.async_seen("box1", "123456", title="Still old content", retained=True)
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

    def test_new_live_placement_on_other_box_recovers_deleted_figure(self):
        async def run():
            lib = await self.load()
            await lib.async_seen("boxA", "777")
            await lib.async_delete("777")
            # Same content on boxA doesn't revive the deleted record.
            await lib.async_seen("boxA", "777")
            self.assertEqual(len(lib.public_entries()), 0)
            # The retained message at a new subscriber isn't a new placement.
            await lib.async_seen("boxB", "777", retained=True)
            self.assertEqual(len(lib.public_entries()), 0)
            # But a genuinely new live MQTT event from boxC is.
            await lib.async_seen("boxC", "777", retained=False)
            self.assertEqual(len(lib.public_entries()), 1)
        asyncio.run(run())

    def test_system_sounds_excluded_in_all_library_views_and_after_restart(self):
        async def run():
            lib = await self.load()
            for index, title in enumerate((
                "System sounds de-de - Jingle (Startup)",
                "System sounds en-gb - Jingle (Shutdown)",
                " SYSTEM SOUNDS fr-fr - Signal ",
                "System sounds - Warning",
            )):
                await lib.async_seen("box", str(index), title=title)
            await lib.async_seen("box", "real", title="Mein Hörspiel")
            self.assertEqual([e["audio_id"] for e in lib.public_entries()], ["real"])
            self.assertEqual([e["audio_id"] for e in lib.entries()], ["real"])
            # Existing storage is filtered without having to delete every sound.
            lib = await self.load()
            self.assertEqual([e["audio_id"] for e in lib.public_entries()], ["real"])
            lib.box_cleared("box")
            await lib.async_seen("box", "0", title="System sounds de-de - Jingle (Startup)")
            self.assertEqual(len(lib.public_entries()), 1)
            await lib.async_edit("0", title="Renamed startup sound")
            self.assertEqual(len(lib.public_entries()), 1)
        asyncio.run(run())

    def test_late_titles_filter_sounds_without_permanently_blocking_real_figures(self):
        async def run():
            lib = await self.load()
            await lib.async_seen("box", "123")
            await lib.async_metadata("123", title="System sounds de-de - Jingle (Startup)")
            self.assertEqual(lib.public_entries(), [])
            # A title from the previous sound may arrive before the new figure's
            # ID; subsequent metadata must recover the real figure, not blacklist it.
            await lib.async_metadata("123", title="Der kleine Rabe Socke")
            self.assertEqual(lib.public_entries()[0]["title"], "Der kleine Rabe Socke")
            for index, title in enumerate(("Startup", "Jingle Bells", "System Sounds of Nature", "Unbekannter Tonie")):
                await lib.async_seen("box", f"figure{index}", title=title)
            self.assertEqual(len(lib.public_entries()), 5)
        asyncio.run(run())

    def test_frequency_aliases_custom_data_and_group_delete(self):
        async def run():
            lib = await self.load()
            await lib.async_seen("red", "111", title="Same episode", box_color="#D82F38")
            await lib.async_edit("111", title="My title", image="https://example.test/my.png")
            await lib.async_seen("blue", "222", title="Same episode", box_color="#78C9E5")
            await lib.async_edit("222", duration_seconds=2400)
            await lib.async_seen("red", "333", title="Different episode")
            # Same title alone never merges two records.
            self.assertEqual(len(lib.public_entries()), 3)
            await lib.async_metadata("111", audio_ids=["111", "222"])
            items = lib.public_entries()
            self.assertEqual(len(items), 2)
            self.assertEqual(items[0]["times_seen"], 2)
            self.assertEqual(items[0]["title"], "My title")
            self.assertEqual(items[0]["image"], "https://example.test/my.png")
            self.assertEqual(items[0]["duration_seconds"], 2400)
            self.assertEqual(len(lib._entries), 3)  # Lossless projection.
            self.assertEqual(items[0]["last_heard_boxes"][0]["box_id"], "blue")
            lib = await self.load()
            self.assertEqual(lib.public_entries()[0]["times_seen"], 2)
            await lib.async_edit("111", title="Updated")
            self.assertEqual(lib.custom_metadata("222")["title"], "Updated")
            await lib.async_delete("111")
            self.assertEqual([x["audio_id"] for x in lib.public_entries()], ["333"])
            lib = await self.load()
            await lib.async_seen("new", "222", retained=True)
            self.assertEqual(len(lib.public_entries()), 1)
        asyncio.run(run())

    def test_last_box_colors_retained_messages_and_system_sounds(self):
        async def run():
            lib = await self.load()
            await lib.async_seen("red", "111", title="Real", box_color="#D82F38")
            await lib.async_seen("blue", "111", title="Real", box_color="#78C9E5")
            await lib.async_seen("red", "sound", title="System sounds de-de - Jingle (Startup)")
            lib = await self.load()
            await lib.async_seen("red", "111", retained=True)
            item = lib.public_entries()[0]
            self.assertEqual(item["times_seen"], 2)
            self.assertEqual(len(item["last_heard_boxes"]), 2)
            self.hass.config_entries = types.SimpleNamespace(async_entries=lambda domain: [
                types.SimpleNamespace(entry_id="red", data={"box_name":"Bedroom", "box_color":"#D82F38"}, options={"box_color":"#123456"})
            ])
            boxes = {b["box_id"]: b for b in lib.public_entries()[0]["last_heard_boxes"]}
            self.assertEqual(boxes["red"]["color"], "#123456")
            self.assertEqual(boxes["red"]["name"], "Bedroom")
        asyncio.run(run())

    def test_catalog_backfills_existing_aliases(self):
        async def run():
            lib = await self.load()
            await lib.async_edit("111", title="Own title")
            await lib.async_edit("222", image="https://example.test/own.png")
            class Catalog:
                async def find(self, audio_id):
                    return {"catalog_title":"Episode", "audio_ids":["111", "222"]}
            await lib.async_refresh_catalog(Catalog())
            self.assertEqual(len(lib.public_entries()), 1)
            self.assertEqual(lib.public_entries()[0]["title"], "Own title")
            self.assertEqual(lib.public_entries()[0]["image"], "https://example.test/own.png")
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

    def test_group_uses_known_title_when_first_alias_has_none(self):
        async def run():
            lib = await self.load()
            await lib.async_seen('box', '123')
            await lib.async_seen('box', '456', title='Yakari')
            await lib.async_metadata('456', audio_ids=['123', '456'])
            self.assertEqual(lib.public_entries()[0]['title'], 'Yakari')
            await lib.async_edit('123', title='Mein Yakari')
            self.assertEqual(lib.public_entries()[0]['title'], 'Mein Yakari')
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
