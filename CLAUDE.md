# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Terminal User Interface (TUI) built with Python + Textual + SQLite for calculating peptide reconstitution dilutions, U-100 insulin syringe draws, titration schedules, multi-person patient protocol tracking, and dose-history/adherence logging, with PubMed literature citations. Research/educational tool — not medical advice (see README disclaimer).

## Commands

Uses `uv` for dependency management (Python >=3.13; runtime dependency: `textual`; dev dependency: `pytest`).

```bash
uv run python main.py     # Run the TUI application
uv run peptide-tui         # Same, via the installed console-script entry point
python main.py             # Run directly if venv is already active

python db.py                # Initialize/verify the SQLite schema standalone (creates peptides.db, prints confirmation)

uv run pytest               # Run the test suite (tests/test_calc.py, tests/test_db.py)
uv run pytest tests/test_calc.py -k test_bpc157_known_good_numbers  # Run a single test
```

There is no linter configured in this repo.

## Architecture

- **`main.py`** — `PeptideCalculatorApp(App)`, a single Textual `App` subclass containing all UI composition, CSS-in-Python styling, and event handlers, plus `ConfirmScreen(ModalScreen[bool])` for destructive-action confirmation, `TitrationGeneratorScreen(ModalScreen[list | None])` for generating a linear dose ramp (`calc.generate_titration_schedule`) and saving it into a protocol (`db.update_protocol_schedule`), and `VialSplitScreen(ModalScreen[None])` for a read-only what-if split of one reconstituted vial into equal storage aliquots (`calc.split_vial_aliquots`). Six tabs inside one `TabbedContent` (each `TabPane` has an explicit `id` — `calc-tab`, `patient-tab`, `schedule-tab`, `dose-log-tab`, `reference-tab`, `literature-tab` — used for programmatic tab switching):
  1. **Calculator & Syringe Visualizer** (`calc-tab`) — dilution math + ASCII syringe gauge (`make_syringe_display`), driven by reactive attributes; also launches `VialSplitScreen` from the current reactive vial/dose state.
  2. **Patient Tracker (Multi-Person)** (`patient-tab`) — profile switcher (add/remove) + `DataTable` of a patient's saved protocols, with edit-selected, log-dose, delete-selected, generate-titration-schedule (`TitrationGeneratorScreen`), and mark-reconstituted (starts the BUD window, resets vial inventory) actions — all requiring a selected row. Columns include "Vial BUD / Expiry" and "Doses Left".
  3. **Dosing Schedule Planner** (`schedule-tab`) — multi-phase titration table for the currently selected peptide, exportable to a text file.
  4. **Dose Log** (`dose-log-tab`) — adherence summary table (adherence state, BUD, doses left) + raw chronological dose-log table for the active profile, with edit-entry (`EditDoseScreen`) and delete-entry.
  5. **Peptide Reference & Cited Sources** (`reference-tab`) — read-only Rich/Static rendering of the master peptide database and PubMed citations, plus a per-peptide "Track N PMIDs" button that batch-fetches that peptide's cited sources into the Literature Tracker. Peptide names aren't valid widget ids (spaces, `/`, `+`), so those buttons are keyed by index through `self._reference_source_buttons` (id → peptide name), rebuilt on every `populate_reference_tab` call.
  6. **Literature Tracker** (`literature-tab`) — enter a PMID to fetch title/authors/abstract from NCBI E-utilities in the background (`ncbi.fetch_pubmed_article`, run via `self.run_worker(...)` so the UI doesn't block) and persist it to `db.tracked_literature`; `DataTable` of tracked articles with delete-selected, a peptide filter `Select` (only lists peptides that actually have tracked articles), and an abstract viewer that updates on row-highlight (`on_data_table_row_highlighted`, which reads the PMID from column index 1).

- **`db.py`** — all persistence. Owns `DEFAULT_PEPTIDES` (the seed data: vial size, water volume, target dose, titration schedule, PubMed sources per peptide) and every SQLite read/write function. `init_db()` creates five tables (`profiles`, `peptides`, `user_protocols`, `dose_log`, `tracked_literature`), runs idempotent migrations (ALTER-TABLE-guarded `created_at`/`reconstituted_at` adds on `user_protocols` and `peptide_name` on `tracked_literature`, a one-time peptide-name rename fix), and seeds master peptides via `INSERT OR IGNORE` on every startup — `main.py` calls `db.init_db()` at the top of `compose()`. `schedule` and `sources` are stored as JSON text columns and (de)serialized in Python; call sites work with them as native lists/dicts. Foreign keys are enforced (`PRAGMA foreign_keys = ON` in `get_connection()`), so deleting a profile cascades to its protocols and dose log. `tracked_literature` (PMID-tracked PubMed articles: title, authors_json, abstract, journal, pub_date, url) is upserted via `save_tracked_article` (`ON CONFLICT(pmid) DO UPDATE`), independent of any profile. `update_protocol_schedule(protocol_id, schedule, target_dose, dose_unit)` overwrites a protocol's `schedule_json` (e.g. from `TitrationGeneratorScreen`) and syncs `target_dose`/`dose_unit` to the new maintenance level.

- **`calc.py`** — pure functions, no I/O. The single source of truth for dosing math (`concentration_mg_ml`, `dose_to_mg`, `draw_volume_ml`, `syringe_units`, `doses_per_vial`) shared by `main.py`'s live calculator/schedule views and `db.py`'s file export — do not reinline this formula elsewhere. Also owns the adherence heuristic (`parse_weekly_frequency`, `adherence_percent`) used by `db.get_protocol_adherence`, `generate_titration_schedule` (linear dose ramp builder returning the same `(phase, dose, unit)` tuple shape as `DEFAULT_PEPTIDES["schedule"]`), `split_vial_aliquots` (per-aliquot mg/mL/concentration for splitting one reconstituted vial — concentration is unchanged by splitting, only reused via `concentration_mg_ml`), and the vial-lifecycle helpers (`bud_expiry_at`, `format_bud_label`, `bud_exceeded_by_duration`, `adherence_label`, `doses_remaining`, `format_doses_remaining`, `parse_dose_timestamp`).

- **`ncbi.py`** — pure NCBI E-utilities client, no Textual/db dependency. `validate_pmid` cleans/validates input; `fetch_pubmed_article_sync` calls `efetch.fcgi` (XML, with retry/backoff on 429/5xx) and `parse_pubmed_xml` extracts title/authors/abstract/journal/pub_date/doi/url; `fetch_pubmed_article` is the `asyncio.to_thread`-wrapped async entrypoint `main.py`'s worker awaits.

### Data flow / state model

- Core UI state lives in Textual `reactive` attributes on the App (`active_profile_id`, `peptide`, `vial_mg`, `water_ml`, `target_dose`, `dose_unit`). Changing an `Input`/`Select` updates the matching reactive, then handlers explicitly call `self.recalculate()` and `self.update_schedule_table()` — there's no automatic reactive-to-reactive derivation, so any new input field must call these itself.
- `watch_active_profile_id` re-renders the active-profile label, patient table, and dose-log tables whenever the profile changes.
- "Master" peptide templates (`db.peptides` table) are the read-only catalog; "Quick Add" or "Save Protocol" copies a template's values into a per-profile row in `user_protocols`, which is what the Patient Tracker tab and file exports actually read. Editing a template does not retroactively change already-saved patient protocols.
- `user_protocols` tracks the *planned* protocol; `dose_log` tracks *actual* logged doses (denormalized `peptide_name` snapshot, so history survives protocol edits/deletes). Adherence % is a best-effort heuristic (`calc.parse_weekly_frequency` regex-parses free-text frequency strings like `"3x weekly"`) — unparseable frequencies report `None` rather than guessing. `calc.adherence_label` turns that `None` into a *reason* ("Too new" vs "Freq. not recognized"), which is what the UI shows.
- Vial lifecycle: `user_protocols.reconstituted_at` (NULL = powder, not yet mixed) drives both the beyond-use date (`calc.bud_expiry_at`, default `calc.DEFAULT_BUD_DAYS` = 28) and vial inventory. Inventory counts only `dose_log` rows with `taken_at >= reconstituted_at`, so marking a protocol reconstituted again starts a fresh vial and resets "doses left" without touching dose history. Doses backdated to before the reconstitution date belong to the previous vial and are excluded by design.
- `db.log_dose(..., taken_at=None)` and `db.update_dose_log_entry` support back-dating and correcting doses; `calc.parse_dose_timestamp` validates the user-entered date (blank/"now" → None → SQLite `CURRENT_TIMESTAMP`, future dates rejected). dose_log timestamps are naive UTC strings, so entered dates are interpreted in that same frame.
- File exports (`db.export_person_reference_sheet`, `db.export_dose_log_csv`, `save_schedule_to_file` in `main.py`) write plain-text reports to the current working directory, not a fixed output folder. The patient summary export includes a trailing "Recent Dose Log" section.
- **Every name interpolated into an export filename must go through `calc.safe_filename_part`.** Profile names are user-entered and five catalog peptides contain `/` (including `Custom / Other`, the default calculator selection), so a raw name turns the filename into a path into a nonexistent directory. The export handlers in `main.py` also catch `OSError` and notify rather than letting it escape a button handler, which crashes the app.
- Calculator inputs are range-checked by `calc.validate_reconstitution_inputs` (bounds: `MAX_VIAL_MG`/`MAX_WATER_ML`/`MAX_DOSE_MG`, plus NaN/inf rejection) before any math runs; `recalculate()` shows the returned message instead of rendering nonsense like a 40-digit concentration.
- Schedule steps carry their own unit, which may differ from the protocol's `dose_unit` — convert with `calc.convert_dose` before mixing the two (the titration generator's prefill does this, otherwise it would be off by 1000x).
- `db.delete_user_protocol` nulls `dose_log.protocol_id` for the deleted protocol: log rows intentionally outlive their protocol, but `protocol_id` has no cascading FK so it would otherwise dangle.
- `Select.set_options()` always resets the widget's selection to blank — `refresh_peptide_templates()` explicitly restores a sensible value afterward. Any new code that calls `set_options()` on a `Select` needs the same treatment or the dropdown silently goes blank.
- Destructive actions (delete protocol/profile/dose-log-entry) route through `ConfirmScreen` via `self.push_screen(ConfirmScreen("..."), callback)` — reuse this pattern for future destructive actions rather than deleting on a single click.
- Programmatically switching `TabbedContent.active` right after a click also moves focus (e.g. `load_selected_protocol_for_edit` calls `self.set_focus(...)` after switching tabs) — `TabPane._on_descendant_focus` re-syncs `active` to whichever tab contains the currently-focused widget, so a stale-focused button in the old tab can silently revert the switch on the next message cycle if focus isn't also moved.

### Adding a new peptide

Add an entry to `DEFAULT_PEPTIDES` in `db.py` (vial_mg, water_ml, dose, unit, freq, notes, schedule tuples, PubMed sources) — it will be picked up by `INSERT OR IGNORE` on next run without a migration. Existing `peptides.db` files won't retroactively update an already-seeded row with the same name; delete/edit the row or the `.db` file if template values need correcting after seeding.
