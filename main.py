import os
import sys
from datetime import datetime, timezone
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, Horizontal, Grid, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import (
    Header,
    Footer,
    Input,
    Label,
    Button,
    Select,
    SelectionList,
    Static,
    DataTable,
    TabbedContent,
    TabPane,
)
from textual.reactive import reactive

import calc
import db
import ncbi

# Compact ASCII syringe drawing helper
def make_syringe_display(units: float) -> str:
    BARREL_WIDTH = 40  # character width of the barrel gauge
    BARREL_START = len("Needle ──┨ ")  # column where the barrel content begins

    if units <= 0:
        filled = 0
    elif units > 100:
        filled = BARREL_WIDTH  # Cap at 100 units visually
    else:
        filled = int(round((units / 100.0) * BARREL_WIDTH))

    empty = BARREL_WIDTH - filled

    stick_len = max(0, filled - 1)
    stick = "=" * stick_len
    rubber = "█" if filled > 0 else ""
    liquid = "░" * max(0, filled - stick_len - 1)
    barrel_content = f"{stick}{rubber}{liquid}{'.' * empty}"

    # Build the ruler so its tick marks line up with the same BARREL_START +
    # units-to-column scale used by the marker below, instead of a fixed
    # string that drifted out of sync with the barrel width.
    ruler_chars = [" "] * BARREL_START
    for label_units in (0, 20, 40, 60, 80, 100):
        pos = BARREL_START + round(label_units / 100.0 * BARREL_WIDTH)
        label = str(label_units)
        if pos + len(label) > len(ruler_chars):
            ruler_chars.extend([" "] * (pos + len(label) - len(ruler_chars)))
        ruler_chars[pos:pos + len(label)] = label
    top_line = "".join(ruler_chars) + " Units"

    mid_line = f"Needle ──┨ {barrel_content} ┠─════ Plunger"

    marker_pos = BARREL_START + filled
    bottom_line = " " * marker_pos + f"▲ {units:.1f}U"
    if units > 100:
        bottom_line += " [!] EXCEEDS 1mL CAPACITY"

    return f"{top_line}\n{mid_line}\n{bottom_line}"


CSS = """
Screen {
    background: #0f172a;
    color: #e2e8f0;
}

Header {
    background: #1e293b;
    color: #38bdf8;
    text-align: center;
    height: 1;
    border-bottom: solid #38bdf8;
}

Footer {
    background: #1e293b;
    color: #cbd5e1;
    dock: bottom;
    height: 1;
}

FooterKey {
    background: #334155;
    color: #38bdf8;
    text-style: bold;
}

FooterLabel {
    color: #cbd5e1;
}

TabbedContent {
    margin-top: 0;
    height: 1fr;
}

TabPane {
    padding: 0;
    height: 1fr;
}

.pane-container {
    layout: grid;
    grid-size: 2;
    grid-columns: 1fr 1fr;
    grid-gutter: 1;
    padding: 0 1;
    height: 1fr;
}

.sidebar-panel {
    background: #1e293b;
    border: solid #334155;
    padding: 0 1;
    height: 1fr;
}

.results-panel {
    background: #1e293b;
    border: solid #334155;
    padding: 0 1;
    layout: vertical;
    height: 1fr;
}

.title-label {
    color: #38bdf8;
    text-style: bold;
    margin-bottom: 0;
    border-bottom: solid #334155;
}

.input-label {
    text-style: bold;
    margin-top: 1;
    color: #cbd5e1;
}

.preset-row {
    layout: horizontal;
    height: 3;
    margin-bottom: 0;
    margin-top: 0;
}

.preset-row Button {
    margin-right: 1;
    min-width: 6;
    height: 3;
    background: #334155;
    color: #f1f5f9;
}

.preset-row Button:hover {
    background: #475569;
}

Input {
    background: #0f172a;
    border: solid #475569;
    color: #f1f5f9;
    margin-bottom: 0;
    height: 3;
}

Select {
    margin-bottom: 0;
    height: 3;
}

SelectCurrent {
    background: #0f172a;
    border: solid #38bdf8;
    color: #38bdf8;
    text-style: bold;
    height: 3;
}

.result-row {
    layout: horizontal;
    height: 2;
    content-align: left middle;
    border-bottom: solid #334155;
}

.result-label {
    width: 24;
    text-style: bold;
    color: #94a3b8;
}

.result-val {
    color: #f8fafc;
    text-style: bold;
}

#syringe-visual {
    background: #0f172a;
    border: double #38bdf8;
    padding: 0 1;
    margin-top: 0;
    margin-bottom: 0;
    height: 5;
    color: #38bdf8;
}

.help-box {
    background: #1e293b;
    border: solid #334155;
    padding: 0 1;
    margin-top: 0;
    color: #94a3b8;
}

.action-bar {
    layout: horizontal;
    height: 3;
    align: right middle;
    padding: 0 1;
    background: #1e293b;
    border-bottom: solid #334155;
}

.global-profile-bar {
    layout: horizontal;
    height: 3;
    align: left middle;
    padding: 0 1;
    background: #1e293b;
    border-bottom: solid #38bdf8;
}

.global-profile-bar .action-title {
    margin-right: 1;
}

.patient-controls-bar {
    layout: vertical;
    padding: 0 1;
    background: #1e293b;
    border-bottom: solid #334155;
    height: 10;
}

.control-row {
    layout: horizontal;
    height: 3;
    align: left middle;
    margin-bottom: 0;
}

#profile-select {
    width: 25;
    margin-right: 1;
}

#patient-add-peptide-select {
    width: 25;
    margin-right: 1;
}

#new-profile-input {
    width: 22;
    margin-right: 1;
}

#schedule-protocol-select {
    width: 48;
    margin-right: 1;
}

.schedule-controls-bar {
    layout: vertical;
    padding: 0 1;
    background: #1e293b;
    border-bottom: solid #334155;
    height: auto;
}

.schedule-banner-row {
    layout: horizontal;
    align: left middle;
    background: #0f172a;
    border: solid #334155;
    padding: 0 1;
    margin-top: 1;
    margin-bottom: 1;
    height: 3;
}

#schedule-banner-text {
    color: #38bdf8;
    text-style: bold;
}

.action-title {
    color: #38bdf8;
    text-style: bold;
    margin-right: 1;
}

DataTable {
    height: 1fr;
    border: solid #334155;
    background: #0f172a;
    margin: 0 1;
}

.info-pane {
    padding: 1 2;
    height: 100%;
}

.info-section {
    background: #1e293b;
    border: solid #334155;
    padding: 1 2;
    margin-bottom: 1;
    height: auto;
}

.info-title {
    color: #38bdf8;
    text-style: bold;
    margin-bottom: 1;
}

.info-text {
    color: #cbd5e1;
    margin-bottom: 1;
    height: auto;
}

.source-link {
    color: #38bdf8;
    margin-left: 2;
    margin-bottom: 1;
    height: auto;
}

#save-target-profiles {
    height: 6;
    border: solid #334155;
    background: #0f172a;
    margin-bottom: 1;
}

#save-profile-protocol-btn {
    background: #38bdf8;
    color: #0f172a;
    text-style: bold;
    margin-top: 1;
    height: 3;
}

#save-schedule-btn, #export-patient-sheet-btn, #export-dose-log-csv-btn {
    background: #10b981;
    color: #0f172a;
    text-style: bold;
    min-width: 24;
    margin-left: 1;
    height: 3;
}

#add-profile-btn, #quick-add-peptide-btn {
    background: #38bdf8;
    color: #0f172a;
    text-style: bold;
    min-width: 16;
    margin-left: 1;
    height: 3;
}

#delete-protocol-btn, #remove-profile-btn, #delete-log-btn {
    background: #f43f5e;
    color: #ffffff;
    text-style: bold;
    min-width: 18;
    margin-left: 1;
    height: 3;
}

#edit-protocol-btn, #log-dose-btn, #view-schedule-btn {
    background: #38bdf8;
    color: #0f172a;
    text-style: bold;
    min-width: 16;
    margin-left: 1;
    height: 3;
}

#adherence-table {
    height: 10;
    margin: 0 1;
}
"""

CONFIRM_CSS = """
ConfirmScreen {
    align: center middle;
}

#confirm-dialog {
    width: 60;
    height: auto;
    background: #1e293b;
    border: solid #f43f5e;
    padding: 1 2;
}

#confirm-message {
    color: #f1f5f9;
    margin-bottom: 1;
    height: auto;
}

#confirm-buttons {
    layout: horizontal;
    height: 3;
    align: right middle;
}

#confirm-buttons Button {
    margin-left: 1;
    min-width: 10;
}

#confirm-yes {
    background: #f43f5e;
    color: #ffffff;
}

#confirm-no {
    background: #334155;
    color: #f1f5f9;
}
"""

LOG_DOSE_CSS = """
LogDoseScreen {
    align: center middle;
}

#logdose-dialog {
    width: 60;
    height: auto;
    background: #1e293b;
    border: solid #38bdf8;
    padding: 1 2;
}

#logdose-message {
    color: #f1f5f9;
    margin-bottom: 1;
    height: auto;
}

#logdose-notes {
    margin-bottom: 1;
}

#logdose-buttons {
    layout: horizontal;
    height: 3;
    align: right middle;
}

#logdose-buttons Button {
    margin-left: 1;
    min-width: 10;
}

#logdose-yes {
    background: #38bdf8;
    color: #0f172a;
}

#logdose-no {
    background: #334155;
    color: #f1f5f9;
}
"""


class ConfirmScreen(ModalScreen[bool]):
    """A simple Yes/No confirmation modal. Dismisses with True (confirmed) or False (cancelled)."""

    CSS = CONFIRM_CSS
    BINDINGS = [Binding("escape", "cancel", show=False)]

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Container(id="confirm-dialog"):
            yield Label(self.message, id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button("Cancel", id="confirm-no")
                yield Button("Confirm", id="confirm-yes")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(event.button.id == "confirm-yes")

    def action_cancel(self) -> None:
        self.dismiss(False)


class LogDoseScreen(ModalScreen[str | None]):
    """Prompts for optional notes (injection site, side effects, etc.) when logging
    a dose. Dismisses with the entered notes string on confirm, or None on cancel."""

    CSS = LOG_DOSE_CSS
    BINDINGS = [Binding("escape", "cancel", show=False)]

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Container(id="logdose-dialog"):
            yield Label(self.message, id="logdose-message")
            yield Input(placeholder="Notes (injection site, side effects, etc.) - optional", id="logdose-notes")
            with Horizontal(id="logdose-buttons"):
                yield Button("Cancel", id="logdose-no")
                yield Button("Log Dose", id="logdose-yes")

    def on_mount(self) -> None:
        self.query_one("#logdose-notes", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "logdose-yes":
            self.dismiss(self.query_one("#logdose-notes", Input).value.strip())
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self.dismiss(event.value.strip())

    def action_cancel(self) -> None:
        self.dismiss(None)


HELP_CSS = """
HelpScreen {
    align: center middle;
}

#help-dialog {
    width: 74;
    height: auto;
    background: #1e293b;
    border: solid #38bdf8;
    padding: 1 2;
}

#help-title {
    color: #38bdf8;
    text-style: bold;
    margin-bottom: 1;
    text-align: center;
}

.help-cmd-row {
    layout: horizontal;
    height: 1;
    margin-bottom: 0;
}

.help-cmd-key {
    width: 20;
    color: #38bdf8;
    text-style: bold;
}

.help-cmd-desc {
    color: #e2e8f0;
}

#help-close-btn {
    margin-top: 1;
    background: #38bdf8;
    color: #0f172a;
    text-style: bold;
    width: 100%;
}
"""


class HelpScreen(ModalScreen[None]):
    """Modal displaying all keyboard commands and shortcuts."""

    CSS = HELP_CSS
    BINDINGS = [
        Binding("escape", "dismiss_help", show=False),
        Binding("enter", "dismiss_help", show=False),
        Binding("question_mark", "dismiss_help", show=False),
    ]

    def compose(self) -> ComposeResult:
        shortcuts = [
            ("1 / F1", "Calculator & Syringe Visualizer tab"),
            ("2 / F2", "Patient Tracker (Multi-Person) tab"),
            ("3 / F3", "Dosing Schedule Planner tab"),
            ("4 / F4", "Dose Log & Adherence History tab"),
            ("5 / F5", "Peptide Reference & PubMed Citations tab"),
            ("6 / F6", "Literature Tracker tab (fetch article by PMID)"),
            ("Ctrl+P", "Cycle active patient / person profile"),
            ("Ctrl+S", "Save current schedule to text file"),
            ("Ctrl+L", "Quick-log dose for active protocol"),
            ("Tab / Shift+Tab", "Navigate between inputs, buttons & tables"),
            ("Space / Enter", "Select dropdown option / activate button"),
            ("? / F12", "Toggle this keyboard shortcuts help"),
            ("Ctrl+Q", "Quit application"),
        ]

        with Container(id="help-dialog"):
            yield Label("⌨️  KEYBOARD COMMANDS & SHORTCUTS", id="help-title")
            for key, desc in shortcuts:
                with Horizontal(classes="help-cmd-row"):
                    yield Label(key, classes="help-cmd-key")
                    yield Label(f"• {desc}", classes="help-cmd-desc")
            yield Button("Close (Esc)", id="help-close-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(None)

    def action_dismiss_help(self) -> None:
        self.dismiss(None)


class PeptideCalculatorApp(App):
    TITLE = "Peptide Dosage & Reconstitution TUI"
    SUB_TITLE = "Multi-Person Protocol Tracker with Scientific Citations"
    CSS = CSS
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("1", "switch_tab('calc-tab')", "Calc", show=True),
        Binding("2", "switch_tab('patient-tab')", "Patients", show=True),
        Binding("3", "switch_tab('schedule-tab')", "Schedule", show=True),
        Binding("4", "switch_tab('dose-log-tab')", "Dose Log", show=True),
        Binding("5", "switch_tab('reference-tab')", "Ref", show=True),
        Binding("6", "switch_tab('literature-tab')", "Lit Tracker", show=True),
        Binding("ctrl+p", "next_profile", "Next Person", show=True),
        Binding("ctrl+s", "save_schedule", "Save Schedule", show=True),
        Binding("ctrl+l", "quick_log_dose", "Log Dose", show=True),
        Binding("question_mark", "show_help", "Help", show=True),
        Binding("ctrl+q", "quit", "Quit", show=True),
        # Secondary convenience shortcuts
        Binding("f1", "switch_tab('calc-tab')", "Calc", show=False),
        Binding("f2", "switch_tab('patient-tab')", "Patients", show=False),
        Binding("f3", "switch_tab('schedule-tab')", "Schedule", show=False),
        Binding("f4", "switch_tab('dose-log-tab')", "Dose Log", show=False),
        Binding("f5", "switch_tab('reference-tab')", "Ref", show=False),
        Binding("f6", "switch_tab('literature-tab')", "Lit Tracker", show=False),
        Binding("f12", "show_help", "Help", show=False),
        Binding("q", "quit", "Quit", show=False),
    ]

    active_profile_id = reactive(1)
    peptide = reactive("Custom / Other")
    vial_mg = reactive(5.0)
    water_ml = reactive(2.0)
    target_dose = reactive(250.0)
    dose_unit = reactive("mcg")

    def compose(self) -> ComposeResult:
        db.init_db()
        yield Header()
        with Horizontal(classes="global-profile-bar"):
            yield Label("👤 Active Person:", classes="action-title")
            yield Select(options=[("Default User", "1")], value="1", id="profile-select")
        with TabbedContent():
            with TabPane("Calculator & Syringe Visualizer", id="calc-tab"):
                with Grid(classes="pane-container"):
                    # Left Sidebar: Inputs in Scrollable Container
                    with ScrollableContainer(classes="sidebar-panel"):
                        yield Label("PEPTIDE CONFIGURATION", classes="title-label")
                        
                        yield Label("Select Peptide Template:", classes="input-label")
                        yield Select(
                            options=[("Custom / Other", "Custom / Other")],
                            value="Custom / Other",
                            id="peptide-select"
                        )
                        
                        yield Label("Vial Size (mg of peptide):", classes="input-label")
                        with Horizontal(classes="preset-row"):
                            yield Button("5mg", id="vial-btn-5")
                            yield Button("10mg", id="vial-btn-10")
                            yield Button("25mg", id="vial-btn-25")
                            yield Button("30mg", id="vial-btn-30")
                            yield Button("50mg", id="vial-btn-50")
                            yield Button("60mg", id="vial-btn-60")
                        yield Input(value="5.0", placeholder="Enter mg...", id="vial-size-input")
                        
                        yield Label("Bacteriostatic Water (mL added):", classes="input-label")
                        with Horizontal(classes="preset-row"):
                            yield Button("1mL", id="water-btn-1")
                            yield Button("2mL", id="water-btn-2")
                            yield Button("2.5mL", id="water-btn-2_5")
                            yield Button("3mL", id="water-btn-3")
                        yield Input(value="2.0", placeholder="Enter mL...", id="water-input")
                        yield Label(
                            "GLP-1/2/3: 2mL-3mL | Peptides: 3mL\n"
                            "Higher water = lower conc, making small doses easier to draw.",
                            classes="help-box"
                        )
                        
                        yield Label("Target Dose Amount:", classes="input-label")
                        yield Input(value="250.0", placeholder="Enter target dose...", id="dose-input")
                        yield Label("Target Dose Unit:", classes="input-label")
                        yield Select(
                            options=[("mcg", "mcg"), ("mg", "mg")],
                            value="mcg",
                            id="dose-unit-select"
                        )
                        
                        yield Label("Save Protocol To (select one or more people):", classes="input-label")
                        yield SelectionList(id="save-target-profiles")
                        yield Button("💾 Save Protocol", id="save-profile-protocol-btn")

                    # Right Panel: Output & Visualizer in Scrollable Container
                    with ScrollableContainer(classes="results-panel"):
                        yield Label("DILUTION & CALCULATED DOSES", classes="title-label")
                        
                        with Horizontal(classes="result-row"):
                            yield Label("Active Profile:", classes="result-label")
                            yield Label("Default User", id="calc-active-profile", classes="result-val highlight-val")

                        with Horizontal(classes="result-row"):
                            yield Label("Solution Concentration:", classes="result-label")
                            yield Label("Enter valid inputs...", id="calc-concentration", classes="result-val")
                            
                        with Horizontal(classes="result-row"):
                            yield Label("Single Dose Volume (mL):", classes="result-label")
                            yield Label("Enter valid inputs...", id="calc-dose-volume", classes="result-val")
                            
                        with Horizontal(classes="result-row"):
                            yield Label("U-100 Syringe Draw:", classes="result-label")
                            yield Label("Enter valid inputs...", id="calc-syringe-draw", classes="result-val highlight-val")
                            
                        with Horizontal(classes="result-row"):
                            yield Label("Total Doses per Vial:", classes="result-label")
                            yield Label("Enter valid inputs...", id="calc-doses-per-vial", classes="result-val")
                        
                        yield Label("INSULIN SYRINGE DRAW VISUALIZER (U-100 Syringe)", classes="title-label")
                        yield Label("  Syringe representation will appear here when inputs are valid.", id="syringe-visual")

            with TabPane("Patient Tracker (Multi-Person)", id="patient-tab"):
                with Vertical():
                    with Container(classes="patient-controls-bar"):
                        with Horizontal(classes="control-row"):
                            yield Label("Manage People:", classes="action-title")
                            yield Input(placeholder="New person name...", id="new-profile-input")
                            yield Button("+ Add Person", id="add-profile-btn")
                            yield Button("❌ Remove Person", id="remove-profile-btn")
                        with Horizontal(classes="control-row"):
                            yield Label("Quick Add Peptide:", classes="action-title")
                            yield Select(options=[("BPC-157", "BPC-157")], value="BPC-157", id="patient-add-peptide-select")
                            yield Button("+ Add to Person", id="quick-add-peptide-btn")
                            yield Button("🖨️ Export Printable Sheet", id="export-patient-sheet-btn")
                            yield Button("❌ Remove Selected", id="delete-protocol-btn")
                        with Horizontal(classes="control-row"):
                            yield Button("✏️ Edit Selected", id="edit-protocol-btn")
                            yield Button("💊 Log Dose Taken", id="log-dose-btn")
                            yield Button("📅 View Titration Schedule", id="view-schedule-btn")
                    yield DataTable(id="patient-protocols-table", cursor_type="row")

            with TabPane("Dosing Schedule Planner", id="schedule-tab"):
                with Vertical():
                    with Container(classes="schedule-controls-bar"):
                        with Horizontal(classes="control-row"):
                            yield Label("Select Schedule to View:", classes="action-title")
                            yield Select(
                                options=[("📋 All Active Peptides", "__all__")],
                                value="__all__",
                                id="schedule-protocol-select",
                            )
                            yield Button("💾 Save Schedule to File", id="save-schedule-btn")
                        with Horizontal(classes="schedule-banner-row"):
                            yield Label("Loading schedule details...", id="schedule-banner-text")
                    yield DataTable(id="schedule-table", cursor_type="row")

            with TabPane("Dose Log", id="dose-log-tab"):
                with Vertical():
                    with Container(classes="action-bar"):
                        yield Label("Dose History & Adherence (Active Profile)", classes="action-title")
                        yield Button("📄 Export CSV", id="export-dose-log-csv-btn")
                        yield Button("🗑️ Delete Entry", id="delete-log-btn")
                    yield Label("Adherence Summary", classes="title-label")
                    yield DataTable(id="adherence-table", cursor_type="row")
                    yield Label("Recent Dose Log", classes="title-label")
                    yield DataTable(id="dose-log-table", cursor_type="row")

            with TabPane("Peptide Reference & Cited Sources", id="reference-tab"):
                with Vertical():
                    with Container(classes="action-bar"):
                        yield Label("Search Peptide Reference:", classes="action-title")
                        yield Input(placeholder="Filter by name or notes (e.g. GLP-1, weight loss, sleep)...", id="reference-search-input")
                    with ScrollableContainer(classes="info-pane", id="reference-scroll-container"):
                        yield Label("Loading reference database...", classes="info-title")

            with TabPane("Literature Tracker", id="literature-tab"):
                with Vertical():
                    with Container(classes="action-bar"):
                        yield Label("Track PubMed Article by PMID:", classes="action-title")
                        yield Input(placeholder="Enter PMID (e.g. 34097675)...", id="literature-pmid-input")
                        yield Button("🔎 Fetch & Track", id="fetch-literature-btn")
                        yield Button("🗑️ Remove Selected", id="delete-literature-btn")
                    yield Label("Idle. Enter a PMID above to fetch its title, authors, and abstract from NCBI.", id="literature-status", classes="info-text")
                    yield DataTable(id="literature-table", cursor_type="row")
                    with ScrollableContainer(classes="info-pane"):
                        with Vertical(classes="info-section"):
                            yield Label("Abstract", classes="info-title")
                            yield Static("Select a tracked article above to view its abstract.", id="literature-abstract-view", classes="info-text")
        yield Footer()

    def on_mount(self) -> None:
        patient_table = self.query_one("#patient-protocols-table", DataTable)
        patient_table.add_columns("ID", "Peptide Name", "Vial Strength", "BAC Water", "Target Dose", "Syringe Draw", "Frequency", "Next Dose Due", "Last Updated")

        adherence_table = self.query_one("#adherence-table", DataTable)
        adherence_table.add_columns("Peptide", "Frequency", "Doses Logged", "Adherence %", "Next Dose Due")

        dose_log_table = self.query_one("#dose-log-table", DataTable)
        dose_log_table.add_columns("ID", "Peptide", "Dose", "Taken At", "Notes")

        literature_table = self.query_one("#literature-table", DataTable)
        literature_table.add_columns("ID", "PMID", "Title", "Authors", "Journal", "Year")

        self.refresh_profiles()
        self.refresh_peptide_templates()
        self.refresh_patient_protocols_table()
        self.refresh_dose_log_tables()
        self.refresh_schedule_selector()
        self.update_schedule_table()
        self.populate_reference_tab()
        self.refresh_literature_table()
        self.recalculate()

    def refresh_profiles(self) -> None:
        profiles = db.get_profiles()
        if not profiles:
            return
        options = [(p["name"], str(p["id"])) for p in profiles]

        profile_select = self.query_one("#profile-select", Select)
        profile_select.set_options(options)
        profile_select.value = str(self.active_profile_id)

        self.refresh_active_profile_display()

    def refresh_save_target_profiles(self) -> None:
        """Repopulate the Calculator tab's multi-person save checklist.

        Always defaults to matching the active person selected in the
        global picker at the top of the app -- switching that picker
        re-syncs this checklist to just that person. The user can still
        check additional people before clicking Save to save to several
        profiles at once for that one action.
        """
        try:
            selection_list = self.query_one("#save-target-profiles", SelectionList)
        except Exception:
            return

        profiles = db.get_profiles()
        selection_list.clear_options()
        selection_list.add_options([
            (p["name"], p["id"], p["id"] == self.active_profile_id)
            for p in profiles
        ])

    def refresh_active_profile_display(self) -> None:
        profiles = db.get_profiles()
        current_prof_name = next((p["name"] for p in profiles if p["id"] == self.active_profile_id), "Unknown")
        try:
            self.query_one("#calc-active-profile", Label).update(current_prof_name)
            prof_select = self.query_one("#profile-select", Select)
            if str(prof_select.value) != str(self.active_profile_id):
                prof_select.value = str(self.active_profile_id)
        except Exception:
            pass
        self.refresh_save_target_profiles()
        self.refresh_patient_protocols_table()
        self.refresh_dose_log_tables()
        self.refresh_schedule_selector()
        self.update_schedule_table()

    def refresh_peptide_templates(self) -> None:
        peptides = db.get_peptides()
        options = [(p["name"], p["name"]) for p in peptides]
        names = {p["name"] for p in peptides}

        # Select.set_options() always resets the current selection to blank,
        # so restore a sensible value afterward (previous selection if it
        # still exists, else a fallback) rather than leaving the dropdown empty.
        peptide_select = self.query_one("#peptide-select", Select)
        prior_peptide = peptide_select.value if peptide_select.value != Select.BLANK else self.peptide
        peptide_select.set_options(options)
        peptide_select.value = prior_peptide if prior_peptide in names else "Custom / Other"

        patient_add_select = self.query_one("#patient-add-peptide-select", Select)
        prior_patient_add = patient_add_select.value
        patient_add_select.set_options(options)
        if prior_patient_add in names:
            patient_add_select.value = prior_patient_add
        elif "BPC-157" in names:
            patient_add_select.value = "BPC-157"
        elif names:
            patient_add_select.value = sorted(names)[0]

        try:
            self.refresh_schedule_selector()
        except Exception:
            pass

    def refresh_schedule_selector(self, preferred_value: str | None = None) -> None:
        try:
            sched_select = self.query_one("#schedule-protocol-select", Select)
        except Exception:
            return

        profiles = db.get_profiles()
        current_prof = next((p for p in profiles if p["id"] == self.active_profile_id), None)
        prof_name = current_prof["name"] if current_prof else f"Profile #{self.active_profile_id}"

        protocols = db.get_user_protocols(self.active_profile_id)
        catalog_peptides = db.get_peptides()

        options: list[tuple[str, str]] = []
        if protocols:
            options.append((f"📋 All Active Peptides for {prof_name} ({len(protocols)} protocols)", "__all__"))
            for p in protocols:
                label = f"💊 {p['peptide_name']} ({p['vial_mg']:.1f}mg/{p['water_ml']:.1f}mL • {p['target_dose']}{p['dose_unit']})"
                options.append((label, f"protocol_{p['id']}"))
        else:
            options.append((f"📋 No active protocols for {prof_name}", "__none__"))

        for cat in catalog_peptides:
            label = f"🔬 Catalog: {cat['name']} ({cat['vial_mg']:.1f}mg/{cat['water_ml']:.1f}mL)"
            options.append((label, f"catalog_{cat['name']}"))

        valid_values = {val for _, val in options}
        prior_val = str(sched_select.value) if sched_select.value != Select.BLANK else None

        if preferred_value and preferred_value in valid_values:
            target_val = preferred_value
        elif prior_val and prior_val in valid_values:
            target_val = prior_val
        elif protocols:
            target_val = "__all__"
        else:
            target_val = options[0][1] if options else Select.BLANK

        with sched_select.prevent(Select.Changed):
            sched_select.set_options(options)
            sched_select.value = target_val

    def refresh_patient_protocols_table(self) -> None:
        table = self.query_one("#patient-protocols-table", DataTable)
        prev_protocol_id: int | None = None
        if table.cursor_row is not None and table.row_count > 0:
            try:
                prev_protocol_id = int(table.get_cell_at((table.cursor_row, 0)))
            except Exception:
                pass

        table.clear()

        now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC, to match db.py's next_due_at
        due_by_protocol_id = {
            entry['protocol_id']: entry['next_due_at']
            for entry in db.get_protocol_adherence(self.active_profile_id)
        }

        protocols = db.get_user_protocols(self.active_profile_id)
        restore_row = 0
        for idx, p in enumerate(protocols):
            if prev_protocol_id is not None and p['id'] == prev_protocol_id:
                restore_row = idx
            conc = calc.concentration_mg_ml(p['vial_mg'], p['water_ml'])
            dose_mg = calc.dose_to_mg(p['target_dose'], p['dose_unit'])
            vol_ml = calc.draw_volume_ml(dose_mg, conc)
            units = calc.syringe_units(vol_ml)
            due_label = calc.format_due_label(due_by_protocol_id.get(p['id']), now)

            table.add_row(
                str(p['id']),
                p['peptide_name'],
                f"{p['vial_mg']:.1f} mg",
                f"{p['water_ml']:.1f} mL",
                f"{p['target_dose']} {p['dose_unit']}",
                f"{units:.1f} Units",
                p['frequency'],
                due_label,
                p['updated_at'][:10]
            )

        if protocols and restore_row < table.row_count:
            try:
                table.move_cursor(row=restore_row)
            except Exception:
                pass

        try:
            self.refresh_schedule_selector()
        except Exception:
            pass

    def refresh_dose_log_tables(self) -> None:
        try:
            adherence_table = self.query_one("#adherence-table", DataTable)
            dose_log_table = self.query_one("#dose-log-table", DataTable)
        except Exception:
            return  # tables not mounted yet

        adherence_table.clear()
        now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC, to match db.py's next_due_at
        for entry in db.get_protocol_adherence(self.active_profile_id):
            pct_str = f"{entry['adherence_pct']:.0f}%" if entry['adherence_pct'] is not None else "N/A"
            due_label = calc.format_due_label(entry['next_due_at'], now)
            adherence_table.add_row(
                entry['peptide_name'],
                entry['frequency'] or "-",
                str(entry['logged_count']),
                pct_str,
                due_label,
            )

        dose_log_table.clear()
        for log in db.get_dose_log(self.active_profile_id):
            dose_log_table.add_row(
                str(log['id']),
                log['peptide_name'],
                f"{log['dose_amount']} {log['dose_unit']}",
                log['taken_at'],
                log['notes'] or "",
            )

    def delete_selected_dose_log_entry(self) -> None:
        table = self.query_one("#dose-log-table", DataTable)
        if table.cursor_row is None or table.row_count == 0:
            self.notify("Select a row in the dose log to remove.", severity="warning")
            return

        try:
            log_id = int(table.get_cell_at((table.cursor_row, 0)))
        except (TypeError, ValueError):
            self.notify("Error reading selected log entry.", severity="error")
            return

        def handle_confirm(confirmed: bool | None) -> None:
            if not confirmed:
                return
            db.delete_dose_log_entry(log_id)
            self.refresh_dose_log_tables()
            self.notify("Removed dose log entry.", timeout=3.0)

        self.push_screen(ConfirmScreen("Delete this dose log entry?"), handle_confirm)

    def populate_reference_tab(self, filter_text: str = "") -> None:
        container = self.query_one("#reference-scroll-container", ScrollableContainer)
        container.remove_children()

        peptides = db.get_peptides()
        needle = filter_text.strip().lower()
        if needle:
            peptides = [
                p for p in peptides
                if needle in p['name'].lower() or needle in (p['notes'] or "").lower()
            ]

        if not peptides:
            container.mount(Label(f"No peptides match '{filter_text.strip()}'.", classes="info-title"))
            return

        for p in peptides:
            children = [
                Label(f"🔬 {p['name']} Reference & Clinical Guidelines", classes="info-title"),
                Static(f"• Standard Vial: {p['vial_mg']} mg | Recommended BAC Water: {p['water_ml']} mL\n• Target Dose: {p['dose']} {p['unit']} ({p['freq']})\n• Details: {p['notes']}", classes="info-text")
            ]
            if p['sources']:
                children.append(Label("Scientific Citations & PubMed Literature:", classes="input-label"))
                for s in p['sources']:
                    cite_md = f"  - {s['title']} (PMID: {s['pmid']})\n    URL: {s['url']}"
                    children.append(Static(cite_md, classes="source-link"))
                    
            sec = Vertical(*children, classes="info-section")
            container.mount(sec)

    def refresh_literature_table(self) -> None:
        try:
            table = self.query_one("#literature-table", DataTable)
        except Exception:
            return

        table.clear()
        for article in db.get_tracked_literature():
            authors = article["authors"] or ["Unknown Authors"]
            authors_str = ", ".join(authors[:3])
            if len(authors) > 3:
                authors_str += ", et al."
            table.add_row(
                str(article["id"]),
                article["pmid"],
                article["title"],
                authors_str,
                article["journal"] or "-",
                article["pub_date"] or "-",
            )

    def fetch_literature_pmid(self) -> None:
        input_widget = self.query_one("#literature-pmid-input", Input)
        status = self.query_one("#literature-status", Label)
        raw_pmid = input_widget.value.strip()

        try:
            clean_pmid = ncbi.validate_pmid(raw_pmid)
        except ValueError as e:
            status.update(f"❌ {e}")
            self.notify(str(e), severity="error")
            return

        status.update(f"⏳ Fetching PMID {clean_pmid} from NCBI E-utilities...")
        self.run_worker(
            self.fetch_literature_worker(clean_pmid),
            group="literature-fetch",
            exclusive=True,
        )

    async def fetch_literature_worker(self, pmid: str) -> None:
        status = self.query_one("#literature-status", Label)
        try:
            article = await ncbi.fetch_pubmed_article(pmid)
        except Exception as e:
            status.update(f"❌ Failed to fetch PMID {pmid}: {e}")
            self.notify(f"Failed to fetch PMID {pmid}.", severity="error")
            return

        db.save_tracked_article(
            pmid=article["pmid"],
            title=article["title"],
            authors=article["authors"],
            abstract=article["abstract"],
            journal=article["journal"],
            pub_date=article["pub_date"],
            url=article["url"],
        )

        status.update(f"✅ Tracked PMID {pmid}: {article['title'][:80]}")
        self.query_one("#literature-pmid-input", Input).value = ""
        self.refresh_literature_table()
        self.notify(f"Added PMID {pmid} to the literature tracker.", timeout=4.0)

    def delete_selected_tracked_article(self) -> None:
        table = self.query_one("#literature-table", DataTable)
        if table.cursor_row is None or table.row_count == 0:
            self.notify("Select a tracked article to remove.", severity="warning")
            return

        try:
            article_id = int(table.get_cell_at((table.cursor_row, 0)))
        except (TypeError, ValueError):
            self.notify("Error reading selected article.", severity="error")
            return

        def handle_confirm(confirmed: bool | None) -> None:
            if not confirmed:
                return
            db.delete_tracked_article(article_id)
            self.refresh_literature_table()
            self.query_one("#literature-abstract-view", Static).update(
                "Select a tracked article above to view its abstract."
            )
            self.notify("Removed tracked article.", timeout=3.0)

        self.push_screen(ConfirmScreen("Remove this tracked article?"), handle_confirm)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id != "literature-table":
            return
        if event.row_key is None:
            return
        try:
            pmid = event.data_table.get_cell_at((event.cursor_row, 1))
        except Exception:
            return
        article = db.get_tracked_article_by_pmid(pmid)
        if article:
            self.query_one("#literature-abstract-view", Static).update(
                f"[b]{article['title']}[/b]\n\n{article['abstract']}"
            )

    def watch_active_profile_id(self, old_val: int, new_val: int) -> None:
        self.refresh_active_profile_display()

    def on_select_changed(self, event: Select.Changed) -> None:
        if not event.value or event.value == Select.BLANK:
            return
            
        if event.select.id == "peptide-select":
            self.peptide = str(event.value)
            p = db.get_peptide_by_name(self.peptide)
            if p:
                self.query_one("#vial-size-input", Input).value = f"{p['vial_mg']}"
                self.query_one("#water-input", Input).value = f"{p['water_ml']}"
                self.query_one("#dose-input", Input).value = f"{p['dose']}"
                self.query_one("#dose-unit-select", Select).value = p["unit"]
                
                self.vial_mg = p['vial_mg']
                self.water_ml = p['water_ml']
                self.target_dose = p['dose']
                self.dose_unit = p['unit']
        elif event.select.id == "dose-unit-select":
            self.dose_unit = str(event.value)
        elif event.select.id == "profile-select":
            try:
                val = int(str(event.value))
                if val != self.active_profile_id:
                    self.active_profile_id = val
                    self.refresh_active_profile_display()
            except (ValueError, TypeError):
                pass
        elif event.select.id == "schedule-protocol-select":
            self.update_schedule_table()
            return
            
        self.recalculate()
        self.update_schedule_table()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "reference-search-input":
            self.populate_reference_tab(event.value)
            return

        try:
            val = float(event.input.value) if event.input.value else 0.0
            if event.input.id == "vial-size-input":
                self.vial_mg = val
            elif event.input.id == "water-input":
                self.water_ml = val
            elif event.input.id == "dose-input":
                self.target_dose = val
        except ValueError:
            pass
            
        self.recalculate()
        self.update_schedule_table()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "literature-pmid-input":
            self.fetch_literature_pmid()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if not btn_id:
            return

        if btn_id.startswith("vial-btn-"):
            val = btn_id.replace("vial-btn-", "")
            self.query_one("#vial-size-input", Input).value = val
            self.vial_mg = float(val)
        elif btn_id.startswith("water-btn-"):
            val = btn_id.replace("water-btn-", "")
            val_clean = val.replace("_", ".")
            self.query_one("#water-input", Input).value = val_clean
            self.water_ml = float(val_clean)
        elif btn_id == "save-profile-protocol-btn":
            self.save_current_to_profile()
        elif btn_id == "quick-add-peptide-btn":
            self.quick_add_peptide_to_patient()
        elif btn_id == "add-profile-btn":
            self.create_new_profile()
        elif btn_id == "export-patient-sheet-btn":
            self.export_patient_sheet()
        elif btn_id == "delete-protocol-btn":
            self.delete_selected_patient_protocol()
        elif btn_id == "remove-profile-btn":
            self.delete_selected_profile()
        elif btn_id == "edit-protocol-btn":
            self.load_selected_protocol_for_edit()
        elif btn_id == "view-schedule-btn":
            self.view_selected_protocol_schedule()
        elif btn_id == "log-dose-btn":
            self.log_selected_protocol_dose()
        elif btn_id == "delete-log-btn":
            self.delete_selected_dose_log_entry()
        elif btn_id == "export-dose-log-csv-btn":
            self.export_dose_log_csv()
        elif btn_id == "save-schedule-btn":
            self.save_schedule_to_file()
        elif btn_id == "fetch-literature-btn":
            self.fetch_literature_pmid()
        elif btn_id == "delete-literature-btn":
            self.delete_selected_tracked_article()

        self.recalculate()
        self.update_schedule_table()

    def save_current_to_profile(self) -> None:
        try:
            selection_list = self.query_one("#save-target-profiles", SelectionList)
            target_ids = list(selection_list.selected)
        except Exception:
            target_ids = []
        if not target_ids:
            target_ids = [self.active_profile_id]

        p = db.get_peptide_by_name(self.peptide)
        freq = p["freq"] if p else "daily"
        notes = p["notes"] if p else "User custom calculation"
        sched = p["schedule"] if p else [("Custom", self.target_dose, self.dose_unit)]
        sources = p["sources"] if p else []

        for profile_id in target_ids:
            db.add_or_update_user_protocol(
                profile_id,
                self.peptide,
                self.vial_mg,
                self.water_ml,
                self.target_dose,
                self.dose_unit,
                freq,
                notes,
                sched,
                sources
            )

        self.refresh_patient_protocols_table()
        self.refresh_dose_log_tables()

        profiles = db.get_profiles()
        names = [prof["name"] for prof in profiles if prof["id"] in target_ids]
        names_str = ", ".join(names) if names else "selected people"
        self.notify(f"Saved {self.peptide} protocol to: {names_str}", timeout=4.0)

    def quick_add_peptide_to_patient(self) -> None:
        select_widget = self.query_one("#patient-add-peptide-select", Select)
        if not select_widget.value or select_widget.value == Select.BLANK:
            self.notify("Please select a peptide template.", severity="warning")
            return
            
        peptide_name = str(select_widget.value)
        p = db.get_peptide_by_name(peptide_name)
        if p:
            db.add_or_update_user_protocol(
                self.active_profile_id,
                p["name"],
                p["vial_mg"],
                p["water_ml"],
                p["dose"],
                p["unit"],
                p["freq"],
                p["notes"],
                p["schedule"],
                p["sources"]
            )
            self.refresh_patient_protocols_table()
            profiles = db.get_profiles()
            prof_name = next((prof["name"] for prof in profiles if prof["id"] == self.active_profile_id), "Person")
            self.notify(f"Added {peptide_name} to {prof_name}'s protocol list!", timeout=3.0)

    def create_new_profile(self) -> None:
        input_widget = self.query_one("#new-profile-input", Input)
        name = input_widget.value.strip()
        if not name:
            self.notify("Please enter a person name.", severity="error")
            return
        prof_id = db.add_profile(name)
        if prof_id:
            input_widget.value = ""
            self.active_profile_id = prof_id
            self.refresh_profiles()
            self.notify(f"Created & selected profile: {name}", timeout=3.0)
        else:
            self.notify("Profile name already exists.", severity="error")

    def export_patient_sheet(self) -> None:
        filename = db.export_person_reference_sheet(self.active_profile_id)
        if filename:
            self.notify(f"Exported patient summary to: {filename}", timeout=4.0)
        else:
            self.notify("Error exporting summary sheet.", severity="error")

    def export_dose_log_csv(self) -> None:
        filename = db.export_dose_log_csv(self.active_profile_id)
        if filename:
            self.notify(f"Exported dose log to: {filename}", timeout=4.0)
        else:
            self.notify("Error exporting dose log.", severity="error")

    def delete_selected_patient_protocol(self) -> None:
        table = self.query_one("#patient-protocols-table", DataTable)
        if table.cursor_row is None or table.row_count == 0:
            self.notify("Select a row in the patient table to remove.", severity="warning")
            return

        try:
            protocol_id = int(table.get_cell_at((table.cursor_row, 0)))
        except (TypeError, ValueError):
            self.notify("Error reading selected protocol.", severity="error")
            return

        def handle_confirm(confirmed: bool | None) -> None:
            if not confirmed:
                return
            db.delete_user_protocol(protocol_id)
            self.refresh_patient_protocols_table()
            self.refresh_dose_log_tables()
            self.notify("Removed protocol from patient profile.", timeout=3.0)

        self.push_screen(ConfirmScreen("Remove this protocol from the patient's list?"), handle_confirm)

    def delete_selected_profile(self) -> None:
        profiles = db.get_profiles()
        if len(profiles) <= 1:
            self.notify("Cannot remove the only remaining profile.", severity="warning")
            return

        profile_id = self.active_profile_id
        prof_name = next((p["name"] for p in profiles if p["id"] == profile_id), "this profile")

        def handle_confirm(confirmed: bool | None) -> None:
            if not confirmed:
                return
            if db.delete_profile(profile_id):
                remaining = db.get_profiles()
                self.active_profile_id = remaining[0]["id"]
                self.refresh_profiles()
                self.refresh_dose_log_tables()
                self.notify(f"Removed profile: {prof_name}", timeout=3.0)
            else:
                self.notify("Cannot remove the only remaining profile.", severity="warning")

        self.push_screen(
            ConfirmScreen(f"Remove person '{prof_name}' and all their saved protocols/dose history? This cannot be undone."),
            handle_confirm,
        )

    def load_selected_protocol_for_edit(self) -> None:
        table = self.query_one("#patient-protocols-table", DataTable)
        if table.cursor_row is None or table.row_count == 0:
            self.notify("Select a row in the patient table to edit.", severity="warning")
            return

        try:
            protocol_id = int(table.get_cell_at((table.cursor_row, 0)))
        except (TypeError, ValueError):
            self.notify("Error reading selected protocol.", severity="error")
            return

        protocol = db.get_user_protocol_by_id(protocol_id)
        if not protocol:
            self.notify("Protocol not found.", severity="error")
            return

        peptide_select = self.query_one("#peptide-select", Select)
        dose_unit_select = self.query_one("#dose-unit-select", Select)

        # Bypass on_select_changed's auto-refill-from-template side effect --
        # we want this protocol's exact saved values, not the master template's.
        with peptide_select.prevent(Select.Changed):
            peptide_select.value = protocol["peptide_name"]
        with dose_unit_select.prevent(Select.Changed):
            dose_unit_select.value = protocol["dose_unit"]

        self.query_one("#vial-size-input", Input).value = f"{protocol['vial_mg']}"
        self.query_one("#water-input", Input).value = f"{protocol['water_ml']}"
        self.query_one("#dose-input", Input).value = f"{protocol['target_dose']}"

        self.peptide = protocol["peptide_name"]
        self.vial_mg = protocol["vial_mg"]
        self.water_ml = protocol["water_ml"]
        self.target_dose = protocol["target_dose"]
        self.dose_unit = protocol["dose_unit"]

        self.query_one(TabbedContent).active = "calc-tab"
        # TabbedContent re-syncs `active` to whichever tab contains the
        # focused widget (see TabPane._on_descendant_focus), and the button
        # that triggered this handler is still focused inside patient-tab --
        # that resync would otherwise revert the tab switch above on the next
        # message cycle. Moving focus into the new tab keeps them in sync.
        self.set_focus(self.query_one("#vial-size-input", Input))
        self.recalculate()
        self.update_schedule_table()
        self.notify(
            f"Loaded {protocol['peptide_name']} into the calculator for editing. Adjust and Save to update.",
            timeout=4.0,
        )

    def view_selected_protocol_schedule(self) -> None:
        table = self.query_one("#patient-protocols-table", DataTable)
        if table.cursor_row is None or table.row_count == 0:
            self.notify("Select a row in the patient table to view its schedule.", severity="warning")
            return

        try:
            protocol_id = int(table.get_cell_at((table.cursor_row, 0)))
        except (TypeError, ValueError):
            self.notify("Error reading selected protocol.", severity="error")
            return

        protocol = db.get_user_protocol_by_id(protocol_id)
        if not protocol:
            self.notify("Protocol not found.", severity="error")
            return

        self.query_one(TabbedContent).active = "schedule-tab"
        self.refresh_schedule_selector(preferred_value=f"protocol_{protocol_id}")
        self.set_focus(self.query_one("#schedule-protocol-select", Select))
        self.update_schedule_table()
        self.notify(
            f"Loaded titration schedule for {protocol['peptide_name']}.",
            timeout=3.0,
        )

    def log_selected_protocol_dose(self) -> None:
        table = self.query_one("#patient-protocols-table", DataTable)
        if table.cursor_row is None or table.row_count == 0:
            self.notify("Select a row in the patient table to log a dose.", severity="warning")
            return

        try:
            protocol_id = int(table.get_cell_at((table.cursor_row, 0)))
        except (TypeError, ValueError):
            self.notify("Error reading selected protocol.", severity="error")
            return

        protocol = db.get_user_protocol_by_id(protocol_id)
        if not protocol:
            self.notify("Protocol not found.", severity="error")
            return

        dose_desc = f"{protocol['peptide_name']} {protocol['target_dose']} {protocol['dose_unit']}"

        def handle_notes(notes: str | None) -> None:
            if notes is None:
                return  # cancelled
            db.log_dose(
                self.active_profile_id,
                protocol_id,
                protocol["peptide_name"],
                protocol["target_dose"],
                protocol["dose_unit"],
                notes,
            )
            self.refresh_dose_log_tables()
            self.notify(f"Logged dose: {dose_desc}", timeout=3.0)

        self.push_screen(LogDoseScreen(f"Log dose: {dose_desc}"), handle_notes)

    def recalculate(self) -> None:
        try:
            vial_mg = self.vial_mg
            water_ml = self.water_ml
            dose = self.target_dose
            unit = self.dose_unit

            if vial_mg <= 0 or water_ml <= 0 or dose <= 0:
                self.query_one("#calc-concentration", Label).update("Enter positive numbers...")
                self.query_one("#calc-dose-volume", Label).update("Enter positive numbers...")
                self.query_one("#calc-syringe-draw", Label).update("Enter positive numbers...")
                self.query_one("#calc-doses-per-vial", Label).update("Enter positive numbers...")
                self.query_one("#syringe-visual", Label).update("  Syringe representation will appear here when inputs are valid.")
                return

            conc_mg_ml = calc.concentration_mg_ml(vial_mg, water_ml)
            conc_mcg_ml = conc_mg_ml * 1000.0
            dose_mg = calc.dose_to_mg(dose, unit)
            draw_volume_ml = calc.draw_volume_ml(dose_mg, conc_mg_ml)
            syringe_units = calc.syringe_units(draw_volume_ml)
            doses_per_vial = calc.doses_per_vial(vial_mg, dose_mg)

            self.query_one("#calc-concentration", Label).update(f"{conc_mg_ml:.2f} mg/mL ({conc_mcg_ml:,.0f} mcg/mL)")
            self.query_one("#calc-dose-volume", Label).update(f"{draw_volume_ml:.3f} mL")
            
            if syringe_units > 100.0:
                self.query_one("#calc-syringe-draw", Label).update(f"{syringe_units:.1f} Units [bold red](Exceeds Capacity!)[/]")
            else:
                self.query_one("#calc-syringe-draw", Label).update(f"{syringe_units:.1f} Units")
                
            self.query_one("#calc-doses-per-vial", Label).update(f"{doses_per_vial:.1f} doses")
            
            syringe_ascii = make_syringe_display(syringe_units)
            self.query_one("#syringe-visual", Label).update(syringe_ascii)
        except Exception:
            pass

    def update_schedule_table(self) -> None:
        try:
            table = self.query_one("#schedule-table", DataTable)
            banner = self.query_one("#schedule-banner-text", Label)
            sched_select = self.query_one("#schedule-protocol-select", Select)
        except Exception:
            return

        selected = str(sched_select.value) if sched_select.value != Select.BLANK else "__all__"
        profiles = db.get_profiles()
        current_prof = next((p for p in profiles if p["id"] == self.active_profile_id), None)
        prof_name = current_prof["name"] if current_prof else f"Profile #{self.active_profile_id}"
        protocols = db.get_user_protocols(self.active_profile_id)

        if selected == "__all__" or (not protocols and selected == "__none__"):
            if not protocols:
                banner.update(f"ℹ️ No saved protocols found for {prof_name}. Select a Catalog peptide above or add peptides in the Patient Tracker.")
                table.clear(columns=True)
                table.add_columns("Notice")
                table.add_row(f"No active protocols assigned for {prof_name}. Use the selector above to explore titration schedules for Catalog peptides.")
                return

            banner.update(f"📋 Showing All {len(protocols)} Peptides for {prof_name} • Full Titration & Reconstitution Overview")
            table.clear(columns=True)
            table.add_columns(
                "Peptide",
                "Phase / Week",
                "Dose",
                "Volume (mL)",
                "Syringe Draw (U-100)",
                "Est. Doses / Vial",
                "Frequency",
                "Reconstitution & Syringe Status",
            )

            for p in protocols:
                vial_mg = p["vial_mg"]
                water_ml = p["water_ml"]
                if vial_mg <= 0 or water_ml <= 0:
                    continue
                conc_mg_ml = calc.concentration_mg_ml(vial_mg, water_ml)
                schedule_steps = p["schedule"] if p.get("schedule") else [("Prescribed Dose", p["target_dose"], p["dose_unit"])]
                freq = p.get("frequency") or "—"

                for phase, dose_val, unit in schedule_steps:
                    if dose_val <= 0:
                        continue
                    dose_mg = calc.dose_to_mg(dose_val, unit)
                    vol_ml = calc.draw_volume_ml(dose_mg, conc_mg_ml)
                    units = calc.syringe_units(vol_ml)
                    doses_per_vial = calc.doses_per_vial(vial_mg, dose_mg)
                    dose_str = f"{dose_val:.0f} mcg" if unit == "mcg" else f"{dose_val:.2f} mg"

                    draw_label, safety_status = calc.syringe_draw_status(units)
                    recon_info = f"{vial_mg:.1f}mg/{water_ml:.1f}mL ({conc_mg_ml:.2f}mg/mL)"
                    if "⚠️" in draw_label:
                        full_status = f"{safety_status} | {recon_info}"
                    else:
                        full_status = f"✓ {recon_info}"

                    table.add_row(
                        p["peptide_name"],
                        phase,
                        dose_str,
                        f"{vol_ml:.3f} mL",
                        draw_label,
                        f"{doses_per_vial:.1f} doses",
                        freq,
                        full_status,
                    )
            return

        elif selected.startswith("protocol_"):
            try:
                proto_id = int(selected.replace("protocol_", ""))
            except ValueError:
                return
            p = db.get_user_protocol_by_id(proto_id)
            if not p:
                return

            vial_mg = p["vial_mg"]
            water_ml = p["water_ml"]
            conc_mg_ml = calc.concentration_mg_ml(vial_mg, water_ml)
            conc_mcg_ml = conc_mg_ml * 1000.0
            freq = p.get("frequency") or "unspecified"
            weekly_exp = calc.parse_weekly_frequency(freq)

            banner.update(
                f"🔬 Showing: {p['peptide_name']} ({prof_name}) | "
                f"Vial: {vial_mg:.1f} mg | BAC Water: {water_ml:.1f} mL | "
                f"Strength: {conc_mg_ml:.2f} mg/mL ({conc_mcg_ml:,.0f} mcg/mL) | "
                f"Prescribed: {p['target_dose']} {p['dose_unit']} ({freq})"
            )

            table.clear(columns=True)
            table.add_columns(
                "Phase / Week",
                "Dose",
                "Volume (mL)",
                "Syringe Draw (U-100)",
                "Est. Doses per Vial",
                "Est. Vial Duration",
                "Syringe Safety & Multi-Draw Status",
            )

            schedule_steps = p["schedule"] if p.get("schedule") else [("Prescribed Dose", p["target_dose"], p["dose_unit"])]
            for phase, dose_val, unit in schedule_steps:
                if dose_val <= 0:
                    continue
                dose_mg = calc.dose_to_mg(dose_val, unit)
                vol_ml = calc.draw_volume_ml(dose_mg, conc_mg_ml)
                units = calc.syringe_units(vol_ml)
                doses_per_vial = calc.doses_per_vial(vial_mg, dose_mg)
                dose_str = f"{dose_val:.0f} mcg" if unit == "mcg" else f"{dose_val:.2f} mg"

                draw_label, safety_status = calc.syringe_draw_status(units)
                vial_dur = calc.format_vial_duration(doses_per_vial, weekly_exp, freq)

                table.add_row(
                    phase,
                    dose_str,
                    f"{vol_ml:.3f} mL",
                    draw_label,
                    f"{doses_per_vial:.1f} doses",
                    vial_dur,
                    safety_status,
                )
            return

        elif selected.startswith("catalog_"):
            pep_name = selected.replace("catalog_", "")
            cat = db.get_peptide_by_name(pep_name)
            if not cat:
                return

            vial_mg = cat["vial_mg"]
            water_ml = cat["water_ml"]
            conc_mg_ml = calc.concentration_mg_ml(vial_mg, water_ml)
            conc_mcg_ml = conc_mg_ml * 1000.0
            freq = cat.get("freq") or "unspecified"
            weekly_exp = calc.parse_weekly_frequency(freq)

            banner.update(
                f"🔬 Showing Catalog: {cat['name']} | "
                f"Standard Vial: {vial_mg:.1f} mg | BAC Water: {water_ml:.1f} mL | "
                f"Strength: {conc_mg_ml:.2f} mg/mL ({conc_mcg_ml:,.0f} mcg/mL) | "
                f"Standard Dose: {cat['dose']} {cat['unit']} ({freq})"
            )

            table.clear(columns=True)
            table.add_columns(
                "Phase / Week",
                "Dose",
                "Volume (mL)",
                "Syringe Draw (U-100)",
                "Est. Doses per Vial",
                "Est. Vial Duration",
                "Syringe Safety & Multi-Draw Status",
            )

            schedule_steps = cat["schedule"] if cat.get("schedule") else [("Standard Dose", cat["dose"], cat["unit"])]
            for phase, dose_val, unit in schedule_steps:
                if dose_val <= 0:
                    continue
                dose_mg = calc.dose_to_mg(dose_val, unit)
                vol_ml = calc.draw_volume_ml(dose_mg, conc_mg_ml)
                units = calc.syringe_units(vol_ml)
                doses_per_vial = calc.doses_per_vial(vial_mg, dose_mg)
                dose_str = f"{dose_val:.0f} mcg" if unit == "mcg" else f"{dose_val:.2f} mg"

                draw_label, safety_status = calc.syringe_draw_status(units)
                vial_dur = calc.format_vial_duration(doses_per_vial, weekly_exp, freq)

                table.add_row(
                    phase,
                    dose_str,
                    f"{vol_ml:.3f} mL",
                    draw_label,
                    f"{doses_per_vial:.1f} doses",
                    vial_dur,
                    safety_status,
                )
            return

        else:
            vial_mg = self.vial_mg
            water_ml = self.water_ml
            if vial_mg <= 0 or water_ml <= 0 or self.target_dose <= 0:
                return

            conc_mg_ml = calc.concentration_mg_ml(vial_mg, water_ml)
            p = db.get_peptide_by_name(self.peptide)
            schedule_steps = p["schedule"] if p and p["schedule"] else [("Custom Dose", self.target_dose, self.dose_unit)]

            banner.update(f"🔬 Showing: {self.peptide} (Calculator) | Vial: {vial_mg:.1f} mg | BAC Water: {water_ml:.1f} mL | Conc: {conc_mg_ml:.2f} mg/mL")

            table.clear(columns=True)
            table.add_columns(
                "Phase / Week",
                "Dose",
                "Volume (mL)",
                "Syringe Draw (U-100)",
                "Est. Doses per Vial",
                "Syringe Safety & Status",
            )

            for phase, dose_val, unit in schedule_steps:
                dose_mg = calc.dose_to_mg(dose_val, unit)
                vol_ml = calc.draw_volume_ml(dose_mg, conc_mg_ml)
                units = calc.syringe_units(vol_ml)
                doses_per_vial = calc.doses_per_vial(vial_mg, dose_mg)
                dose_str = f"{dose_val:.0f} mcg" if unit == "mcg" else f"{dose_val:.2f} mg"
                draw_label, safety_status = calc.syringe_draw_status(units)

                table.add_row(phase, dose_str, f"{vol_ml:.3f} mL", draw_label, f"{doses_per_vial:.1f} doses", safety_status)

    def save_schedule_to_file(self) -> None:
        try:
            sched_select = self.query_one("#schedule-protocol-select", Select)
            selected = str(sched_select.value) if sched_select.value != Select.BLANK else "__all__"
            profiles = db.get_profiles()
            current_prof = next((p for p in profiles if p["id"] == self.active_profile_id), None)
            prof_name = current_prof["name"] if current_prof else f"Profile_{self.active_profile_id}"

            if selected == "__all__":
                protocols = db.get_user_protocols(self.active_profile_id)
                if not protocols:
                    self.notify(f"No active protocols to export for {prof_name}.", severity="warning")
                    return

                filename = f"schedule_{prof_name.lower().replace(' ', '_')}_all_peptides.txt"
                filepath = os.path.join(os.getcwd(), filename)

                with open(filepath, "w") as f:
                    f.write("=" * 76 + "\n")
                    f.write(f" COMPLETE PATIENT DOSING SCHEDULE & TITRATION PLAN: {prof_name.upper()}\n")
                    f.write("=" * 76 + "\n")
                    f.write(f"Date Generated:         {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Patient Name:           {prof_name}\n")
                    f.write(f"Total Tracked Peptides: {len(protocols)}\n")
                    f.write("=" * 76 + "\n\n")

                    for i, p in enumerate(protocols, 1):
                        vial_mg = p["vial_mg"]
                        water_ml = p["water_ml"]
                        conc_mg_ml = calc.concentration_mg_ml(vial_mg, water_ml)
                        conc_mcg_ml = conc_mg_ml * 1000.0
                        freq = p.get("frequency") or "unspecified"
                        weekly_exp = calc.parse_weekly_frequency(freq)

                        f.write(f"[{i}] PEPTIDE: {p['peptide_name'].upper()}\n")
                        f.write("-" * 50 + "\n")
                        f.write(f"• Vial Size:           {vial_mg:.1f} mg\n")
                        f.write(f"• BAC Water Added:     {water_ml:.1f} mL\n")
                        f.write(f"• Solution Strength:   {conc_mg_ml:.2f} mg/mL ({conc_mcg_ml:,.0f} mcg/mL)\n")
                        f.write(f"• Prescribed Target:   {p['target_dose']} {p['dose_unit']} ({freq})\n")
                        if p.get("notes"):
                            f.write(f"• Clinical Notes:      {p['notes']}\n")

                        schedule_steps = p["schedule"] if p.get("schedule") else [("Prescribed Dose", p["target_dose"], p["dose_unit"])]
                        f.write("\n  Titration Schedule & Syringe Draws (U-100):\n")
                        phase_width = max(24, max((len(ph) for ph, _, _ in schedule_steps), default=24))
                        header = f"  {'Phase / Week':<{phase_width}} | {'Dose':<12} | {'Volume':<10} | {'Syringe Draw':<16} | {'Vial Est.':<14} | {'Safety / Status'}"
                        f.write(header + "\n")
                        f.write("  " + "-" * (len(header) - 2) + "\n")

                        for phase, dose_val, unit in schedule_steps:
                            dose_mg = calc.dose_to_mg(dose_val, unit)
                            vol_ml = calc.draw_volume_ml(dose_mg, conc_mg_ml)
                            units = calc.syringe_units(vol_ml)
                            doses_per_vial = calc.doses_per_vial(vial_mg, dose_mg)
                            dose_str = f"{dose_val:.0f} mcg" if unit == "mcg" else f"{dose_val:.2f} mg"
                            draw_label, safety_status = calc.syringe_draw_status(units)
                            vial_dur = calc.format_vial_duration(doses_per_vial, weekly_exp, freq)

                            f.write(f"  {phase:<{phase_width}} | {dose_str:<12} | {vol_ml:.3f} mL  | {draw_label:<16} | {vial_dur:<14} | {safety_status}\n")

                        if p.get("sources"):
                            f.write("\n  Scientific Citations:\n")
                            for s in p["sources"]:
                                f.write(f"  - {s['title']} (PMID: {s['pmid']})\n    URL: {s['url']}\n")

                        f.write("\n" + "=" * 76 + "\n\n")

                self.notify(f"Saved all-peptides schedule to: {filename}", timeout=4.0)
                return

            elif selected.startswith("protocol_"):
                proto_id = int(selected.replace("protocol_", ""))
                p = db.get_user_protocol_by_id(proto_id)
                if not p:
                    self.notify("Protocol not found.", severity="error")
                    return

                pep_name = p["peptide_name"]
                vial_mg = p["vial_mg"]
                water_ml = p["water_ml"]
                conc_mg_ml = calc.concentration_mg_ml(vial_mg, water_ml)
                conc_mcg_ml = conc_mg_ml * 1000.0
                freq = p.get("frequency") or "unspecified"
                weekly_exp = calc.parse_weekly_frequency(freq)
                schedule_steps = p["schedule"] if p.get("schedule") else [("Prescribed Dose", p["target_dose"], p["dose_unit"])]
                notes = p.get("notes") or "Patient protocol."
                sources = p.get("sources") or []

                filename = f"schedule_{prof_name.lower().replace(' ', '_')}_{pep_name.lower().replace(' ', '_')}.txt"
                filepath = os.path.join(os.getcwd(), filename)

                with open(filepath, "w") as f:
                    f.write("=" * 76 + "\n")
                    f.write(f" PEPTIDE TITRATION SCHEDULE: {pep_name.upper()}\n")
                    f.write("=" * 76 + "\n")
                    f.write(f"Patient Name:         {prof_name}\n")
                    f.write(f"Date Generated:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Vial Strength:        {vial_mg:.1f} mg\n")
                    f.write(f"Reconstitution Water: {water_ml:.1f} mL (Bacteriostatic Water)\n")
                    f.write(f"Concentration:        {conc_mg_ml:.2f} mg/mL ({conc_mcg_ml:,.0f} mcg/mL)\n")
                    f.write(f"Syringe Standard:     U-100 Insulin Syringe (100 Units = 1.0 mL)\n")
                    f.write(f"Frequency:            {freq}\n")
                    f.write("-" * 76 + "\n")
                    f.write("Notes & Details:\n")
                    f.write(f"{notes}\n")
                    f.write("-" * 76 + "\n\n")

                    f.write("DOSING SCHEDULE:\n")
                    phase_width = max(24, max((len(phase) for phase, _, _ in schedule_steps), default=24))
                    header = f"{'Phase / Period':<{phase_width}} | {'Dose':<12} | {'Volume':<10} | {'Syringe Draw':<16} | {'Vial Duration':<14} | {'Status'}"
                    f.write(header + "\n")
                    f.write("-" * len(header) + "\n")

                    for phase, dose_val, unit in schedule_steps:
                        dose_mg = calc.dose_to_mg(dose_val, unit)
                        vol_ml = calc.draw_volume_ml(dose_mg, conc_mg_ml)
                        units = calc.syringe_units(vol_ml)
                        doses_per_vial = calc.doses_per_vial(vial_mg, dose_mg)
                        dose_str = f"{dose_val:.0f} mcg" if unit == "mcg" else f"{dose_val:.2f} mg"
                        draw_label, safety_status = calc.syringe_draw_status(units)
                        vial_dur = calc.format_vial_duration(doses_per_vial, weekly_exp, freq)

                        f.write(f"{phase:<{phase_width}} | {dose_str:<12} | {vol_ml:.3f} mL  | {draw_label:<16} | {vial_dur:<14} | {safety_status}\n")

                    if sources:
                        f.write("\n" + "-" * 76 + "\n")
                        f.write("SCIENTIFIC CITATIONS & SOURCES:\n")
                        for s in sources:
                            f.write(f"- {s['title']} (PMID: {s['pmid']})\n  URL: {s['url']}\n")

                    f.write("\n" + "=" * 76 + "\n")

                self.notify(f"Saved schedule to: {filename}", timeout=4.0)
                return

            else:
                if selected.startswith("catalog_"):
                    pep_name = selected.replace("catalog_", "")
                    cat = db.get_peptide_by_name(pep_name)
                    vial_mg = cat["vial_mg"] if cat else self.vial_mg
                    water_ml = cat["water_ml"] if cat else self.water_ml
                    schedule_steps = cat["schedule"] if cat and cat.get("schedule") else [("Standard Dose", cat["dose"], cat["unit"])]
                    notes = cat.get("notes", "") if cat else "Catalog protocol."
                    sources = cat.get("sources", []) if cat else []
                    freq = cat.get("freq", "") if cat else ""
                else:
                    pep_name = self.peptide
                    vial_mg = self.vial_mg
                    water_ml = self.water_ml
                    cat = db.get_peptide_by_name(pep_name)
                    schedule_steps = cat["schedule"] if cat and cat.get("schedule") else [("Custom Dose", self.target_dose, self.dose_unit)]
                    notes = cat.get("notes", "") if cat else "Custom protocol."
                    sources = cat.get("sources", []) if cat else []
                    freq = cat.get("freq", "") if cat else ""

                if vial_mg <= 0 or water_ml <= 0:
                    self.notify("Cannot save schedule: Invalid inputs.", severity="error")
                    return

                conc_mg_ml = calc.concentration_mg_ml(vial_mg, water_ml)
                conc_mcg_ml = conc_mg_ml * 1000.0
                weekly_exp = calc.parse_weekly_frequency(freq)

                filename = f"peptide_{pep_name.lower().replace(' ', '_')}_schedule.txt"
                filepath = os.path.join(os.getcwd(), filename)

                with open(filepath, "w") as f:
                    f.write("=" * 76 + "\n")
                    f.write(" PEPTIDE DOSING SCHEDULE & RECONSTITUTION PROTOCOL\n")
                    f.write("=" * 76 + "\n")
                    f.write(f"Peptide Name:         {pep_name}\n")
                    f.write(f"Date Generated:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Vial Strength:        {vial_mg:.1f} mg\n")
                    f.write(f"Reconstitution Water: {water_ml:.1f} mL (Bacteriostatic Water)\n")
                    f.write(f"Concentration:        {conc_mg_ml:.2f} mg/mL ({conc_mcg_ml:,.0f} mcg/mL)\n")
                    f.write(f"Syringe Standard:     U-100 Insulin Syringe (100 Units = 1.0 mL)\n")
                    f.write("-" * 76 + "\n")
                    f.write("Notes & Details:\n")
                    f.write(f"{notes}\n")
                    f.write("-" * 76 + "\n\n")

                    f.write("DOSING SCHEDULE:\n")
                    phase_width = max(24, max((len(phase) for phase, _, _ in schedule_steps), default=24))
                    header = f"{'Phase / Period':<{phase_width}} | {'Dose':<12} | {'Volume':<10} | {'Syringe Draw':<16} | {'Vial Duration':<14} | {'Status'}"
                    f.write(header + "\n")
                    f.write("-" * len(header) + "\n")

                    for phase, dose_val, unit in schedule_steps:
                        dose_mg = calc.dose_to_mg(dose_val, unit)
                        vol_ml = calc.draw_volume_ml(dose_mg, conc_mg_ml)
                        units = calc.syringe_units(vol_ml)
                        doses_per_vial = calc.doses_per_vial(vial_mg, dose_mg)
                        dose_str = f"{dose_val:.0f} mcg" if unit == "mcg" else f"{dose_val:.2f} mg"
                        draw_label, safety_status = calc.syringe_draw_status(units)
                        vial_dur = calc.format_vial_duration(doses_per_vial, weekly_exp, freq)

                        f.write(f"{phase:<{phase_width}} | {dose_str:<12} | {vol_ml:.3f} mL  | {draw_label:<16} | {vial_dur:<14} | {safety_status}\n")

                    if sources:
                        f.write("\n" + "-" * 76 + "\n")
                        f.write("SCIENTIFIC CITATIONS & SOURCES:\n")
                        for s in sources:
                            f.write(f"- {s['title']} (PMID: {s['pmid']})\n  URL: {s['url']}\n")

                    f.write("\n" + "=" * 76 + "\n")

                self.notify(f"Saved schedule to: {filename}", timeout=4.0)

        except Exception as e:
            self.notify(f"Error saving schedule: {str(e)}", severity="error")

    def action_switch_tab(self, tab_id: str) -> None:
        try:
            tabbed = self.query_one(TabbedContent)
            tabbed.active = tab_id
            if tab_id == "calc-tab":
                self.set_focus(self.query_one("#vial-size-input", Input))
            elif tab_id == "patient-tab":
                self.set_focus(self.query_one("#patient-protocols-table", DataTable))
            elif tab_id == "schedule-tab":
                self.set_focus(self.query_one("#schedule-protocol-select", Select))
            elif tab_id == "dose-log-tab":
                self.set_focus(self.query_one("#dose-log-table", DataTable))
            elif tab_id == "reference-tab":
                self.set_focus(self.query_one("#reference-search-input", Input))
            elif tab_id == "literature-tab":
                self.set_focus(self.query_one("#literature-pmid-input", Input))
        except Exception:
            pass

    def action_next_profile(self) -> None:
        profiles = db.get_profiles()
        if not profiles:
            return
        current_ids = [p["id"] for p in profiles]
        try:
            idx = current_ids.index(self.active_profile_id)
            next_id = current_ids[(idx + 1) % len(current_ids)]
        except ValueError:
            next_id = current_ids[0]
        self.active_profile_id = next_id
        self.refresh_active_profile_display()
        prof_name = next((p["name"] for p in profiles if p["id"] == next_id), "Unknown")
        self.notify(f"Switched active person: {prof_name}", timeout=2.5)

    def action_save_schedule(self) -> None:
        self.save_schedule_to_file()

    def action_quick_log_dose(self) -> None:
        try:
            tabbed = self.query_one(TabbedContent)
            active_tab = tabbed.active
        except Exception:
            active_tab = "calc-tab"

        protocols = db.get_user_protocols(self.active_profile_id)
        protocol_id: int | None = None
        peptide_name: str | None = None
        dose_amount: float | None = None
        dose_unit: str = "mcg"

        if active_tab == "calc-tab":
            calc_peptide = self.peptide
            if calc_peptide and calc_peptide != "Custom / Other":
                peptide_name = calc_peptide
                dose_amount = self.target_dose
                dose_unit = self.dose_unit
                match = next((p for p in protocols if p["peptide_name"].strip().lower() == calc_peptide.strip().lower()), None)
                if match:
                    protocol_id = match["id"]
                    if dose_amount <= 0:
                        dose_amount = match["target_dose"]
                        dose_unit = match["dose_unit"]
            elif calc_peptide == "Custom / Other" and self.target_dose > 0:
                peptide_name = "Custom / Other"
                dose_amount = self.target_dose
                dose_unit = self.dose_unit

        elif active_tab == "schedule-tab":
            try:
                sched_select = self.query_one("#schedule-protocol-select", Select)
                sched_val = str(sched_select.value) if sched_select.value != Select.BLANK else "__all__"
            except Exception:
                sched_val = "__all__"

            if sched_val.startswith("protocol_"):
                try:
                    p_id = int(sched_val.replace("protocol_", ""))
                    p = db.get_user_protocol_by_id(p_id)
                    if p:
                        protocol_id = p["id"]
                        peptide_name = p["peptide_name"]
                        dose_amount = p["target_dose"]
                        dose_unit = p["dose_unit"]

                        # Check if a specific titration row is focused/selected in the schedule table
                        sched_table = self.query_one("#schedule-table", DataTable)
                        if sched_table.has_focus and sched_table.cursor_row is not None:
                            steps = p.get("schedule") or []
                            if 0 <= sched_table.cursor_row < len(steps):
                                dose_amount = float(steps[sched_table.cursor_row][1])
                                dose_unit = str(steps[sched_table.cursor_row][2])
                except Exception:
                    pass
            elif sched_val.startswith("catalog_"):
                cat_name = sched_val.replace("catalog_", "")
                match = next((p for p in protocols if p["peptide_name"].strip().lower() == cat_name.strip().lower()), None)
                if match:
                    protocol_id = match["id"]
                    peptide_name = match["peptide_name"]
                    dose_amount = match["target_dose"]
                    dose_unit = match["dose_unit"]
                else:
                    cat = db.get_peptide_by_name(cat_name)
                    if cat:
                        peptide_name = cat["name"]
                        dose_amount = cat["dose"]
                        dose_unit = cat["unit"]
            elif sched_val == "__all__":
                try:
                    sched_table = self.query_one("#schedule-table", DataTable)
                    if sched_table.cursor_row is not None and sched_table.row_count > 0:
                        pep_cell = str(sched_table.get_cell_at((sched_table.cursor_row, 0)))
                        match = next((p for p in protocols if p["peptide_name"].strip().lower() == pep_cell.strip().lower()), None)
                        if match:
                            protocol_id = match["id"]
                            peptide_name = match["peptide_name"]
                            dose_amount = match["target_dose"]
                            dose_unit = match["dose_unit"]
                except Exception:
                    pass

        elif active_tab == "patient-tab":
            table = self.query_one("#patient-protocols-table", DataTable)
            if table.cursor_row is not None and table.row_count > 0:
                try:
                    p_id = int(table.get_cell_at((table.cursor_row, 0)))
                    p = db.get_user_protocol_by_id(p_id)
                    if p:
                        protocol_id = p["id"]
                        peptide_name = p["peptide_name"]
                        dose_amount = p["target_dose"]
                        dose_unit = p["dose_unit"]
                except Exception:
                    pass

        elif active_tab == "dose-log-tab":
            try:
                adh_table = self.query_one("#adherence-table", DataTable)
                dose_table = self.query_one("#dose-log-table", DataTable)
                if adh_table.has_focus and adh_table.cursor_row is not None and adh_table.row_count > 0:
                    pep_name_cell = str(adh_table.get_cell_at((adh_table.cursor_row, 0)))
                    match = next((p for p in protocols if p["peptide_name"].strip().lower() == pep_name_cell.strip().lower()), None)
                    if match:
                        protocol_id = match["id"]
                        peptide_name = match["peptide_name"]
                        dose_amount = match["target_dose"]
                        dose_unit = match["dose_unit"]
                elif dose_table.has_focus and dose_table.cursor_row is not None and dose_table.row_count > 0:
                    pep_name_cell = str(dose_table.get_cell_at((dose_table.cursor_row, 1)))
                    match = next((p for p in protocols if p["peptide_name"].strip().lower() == pep_name_cell.strip().lower()), None)
                    if match:
                        protocol_id = match["id"]
                        peptide_name = match["peptide_name"]
                        dose_amount = match["target_dose"]
                        dose_unit = match["dose_unit"]
            except Exception:
                pass

        # Fallbacks if active tab context did not identify a peptide
        if peptide_name is None:
            # 1. Patient table selection if present
            table = self.query_one("#patient-protocols-table", DataTable)
            if table.cursor_row is not None and table.row_count > 0:
                try:
                    p_id = int(table.get_cell_at((table.cursor_row, 0)))
                    p = db.get_user_protocol_by_id(p_id)
                    if p:
                        protocol_id = p["id"]
                        peptide_name = p["peptide_name"]
                        dose_amount = p["target_dose"]
                        dose_unit = p["dose_unit"]
                except Exception:
                    pass

            # 2. First active protocol for active profile
            if peptide_name is None and protocols:
                p = protocols[0]
                protocol_id = p["id"]
                peptide_name = p["peptide_name"]
                dose_amount = p["target_dose"]
                dose_unit = p["dose_unit"]

            # 3. Calculator peptide if configured
            if peptide_name is None and self.peptide and self.peptide != "Custom / Other":
                peptide_name = self.peptide
                dose_amount = self.target_dose
                dose_unit = self.dose_unit

        if not peptide_name:
            self.notify("No active protocols found to log a dose for.", severity="warning")
            return

        dose_val = f"{dose_amount} " if dose_amount is not None else ""
        dose_desc = f"{peptide_name} {dose_val}{dose_unit}".strip()

        current_profile_id = self.active_profile_id
        final_protocol_id = protocol_id
        final_peptide_name = peptide_name
        final_dose_amount = dose_amount if dose_amount is not None else 0.0
        final_dose_unit = dose_unit

        def handle_notes(notes: str | None) -> None:
            if notes is None:
                return
            db.log_dose(
                current_profile_id,
                final_protocol_id,
                final_peptide_name,
                final_dose_amount,
                final_dose_unit,
                notes,
            )
            self.refresh_dose_log_tables()
            self.notify(f"Logged dose: {dose_desc}", timeout=3.0)

        self.push_screen(LogDoseScreen(f"Log dose: {dose_desc}"), handle_notes)

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())


def run() -> None:
    app = PeptideCalculatorApp()
    app.run()


if __name__ == "__main__":
    run()
