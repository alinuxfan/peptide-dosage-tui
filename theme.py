"""
theme.py -- Dynamic CSS generator driven by Omarchy theme colors.

Omarchy writes its current palette to ~/.config/omarchy/current/theme/colors.toml
and the active theme slug to ~/.config/omarchy/current/theme.
This module reads that palette and injects it into every screen's stylesheet.
If Omarchy is not present or the file cannot be read, sensible dark-mode defaults
are used so the app looks great anywhere.
"""

import os
import tomllib
from pathlib import Path

# Paths managed by Omarchy
_OMARCHY_BASE = Path.home() / ".config" / "omarchy" / "current"
_THEME_FILE   = _OMARCHY_BASE / "theme"
_COLORS_FILE  = _OMARCHY_BASE / "theme" / "colors.toml"

# Fallback palette -- clean, high-contrast dark theme inspired by Tokyo Night / Catppuccin
_DEFAULTS = {
    "background":         "#0f172a",  # slate-900: deep dark background
    "lighter_background": "#1e293b",  # slate-800: panels, modals, inputs
    "selection":          "#334155",  # slate-700: borders, active rows, dividers
    "foreground":         "#f8fafc",  # slate-50:  primary readable text
    "bright_foreground":  "#ffffff",  # pure white: headers, highlights
    "dark_foreground":    "#94a3b8",  # slate-400: secondary text, labels, hints
    "accent":             "#38bdf8",  # sky-400:   brand color, visualizer, buttons
    "muted":              "#475569",  # slate-600: subtle borders, inactive buttons
    "red":                "#f43f5e",  # rose-500:  destructive actions, warnings
    "green":              "#10b981",  # emerald-500: success, confirmations
    "yellow":             "#f59e0b",  # amber-500: caution, alerts
    "mode":               "dark",
}


def load_palette() -> dict:
    """Read Omarchy's colors.toml, falling back to _DEFAULTS on any error."""
    try:
        if not _COLORS_FILE.exists():
            return dict(_DEFAULTS)
        with open(_COLORS_FILE, "rb") as f:
            data = tomllib.load(f)
        # Flatten: colors.toml commonly has [colors] section
        colors = data.get("colors", data)
        palette = dict(_DEFAULTS)
        for k in _DEFAULTS:
            if k in colors:
                palette[k] = str(colors[k])
        # Also check mode (light vs dark) if specified
        if "mode" in data:
            palette["mode"] = str(data["mode"])
        return palette
    except Exception:
        return dict(_DEFAULTS)


def get_current_theme_slug() -> str:
    """Return the active theme name (e.g. 'catppuccin-mocha'), or '' if unknown."""
    try:
        if _THEME_FILE.is_symlink():
            return Path(os.readlink(_THEME_FILE)).name
        if _THEME_FILE.is_file():
            return _THEME_FILE.read_text().strip()
    except Exception:
        pass
    return ""


# State cache for live reload detection
_last_slug: str = get_current_theme_slug()


def theme_changed_on_disk() -> bool:
    """True if Omarchy switched themes since this was last checked."""
    global _last_slug
    current = get_current_theme_slug()
    if current and current != _last_slug:
        _last_slug = current
        return True
    return False


# ---------------------------------------------------------------------------
# Stylesheet generators
# ---------------------------------------------------------------------------

def _hex(color_str: str) -> str:
    """Ensure a color string is a valid hex color (#rrggbb)."""
    color_str = color_str.strip()
    if not color_str.startswith("#"):
        color_str = f"#{color_str}"
    return color_str


def build_main_css(c: dict) -> str:
    """Generate the root stylesheet for PeptideCalculatorApp."""
    bg        = c["background"]
    bg_light  = c["lighter_background"]
    sel       = c["selection"]
    fg        = c["foreground"]
    fg_bright = c["bright_foreground"]
    fg_muted  = c["dark_foreground"]
    muted     = c["muted"]
    accent    = c["accent"]
    red       = c["red"]
    green     = c["green"]
    yellow    = c.get("yellow", "#f59e0b")

    return f"""
Screen {{
    background: {bg};
    color: {fg};
}}

Header {{
    background: {bg_light};
    color: {fg_bright};
    dock: top;
    height: 1;
}}

Footer {{
    background: {bg_light};
    color: {fg_muted};
    dock: bottom;
    height: 1;
}}

.global-profile-bar {{
    background: {bg_light};
    height: 3;
    padding: 0 1;
    align: left middle;
    border-bottom: solid {sel};
}}

TabbedContent {{
    height: 1fr;
}}

Tabs {{
    background: {bg_light};
}}

Tabs .underline--bar {{
    color: {accent};
    background: {accent};
}}

Tabs:focus .underline--bar {{
    color: {accent};
    background: {accent};
}}

ContentTab {{
    background: {bg_light};
    color: {fg_muted};
    padding: 0 2;
}}

ContentTab:hover {{
    background: {sel};
    color: {fg_bright};
}}

ContentTab.-active {{
    background: {accent};
    color: {bg};
    text-style: bold;
}}

Tabs:focus ContentTab.-active {{
    background: {accent};
    color: {bg};
    text-style: bold;
}}

TabPane {{
    padding: 0;
    height: 1fr;
}}

.pane-container {{
    grid-size: 2;
    grid-columns: 1fr 1fr;
    height: 100%;
    padding: 0;
}}

.sidebar-panel {{
    padding: 1 2;
    height: 100%;
    border-right: solid {sel};
    background: {bg};
}}

.results-panel {{
    padding: 1 2;
    height: 100%;
    background: {bg};
}}

.title-label {{
    text-style: bold;
    color: {accent};
    margin-top: 1;
    margin-bottom: 1;
    border-bottom: solid {sel};
}}

.action-title {{
    color: {fg_bright};
    text-style: bold;
    margin-right: 1;
    height: 3;
    content-align: left middle;
}}

.input-label {{
    color: {fg_muted};
    margin-top: 1;
}}

.preset-row {{
    layout: horizontal;
    height: 3;
    margin-bottom: 1;
}}

.preset-row Button {{
    min-width: 6;
    margin-right: 1;
    height: 3;
    background: {sel};
    color: {fg_bright};
    border: none;
}}

.preset-row Button:hover {{
    background: {accent};
    color: {bg};
}}

Input {{
    background: {bg_light};
    color: {fg_bright};
    border: solid {sel};
    margin-bottom: 1;
    height: 3;
}}

Input:focus {{
    border: solid {accent};
}}

Select {{
    margin-bottom: 0;
    height: 3;
}}

SelectCurrent {{
    background: {bg_light};
    color: {fg_bright};
    border: solid {sel};
}}

SelectionList {{
    background: {bg_light};
    color: {fg};
    border: solid {sel};
    height: 5;
    margin-bottom: 1;
}}

.help-box {{
    color: {fg_muted};
    margin-bottom: 1;
}}

.result-row {{
    layout: horizontal;
    height: 3;
    align: left middle;
    border-bottom: dashed {sel};
}}

.result-label {{
    width: 30;
    color: {fg_muted};
}}

.result-val {{
    color: {fg_bright};
    text-style: bold;
}}

.highlight-val {{
    color: {accent};
}}

.hero-card {{
    background: {bg};
    border: double {accent};
    padding: 1;
    margin-top: 1;
    margin-bottom: 1;
    height: auto;
    content-align: center middle;
}}

.hero-title {{
    color: {fg_muted};
    text-style: bold;
    text-align: center;
}}

.hero-value {{
    color: {accent};
    text-style: bold;
    text-align: center;
}}

#calc-safety-badge {{
    text-align: center;
    color: {green};
    text-style: bold;
    height: auto;
    margin-top: 0;
}}

#calc-edit-mode-banner {{
    background: {sel};
    color: {accent};
    text-style: bold;
    padding: 0 1;
    margin-top: 1;
    margin-bottom: 0;
    height: auto;
    border-left: wide {accent};
}}

#syringe-visual {{
    background: {bg};
    border: solid {sel};
    padding: 0 1;
    margin-top: 0;
    margin-bottom: 1;
    height: 5;
    color: {accent};
}}

.action-bar {{
    layout: horizontal;
    height: 3;
    align: left middle;
    padding: 0 1;
    background: {bg_light};
    border-bottom: solid {sel};
}}

.action-bar Button {{
    margin-left: 1;
    height: 3;
}}

.action-bar Input {{
    width: 40;
    margin-bottom: 0;
    margin-right: 1;
}}

.action-bar Select {{
    width: 30;
    margin-bottom: 0;
    margin-right: 1;
}}

.ambient-status {{
    color: {fg_bright};
    margin-left: 2;
    height: auto;
    content-align: left middle;
}}

.patient-controls-bar {{
    layout: vertical;
    padding: 0 1;
    background: {bg_light};
    border-bottom: solid {sel};
    height: auto;
}}

.control-row {{
    layout: horizontal;
    height: 3;
    align: left middle;
    margin-bottom: 0;
}}

.quick-action-row {{
    layout: horizontal;
    height: 3;
    align: left middle;
    margin-top: 1;
    margin-bottom: 1;
}}

.action-hint-bar {{
    color: {fg_muted};
    margin-left: 1;
    margin-top: 0;
    margin-bottom: 1;
    height: auto;
}}

.empty-state-banner {{
    background: {bg};
    border: dashed {sel};
    color: {fg_muted};
    padding: 1 2;
    margin: 1;
    height: auto;
    text-align: center;
}}

.adherence-progress-bar {{
    color: {accent};
    text-style: bold;
    margin-top: 0;
    margin-bottom: 0;
    padding: 0 1;
    height: auto;
}}

#profile-select {{
    width: 25;
    margin-right: 1;
}}

#new-profile-input {{
    width: 20;
    margin-bottom: 0;
    margin-right: 1;
}}

#patient-add-peptide-select {{
    width: 30;
    margin-bottom: 0;
    margin-right: 1;
}}

.schedule-controls-bar {{
    layout: vertical;
    padding: 0 1;
    background: {bg_light};
    border-bottom: solid {sel};
    height: 6;
}}

#schedule-protocol-select {{
    width: 42;
    margin-bottom: 0;
    margin-right: 1;
}}

.schedule-banner-row {{
    layout: horizontal;
    height: 3;
    align: left middle;
}}

#schedule-banner-text {{
    color: {accent};
    text-style: bold;
    height: 3;
    content-align: left middle;
}}

DataTable {{
    background: {bg};
    color: {fg};
    height: 1fr;
    margin: 0 1;
}}

DataTable > .datatable--cursor {{
    background: {sel};
    color: {fg_bright};
    text-style: bold;
}}

.info-pane {{
    padding: 1 2;
    height: 100%;
    background: {bg};
}}

.info-section {{
    height: auto;
    margin-bottom: 1;
    padding-bottom: 1;
    border-bottom: solid {sel};
}}

.info-title {{
    color: {accent};
    text-style: bold;
    margin-bottom: 0;
}}

.info-text {{
    color: {fg};
}}

.source-link {{
    color: {accent};
    margin-left: 2;
}}

.track-sources-btn {{
    background: {sel};
    color: {accent};
    margin-left: 2;
    margin-top: 1;
    height: 3;
    min-width: 26;
}}

.track-sources-btn:hover {{
    background: {accent};
    color: {bg};
}}

#literature-pmid-input {{
    width: 26;
    margin-bottom: 0;
    margin-right: 1;
}}

#literature-table {{
    height: 12;
    margin: 0 1;
}}

#literature-status {{
    padding: 0 1;
    height: 1;
    color: {fg_muted};
}}

#save-profile-protocol-btn {{
    background: {accent};
    color: {bg};
    text-style: bold;
    margin-top: 1;
    width: 100%;
    height: 3;
}}

#delete-protocol-btn, #remove-profile-btn, #delete-log-btn, #delete-literature-btn {{
    background: {red};
    color: {fg_bright};
    text-style: bold;
    min-width: 16;
    margin-left: 1;
    height: 3;
}}

#add-profile-btn, #quick-add-peptide-btn, #save-schedule-btn, #split-vial-btn {{
    background: {sel};
    color: {fg_bright};
    min-width: 14;
    margin-left: 1;
    height: 3;
}}

#split-vial-btn {{
    margin-top: 1;
    width: 100%;
}}

#export-dose-log-csv-btn, #export-patient-sheet-btn {{
    background: {sel};
    color: {fg_bright};
    min-width: 14;
    margin-left: 1;
    height: 3;
}}

#edit-protocol-btn, #view-schedule-btn, #generate-titration-btn {{
    background: {sel};
    color: {fg_bright};
    min-width: 16;
    margin-left: 1;
    height: 3;
}}

#mark-reconstituted-btn, #edit-log-btn, #fetch-literature-btn {{
    background: {accent};
    color: {bg};
    text-style: bold;
    min-width: 16;
    margin-left: 1;
    height: 3;
}}

#log-dose-btn {{
    background: {green};
    color: {bg};
    text-style: bold;
    min-width: 16;
    margin-left: 1;
    height: 3;
}}

#adherence-table {{
    height: 9;
    margin: 0 1;
}}
"""


def build_confirm_css(c: dict) -> str:
    """Stylesheet for ConfirmScreen modal."""
    bg_light  = c["lighter_background"]
    fg_bright = c["bright_foreground"]
    sel       = c["selection"]
    red       = c["red"]

    return f"""
ConfirmScreen {{
    align: center middle;
}}

#confirm-dialog {{
    width: 52;
    height: auto;
    background: {bg_light};
    border: solid {red};
    padding: 1 2;
}}

#confirm-title {{
    color: {red};
    text-style: bold;
    text-align: center;
    margin-bottom: 1;
}}

#confirm-prompt {{
    color: {fg_bright};
    text-align: center;
    margin-bottom: 1;
}}

#confirm-btn-row {{
    layout: horizontal;
    height: 3;
    align: center middle;
}}

#confirm-btn-row Button {{
    min-width: 12;
    margin: 0 1;
}}

#confirm-yes {{
    background: {red};
    color: {fg_bright};
    text-style: bold;
}}

#confirm-no {{
    background: {sel};
    color: {fg_bright};
}}
"""


def build_log_dose_css(c: dict) -> str:
    """Stylesheet for LogDoseScreen modal."""
    bg_light  = c["lighter_background"]
    fg_bright = c["bright_foreground"]
    fg_muted  = c["dark_foreground"]
    sel       = c["selection"]
    accent    = c["accent"]
    green     = c["green"]
    red       = c["red"]

    return f"""
LogDoseScreen {{
    align: center middle;
}}

#log-dose-dialog {{
    width: 60;
    height: auto;
    background: {bg_light};
    border: solid {accent};
    padding: 1 2;
}}

#log-dose-title {{
    color: {accent};
    text-style: bold;
    text-align: center;
    margin-bottom: 1;
}}

#log-dose-time-label, #log-dose-notes-label {{
    color: {fg_muted};
    margin-top: 1;
}}

#log-dose-time-input, #log-dose-notes-input {{
    margin-bottom: 1;
}}

#log-dose-status {{
    color: {red};
    text-align: center;
    margin-bottom: 1;
    height: 1;
}}

#log-dose-btn-row {{
    layout: horizontal;
    height: 3;
    align: center middle;
}}

#log-dose-btn-row Button {{
    min-width: 14;
    margin: 0 1;
}}

#log-dose-submit-btn {{
    background: {green};
    color: {bg_light};
    text-style: bold;
}}

#log-dose-cancel-btn {{
    background: {sel};
    color: {fg_bright};
}}
"""


def build_edit_dose_css(c: dict) -> str:
    """Stylesheet for EditDoseScreen modal."""
    bg_light  = c["lighter_background"]
    fg_bright = c["bright_foreground"]
    fg_muted  = c["dark_foreground"]
    sel       = c["selection"]
    accent    = c["accent"]
    red       = c["red"]

    return f"""
EditDoseScreen {{
    align: center middle;
}}

#edit-dose-dialog {{
    width: 60;
    height: auto;
    background: {bg_light};
    border: solid {accent};
    padding: 1 2;
}}

#edit-dose-title {{
    color: {accent};
    text-style: bold;
    text-align: center;
    margin-bottom: 1;
}}

#edit-dose-amount-label, #edit-dose-time-label, #edit-dose-notes-label {{
    color: {fg_muted};
    margin-top: 1;
}}

#edit-dose-amount-row {{
    layout: horizontal;
    height: 3;
    margin-bottom: 1;
}}

#edit-dose-amount-input {{
    width: 35;
    margin-bottom: 0;
}}

#edit-dose-unit-select {{
    width: 17;
    margin-left: 1;
    margin-bottom: 0;
}}

#edit-dose-time-input, #edit-dose-notes-input {{
    margin-bottom: 1;
}}

#edit-dose-status {{
    color: {red};
    text-align: center;
    margin-bottom: 1;
    height: 1;
}}

#edit-dose-btn-row {{
    layout: horizontal;
    height: 3;
    align: center middle;
}}

#edit-dose-btn-row Button {{
    min-width: 14;
    margin: 0 1;
}}

#edit-dose-save-btn {{
    background: {accent};
    color: {bg_light};
    text-style: bold;
}}

#edit-dose-cancel-btn {{
    background: {sel};
    color: {fg_bright};
}}
"""


def build_titration_css(c: dict) -> str:
    """Stylesheet for TitrationGeneratorScreen modal."""
    bg        = c["background"]
    bg_light  = c["lighter_background"]
    fg_bright = c["bright_foreground"]
    fg_muted  = c["dark_foreground"]
    sel       = c["selection"]
    accent    = c["accent"]
    red       = c["red"]

    return f"""
TitrationGeneratorScreen {{
    align: center middle;
}}

#titration-dialog {{
    width: 76;
    height: 32;
    background: {bg_light};
    border: solid {accent};
    padding: 1 2;
}}

#titration-title {{
    color: {accent};
    text-style: bold;
    text-align: center;
    margin-bottom: 1;
}}

#titration-start-label, #titration-target-label, #titration-weeks-label, #titration-freq-label {{
    color: {fg_muted};
    margin-top: 1;
}}

.titration-input-row {{
    layout: horizontal;
    height: 3;
    margin-bottom: 1;
}}

#titration-start-input, #titration-target-input {{
    width: 48;
    margin-bottom: 0;
}}

#titration-start-unit-select, #titration-target-unit-select {{
    width: 20;
    margin-left: 1;
    margin-bottom: 0;
}}

#titration-weeks-input {{
    width: 24;
    margin-bottom: 0;
}}

#titration-freq-select {{
    width: 44;
    margin-left: 1;
    margin-bottom: 0;
}}

#titration-preview-label {{
    color: {accent};
    text-style: bold;
    margin-top: 1;
    margin-bottom: 0;
}}

#titration-preview-scroll {{
    height: 8;
    background: {bg};
    border: solid {sel};
    padding: 0 1;
    margin-bottom: 1;
}}

#titration-preview-text {{
    color: {fg_bright};
}}

#titration-status {{
    color: {red};
    text-align: center;
    margin-bottom: 1;
    height: 1;
}}

#titration-btn-row {{
    layout: horizontal;
    height: 3;
    align: center middle;
}}

#titration-btn-row Button {{
    min-width: 14;
    margin: 0 1;
}}

#titration-save-btn {{
    background: {accent};
    color: {bg_light};
    text-style: bold;
}}

#titration-cancel-btn {{
    background: {sel};
    color: {fg_bright};
}}
"""


def build_split_vial_css(c: dict) -> str:
    """Stylesheet for VialSplitScreen modal."""
    bg        = c["background"]
    bg_light  = c["lighter_background"]
    fg_bright = c["bright_foreground"]
    fg_muted  = c["dark_foreground"]
    sel       = c["selection"]
    accent    = c["accent"]
    red       = c["red"]

    return f"""
VialSplitScreen {{
    align: center middle;
}}

#split-dialog {{
    width: 68;
    height: auto;
    background: {bg_light};
    border: solid {accent};
    padding: 1 2;
}}

#split-title {{
    color: {accent};
    text-style: bold;
    text-align: center;
    margin-bottom: 1;
}}

#split-info-label, #split-count-label {{
    color: {fg_muted};
    margin-top: 1;
}}

#split-count-input {{
    margin-bottom: 1;
}}

#split-results {{
    background: {bg};
    border: solid {sel};
    padding: 1 2;
    margin-top: 1;
    margin-bottom: 1;
    height: auto;
    color: {fg_bright};
}}

#split-status {{
    color: {red};
    text-align: center;
    margin-bottom: 1;
    height: 1;
}}

#split-btn-row {{
    layout: horizontal;
    height: 3;
    align: center middle;
}}

#split-btn-row Button {{
    min-width: 14;
    margin: 0 1;
}}

#split-close-btn {{
    background: {sel};
    color: {fg_bright};
}}
"""


def build_help_css(c: dict) -> str:
    """Stylesheet for HelpScreen modal."""
    bg_light  = c["lighter_background"]
    fg        = c["foreground"]
    accent    = c["accent"]
    sel       = c["selection"]
    fg_muted  = c["dark_foreground"]

    return f"""
HelpScreen {{
    align: center middle;
}}

#help-dialog {{
    width: 82;
    height: auto;
    background: {bg_light};
    border: solid {accent};
    padding: 1 2;
}}

#help-title {{
    color: {accent};
    text-style: bold;
    margin-bottom: 1;
    text-align: center;
}}

.help-category {{
    color: {accent};
    text-style: bold;
    margin-top: 1;
    margin-bottom: 0;
    border-bottom: solid {sel};
}}

.help-cmd-row {{
    layout: horizontal;
    height: 1;
    margin-bottom: 0;
}}

.help-cmd-key {{
    width: 22;
    color: {accent};
    text-style: bold;
}}

.help-cmd-desc {{
    color: {fg};
}}

#help-close-btn {{
    background: {accent};
    color: {bg_light};
    text-style: bold;
    margin-top: 1;
    width: 100%;
    height: 3;
}}
"""


def build_all_css() -> dict[str, str]:
    """Return a mapping of screen CSS keys to their CSS strings using current palette."""
    palette = load_palette()
    return {
        "main":      build_main_css(palette),
        "confirm":   build_confirm_css(palette),
        "log_dose":  build_log_dose_css(palette),
        "edit_dose": build_edit_dose_css(palette),
        "titration": build_titration_css(palette),
        "split":     build_split_vial_css(palette),
        "help":      build_help_css(palette),
    }
