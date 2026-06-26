import os
import sys
from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid, ScrollableContainer
from textual.widgets import (
    Header,
    Footer,
    Input,
    Label,
    Button,
    Select,
    Static,
    DataTable,
    TabbedContent,
    TabPane,
)
from textual.reactive import reactive

# Common peptide database with defaults for auto-filling and scheduling
PEPTIDE_DEFAULTS = {
    "BPC-157": {
        "vial_mg": 5.0,
        "water_ml": 2.0,
        "dose": 250.0,
        "unit": "mcg",
        "freq": "daily",
        "notes": "Commonly used for joint/tendon healing. Standard dose: 250mcg - 500mcg daily or twice daily.",
        "schedule": [
            ("Week 1-2", 250.0, "mcg"),
            ("Week 3-4", 350.0, "mcg"),
            ("Week 5-6", 500.0, "mcg"),
        ]
    },
    "Ipamorelin": {
        "vial_mg": 5.0,
        "water_ml": 2.5,
        "dose": 200.0,
        "unit": "mcg",
        "freq": "daily (before bed)",
        "notes": "Growth hormone secretagogue. Standard dose: 200mcg - 300mcg daily, 5 days on / 2 days off.",
        "schedule": [
            ("Week 1-4", 200.0, "mcg"),
            ("Week 5-8", 250.0, "mcg"),
            ("Week 9-12", 300.0, "mcg"),
        ]
    },
    "CJC-1295": {
        "vial_mg": 2.0,
        "water_ml": 2.0,
        "dose": 100.0,
        "unit": "mcg",
        "freq": "daily",
        "notes": "Often combined with Ipamorelin. Standard dose: 100mcg - 150mcg, 1-3 times daily.",
        "schedule": [
            ("Week 1-8", 100.0, "mcg"),
        ]
    },
    "Semaglutide": {
        "vial_mg": 5.0,
        "water_ml": 2.0,
        "dose": 0.25,
        "unit": "mg",
        "freq": "weekly",
        "notes": "GLP-1 receptor agonist. Standard titration starts at 0.25mg weekly for 4 weeks.",
        "schedule": [
            ("Week 1-4 (Titration)", 0.25, "mg"),
            ("Week 5-8 (Titration)", 0.50, "mg"),
            ("Week 9-12 (Titration)", 1.00, "mg"),
            ("Week 13-16 (Titration)", 1.70, "mg"),
            ("Week 17+ (Maintenance)", 2.40, "mg"),
        ]
    },
    "Tirzepatide": {
        "vial_mg": 10.0,
        "water_ml": 2.0,
        "dose": 2.5,
        "unit": "mg",
        "freq": "weekly",
        "notes": "GIP/GLP-1 receptor agonist. Standard titration starts at 2.5mg weekly for 4 weeks.",
        "schedule": [
            ("Week 1-4 (Titration)", 2.5, "mg"),
            ("Week 5-8 (Titration)", 5.0, "mg"),
            ("Week 9-12 (Titration)", 7.5, "mg"),
            ("Week 13-16 (Titration)", 10.0, "mg"),
            ("Week 17-20 (Titration)", 12.5, "mg"),
            ("Week 21+ (Maintenance)", 15.0, "mg"),
        ]
    },
    "Custom / Other": {
        "vial_mg": 5.0,
        "water_ml": 2.0,
        "dose": 250.0,
        "unit": "mcg",
        "freq": "daily",
        "notes": "Enter custom values below to calculate dilution and syringe markings.",
        "schedule": [
            ("Week 1-4", 250.0, "mcg")
        ]
    }
}

# ASCII syringe drawing helper
def make_syringe_display(units: float) -> str:
    if units <= 0:
        filled = 0
    elif units > 100:
        filled = 50  # Cap at 100 units visually
    else:
        filled = int(round(units / 2.0))  # 50 character width (2 units per char)
        
    empty = 50 - filled
    
    # Plunger stick is '=', plunger rubber tip is '█', liquid is '░', empty is '.'
    stick_len = max(0, filled - 1)
    stick = "=" * stick_len
    rubber = "█" if filled > 0 else ""
    liquid = "░" * max(0, filled - stick_len - 1)
    barrel_content = f"{stick}{rubber}{liquid}{'.' * empty}"
    
    # Ticks and barrel outlines
    top_line = "            0   10   20   30   40   50   60   70   80   90  100 Units"
    mid_line = f" Needle ───┨ {barrel_content} ┠──══════ Plunger"
    
    # Plunger indicator arrow
    marker_pos = 13 + filled
    bottom_line = " " * marker_pos + "▲"
    text_line = " " * max(0, marker_pos - 5) + f"{units:.1f} Units"
    
    warning_text = ""
    if units > 100:
        warning_text = "   [!] EXCEEDS 1.0mL SYRINGE CAPACITY!"
        
    return f"{top_line}\n{mid_line}\n{bottom_line}\n{text_line}{warning_text}"


CSS = """
Screen {
    background: #0f172a;
    color: #e2e8f0;
}

Header {
    background: #1e293b;
    color: #38bdf8;
    text-align: center;
    height: 3;
    border-bottom: tall #38bdf8;
}

Footer {
    background: #1e293b;
    color: #94a3b8;
}

TabbedContent {
    margin-top: 1;
}

.pane-container {
    layout: grid;
    grid-size: 2;
    grid-columns: 1fr 1fr;
    grid-gutter: 2;
    padding: 1 2;
}

.sidebar-panel {
    background: #1e293b;
    border: solid #334155;
    padding: 1 2;
    border-radius: 4;
}

.results-panel {
    background: #1e293b;
    border: solid #334155;
    padding: 1 2;
    border-radius: 4;
    layout: vertical;
}

.title-label {
    color: #38bdf8;
    text-style: bold;
    font-size: 110%;
    margin-bottom: 1;
    border-bottom: thin #334155;
    padding-bottom: 1;
}

.input-label {
    text-style: bold;
    margin-top: 1;
    color: #cbd5e1;
}

.preset-row {
    layout: horizontal;
    height: 3;
    margin-bottom: 1;
    margin-top: 1;
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
    margin-bottom: 1;
}

Input:focus {
    border: double #38bdf8;
}

Select {
    background: #0f172a;
    border: solid #475569;
    color: #f1f5f9;
    margin-bottom: 1;
}

Select:focus {
    border: double #38bdf8;
}

.result-row {
    layout: horizontal;
    height: 3;
    content-align: left middle;
    border-bottom: thin #334155;
}

.result-label {
    width: 25;
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
    padding: 1;
    margin-top: 1;
    margin-bottom: 1;
    height: 9;
    color: #38bdf8;
}

.help-box {
    background: #1e293b;
    border: solid #334155;
    padding: 1;
    margin-top: 1;
    color: #94a3b8;
    font-size: 85%;
}

.schedule-header {
    layout: horizontal;
    height: 5;
    align: space-between middle;
    padding: 1 2;
    background: #1e293b;
    border-bottom: solid #334155;
}

.schedule-title {
    color: #38bdf8;
    text-style: bold;
    font-size: 110%;
}

DataTable {
    height: 1fr;
    border: solid #334155;
    background: #0f172a;
    margin: 1 2;
}

.info-pane {
    padding: 1 2;
    layout: vertical;
}

.info-section {
    background: #1e293b;
    border: solid #334155;
    padding: 1 2;
    margin-bottom: 1;
    border-radius: 4;
}

.info-title {
    color: #38bdf8;
    text-style: bold;
    margin-bottom: 1;
}

.info-text {
    color: #cbd5e1;
    margin-bottom: 1;
    line-height: 1.4;
}

#save-schedule-btn {
    background: #10b981;
    color: #0f172a;
    text-style: bold;
    min-width: 25;
}

#save-schedule-btn:hover {
    background: #059669;
}
"""


class PeptideCalculatorApp(App):
    TITLE = "Peptide Dosage & Reconstitution TUI"
    SUB_TITLE = "Calculate dilutions, doses, and syringe draws accurately"
    CSS = CSS

    # Reactive variables for calculation state
    peptide = reactive("Custom / Other")
    vial_mg = reactive(5.0)
    water_ml = reactive(2.0)
    target_dose = reactive(250.0)
    dose_unit = reactive("mcg")

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Calculator & Syringe Visualizer"):
                with Grid(classes="pane-container"):
                    # Left Sidebar: Inputs
                    with Vertical(classes="sidebar-panel"):
                        yield Label("PEPTIDE CONFIGURATION", classes="title-label")
                        
                        yield Label("Select Peptide Template:", classes="input-label")
                        yield Select(
                            options=[(name, name) for name in PEPTIDE_DEFAULTS.keys()],
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
                        yield Input(value="5.0", placeholder="Enter mg...", id="vial-size-input")
                        
                        yield Label("Bacteriostatic Water (mL added):", classes="input-label")
                        with Horizontal(classes="preset-row"):
                            yield Button("1mL", id="water-btn-1")
                            yield Button("2mL", id="water-btn-2")
                            yield Button("2.5mL", id="water-btn-2.5")
                            yield Button("3mL", id="water-btn-3")
                        yield Input(value="2.0", placeholder="Enter mL...", id="water-input")
                        yield Label(
                            "Guidelines: GLP-1s: 2mL-3mL | Peptides: 3mL\n"
                            "Note: Higher water = lower concentration, making small doses easier to draw.",
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

                    # Right Panel: Output & Visualizer
                    with Vertical(classes="results-panel"):
                        yield Label("DILUTION & CALCULATED DOSES", classes="title-label")
                        
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
                        
                        yield Label(
                            "Safety Warning:\n"
                            "Always inject BAC water slowly down the vial side. Do not shake. Gently swirl.\n"
                            "Keep reconstituted peptides refrigerated. Protect from light.",
                            classes="help-box"
                        )

            with TabPane("Dosing Schedule Planner"):
                with Vertical():
                    with Container(classes="schedule-header"):
                        yield Label("Dosing Schedule Planner & Exporter", classes="schedule-title")
                        yield Button("Save Schedule to File", id="save-schedule-btn")
                    yield DataTable(id="schedule-table")

            with TabPane("Peptide Reference & Tips"):
                with ScrollableContainer(classes="info-pane"):
                    with Vertical(classes="info-section"):
                        yield Label("BPC-157 & TB-500 (Healing & Recovery)", classes="info-title")
                        yield Label(
                            "• BPC-157 Typical Dose: 250 mcg to 500 mcg, once or twice daily.\n"
                            "• TB-500 Typical Dose: 2 mg to 5 mg, once or twice weekly.\n"
                            "• Reconstitution: 2.0 mL to 3.0 mL of BAC water. Inject slowly down vial wall.\n"
                            "• Storage: Refrigerate after reconstitution. Valid for ~30 days.",
                            classes="info-text"
                        )
                    with Vertical(classes="info-section"):
                        yield Label("Ipamorelin & CJC-1295 (GH Secretagogues)", classes="info-title")
                        yield Label(
                            "• CJC-1295 Standard Dose: 100 mcg to 150 mcg daily (before bed or morning).\n"
                            "• Ipamorelin Standard Dose: 200 mcg to 300 mcg daily.\n"
                            "• Synergy: Often combined in a 1:1 or 1:2 ratio. Standard cycle: 8-12 weeks.\n"
                            "• Reconstitution: 2.0 mL to 2.5 mL per 5mg vial.",
                            classes="info-text"
                        )
                    with Vertical(classes="info-section"):
                        yield Label("GLP-1 Receptor Agonists (Weight Management)", classes="info-title")
                        yield Label(
                            "• Semaglutide weekly titration: Weeks 1-4: 0.25mg | Weeks 5-8: 0.5mg | Weeks 9-12: 1.0mg | Weeks 13-16: 1.7mg | Weeks 17+: 2.4mg.\n"
                            "• Tirzepatide weekly titration: Weeks 1-4: 2.5mg | Weeks 5-8: 5mg | Weeks 9-12: 7.5mg | Weeks 13-16: 10mg | Weeks 17-20: 12.5mg | Weeks 21+: 15mg.\n"
                            "• Reconstitution: 2.0 mL to 3.0 mL BAC water per vial to ensure comfortable syringe draws.",
                            classes="info-text"
                        )
        yield Footer()

    def on_mount(self) -> None:
        # Initialize schedule table headers
        table = self.query_one("#schedule-table", DataTable)
        table.add_columns("Phase / Week", "Dose", "Volume (mL)", "Syringe Draw (Units)", "Est. Doses per Vial")
        
        # Initial run of calculations
        self.recalculate()
        self.update_schedule_table()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "peptide-select":
            self.peptide = str(event.value)
            if self.peptide in PEPTIDE_DEFAULTS:
                defaults = PEPTIDE_DEFAULTS[self.peptide]
                self.query_one("#vial-size-input", Input).value = f"{defaults['vial_mg']}"
                self.query_one("#water-input", Input).value = f"{defaults['water_ml']}"
                self.query_one("#dose-input", Input).value = f"{defaults['dose']}"
                self.query_one("#dose-unit-select", Select).value = defaults["unit"]
                
                # Update reactive variables directly in case input change fails to trigger
                self.vial_mg = defaults['vial_mg']
                self.water_ml = defaults['water_ml']
                self.target_dose = defaults['dose']
                self.dose_unit = defaults['unit']
        elif event.select.id == "dose-unit-select":
            self.dose_unit = str(event.value)
            
        self.recalculate()
        self.update_schedule_table()

    def on_input_changed(self, event: Input.Changed) -> None:
        try:
            val = float(event.input.value) if event.input.value else 0.0
            if event.input.id == "vial-size-input":
                self.vial_mg = val
            elif event.input.id == "water-input":
                self.water_ml = val
            elif event.input.id == "dose-input":
                self.target_dose = val
        except ValueError:
            # Ignore intermediate parsing errors when user is typing
            pass
            
        self.recalculate()
        self.update_schedule_table()

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
            self.query_one("#water-input", Input).value = val
            self.water_ml = float(val)
        elif btn_id == "save-schedule-btn":
            self.save_schedule_to_file()
            
        self.recalculate()
        self.update_schedule_table()

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

            # Calc concentration
            conc_mg_ml = vial_mg / water_ml
            conc_mcg_ml = conc_mg_ml * 1000.0

            # Calc dose
            if unit == "mcg":
                dose_mg = dose / 1000.0
            else:
                dose_mg = dose

            # Draw volume
            draw_volume_ml = dose_mg / conc_mg_ml
            syringe_units = draw_volume_ml * 100.0
            doses_per_vial = vial_mg / dose_mg

            # Update fields
            self.query_one("#calc-concentration", Label).update(
                f"{conc_mg_ml:.2f} mg/mL ({conc_mcg_ml:,.0f} mcg/mL)"
            )
            self.query_one("#calc-dose-volume", Label).update(f"{draw_volume_ml:.3f} mL")
            
            if syringe_units > 100.0:
                self.query_one("#calc-syringe-draw", Label).update(
                    f"{syringe_units:.1f} Units [bold red](Exceeds Syringe Capacity!)[/]"
                )
            else:
                self.query_one("#calc-syringe-draw", Label).update(f"{syringe_units:.1f} Units")
                
            self.query_one("#calc-doses-per-vial", Label).update(f"{doses_per_vial:.1f} doses")
            
            # Update visual syringe
            syringe_ascii = make_syringe_display(syringe_units)
            self.query_one("#syringe-visual", Label).update(syringe_ascii)
            
        except Exception as e:
            # Prevent crashes if elements are not mounted yet
            pass

    def update_schedule_table(self) -> None:
        try:
            table = self.query_one("#schedule-table", DataTable)
            table.clear()
            
            # Get schedule template based on selected peptide or default custom
            peptide_name = self.peptide
            vial_mg = self.vial_mg
            water_ml = self.water_ml
            
            if vial_mg <= 0 or water_ml <= 0:
                return
                
            conc_mg_ml = vial_mg / water_ml
            
            # If peptide is in defaults, retrieve its schedule, otherwise make a simple one
            if peptide_name in PEPTIDE_DEFAULTS and peptide_name != "Custom / Other":
                schedule_steps = PEPTIDE_DEFAULTS[peptide_name]["schedule"]
            else:
                schedule_steps = [("Custom Dose", self.target_dose, self.dose_unit)]
                
            for phase, dose_val, unit in schedule_steps:
                if unit == "mcg":
                    dose_mg = dose_val / 1000.0
                    dose_str = f"{dose_val:.0f} mcg"
                else:
                    dose_mg = dose_val
                    dose_str = f"{dose_val:.2f} mg"
                    
                vol_ml = dose_mg / conc_mg_ml
                units = vol_ml * 100.0
                doses_per_vial = vial_mg / dose_mg if dose_mg > 0 else 0.0
                
                table.add_row(
                    phase,
                    dose_str,
                    f"{vol_ml:.3f} mL",
                    f"{units:.1f} Units",
                    f"{doses_per_vial:.1f} doses"
                )
        except Exception as e:
            pass

    def save_schedule_to_file(self) -> None:
        try:
            peptide_name = self.peptide
            vial_mg = self.vial_mg
            water_ml = self.water_ml
            
            if vial_mg <= 0 or water_ml <= 0:
                self.notify("Cannot save schedule: Invalid inputs.", severity="error")
                return
                
            conc_mg_ml = vial_mg / water_ml
            conc_mcg_ml = conc_mg_ml * 1000.0
            
            if peptide_name in PEPTIDE_DEFAULTS and peptide_name != "Custom / Other":
                schedule_steps = PEPTIDE_DEFAULTS[peptide_name]["schedule"]
                notes = PEPTIDE_DEFAULTS[peptide_name]["notes"]
            else:
                schedule_steps = [("Custom Dose", self.target_dose, self.dose_unit)]
                notes = "Custom user protocol."
                
            # Construct file output
            filename = f"peptide_{peptide_name.lower().replace(' ', '_')}_schedule.txt"
            filepath = os.path.join(os.getcwd(), filename)
            
            with open(filepath, "w") as f:
                f.write("=" * 68 + "\n")
                f.write(" PEPTIDE DOSING SCHEDULE & RECONSTITUTION PROTOCOL\n")
                f.write("=" * 68 + "\n")
                f.write(f"Peptide Name:         {peptide_name}\n")
                f.write(f"Date Generated:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Vial Strength:        {vial_mg:.1f} mg\n")
                f.write(f"Reconstitution Water: {water_ml:.1f} mL (Bacteriostatic Water)\n")
                f.write(f"Concentration:        {conc_mg_ml:.2f} mg/mL ({conc_mcg_ml:,.0f} mcg/mL)\n")
                f.write(f"Syringe Standard:     U-100 Insulin Syringe (100 Units = 1.0 mL)\n")
                f.write("-" * 68 + "\n")
                f.write("Notes & Details:\n")
                f.write(f"{notes}\n")
                f.write("-" * 68 + "\n\n")
                
                f.write("DOSING SCHEDULE:\n")
                f.write(f"{'Phase / Period':<22} | {'Dose':<12} | {'Volume (mL)':<12} | {'Syringe Draw (U-100)':<20}\n")
                f.write("-" * 68 + "\n")
                
                for phase, dose_val, unit in schedule_steps:
                    if unit == "mcg":
                        dose_mg = dose_val / 1000.0
                        dose_str = f"{dose_val:.0f} mcg"
                    else:
                        dose_mg = dose_val
                        dose_str = f"{dose_val:.2f} mg"
                        
                    vol_ml = dose_mg / conc_mg_ml
                    units = vol_ml * 100.0
                    
                    f.write(f"{phase:<22} | {dose_str:<12} | {vol_ml:.3f} mL    | {units:.1f} Units\n")
                    
                f.write("-" * 68 + "\n\n")
                f.write("RECONSTITUTION & STORAGE GUIDELINES:\n")
                f.write("1. Preparation:\n")
                f.write("   - Clean the rubber tops of both the BAC water and peptide vials with alcohol.\n")
                f.write("   - Use a sterile syringe to draw the bacteriostatic water.\n")
                f.write("2. Reconstitution:\n")
                f.write("   - Slowly inject the water into the peptide vial, aiming at the glass wall.\n")
                f.write("   - DO NOT SHAKE the vial. Shaking damages fragile peptide structures.\n")
                f.write("   - Gently swirl the vial until the powder completely dissolves.\n")
                f.write("3. Storage & Care:\n")
                f.write("   - Store reconstituted peptide in the refrigerator at 36°F to 46°F (2°C to 8°C).\n")
                f.write("   - Protect the vial from direct sunlight and extreme temperatures.\n")
                f.write("   - Reconstituted peptides are generally stable for 30 days under refrigeration.\n")
                f.write("\n" + "=" * 68 + "\n")
                f.write("Disclaimer: For research/educational reference only. Consult a physician.\n")
                f.write("=" * 68 + "\n")
                
            self.notify(f"Saved schedule to: {filename}", timeout=4.0)
            
        except Exception as e:
            self.notify(f"Error saving schedule: {str(e)}", severity="error")


if __name__ == "__main__":
    app = PeptideCalculatorApp()
    app.run()
