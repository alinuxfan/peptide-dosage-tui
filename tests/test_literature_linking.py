import asyncio

from textual.widgets import Button, DataTable, Select

import db
from main import PeptideCalculatorApp


def _isolate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test_peptides.db"))


def _column_labels(table):
    return [str(col.label) for col in table.columns.values()]


def test_literature_table_shows_peptide_and_filter_narrows_rows(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            db.save_tracked_article("111", "A", ["Author A"], "abs A", peptide_name="Semax")
            db.save_tracked_article("222", "B", ["Author B"], "abs B", peptide_name="Semax")
            db.save_tracked_article("333", "C", ["Author C"], "abs C", peptide_name="Selank")
            app.refresh_literature_peptide_filter()
            app.refresh_literature_table()
            app.action_switch_tab("literature-tab")
            await pilot.pause()

            table = app.query_one("#literature-table", DataTable)
            assert "Peptide" in _column_labels(table)
            assert table.row_count == 3

            filter_select = app.query_one("#literature-peptide-filter", Select)
            values = [v for _, v in filter_select._options if isinstance(v, str)]
            assert "__all__" in values and "Semax" in values and "Selank" in values

            filter_select.value = "Semax"
            await pilot.pause()
            assert table.row_count == 2

            filter_select.value = "Selank"
            await pilot.pause()
            assert table.row_count == 1

            filter_select.value = "__all__"
            await pilot.pause()
            assert table.row_count == 3

    asyncio.run(run())


def test_reference_tab_offers_track_sources_button_per_peptide(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            app.action_switch_tab("reference-tab")
            app.populate_reference_tab("Semax")
            await pilot.pause()

            # One generated button, mapped back to the peptide it tracks for.
            assert "Semax" in app._reference_source_buttons.values()
            btn_id = next(k for k, v in app._reference_source_buttons.items() if v == "Semax")
            button = app.query_one(f"#{btn_id}", Button)
            assert "Track" in str(button.label)

    asyncio.run(run())


def test_filter_drops_peptides_with_no_tracked_articles(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            db.save_tracked_article("111", "A", ["Author A"], "abs A", peptide_name="Semax")
            app.refresh_literature_peptide_filter()
            await pilot.pause()

            filter_select = app.query_one("#literature-peptide-filter", Select)
            values = [v for _, v in filter_select._options if isinstance(v, str)]
            assert values == ["__all__", "Semax"]

            article = db.get_tracked_article_by_pmid("111")
            db.delete_tracked_article(article["id"])
            app.refresh_literature_peptide_filter()
            await pilot.pause()

            values = [v for _, v in filter_select._options if isinstance(v, str)]
            assert values == ["__all__"]
            assert str(filter_select.value) == "__all__"

    asyncio.run(run())
