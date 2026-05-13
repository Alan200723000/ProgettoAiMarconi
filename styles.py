# ══════════════════════════════════════════════════════════════════════
# styles.py — Palette colori, costanti UI e stili globali
# ══════════════════════════════════════════════════════════════════════

PRIMARY_BG    = "#080e1a"
SECONDARY_BG  = "#0d1528"
TERTIARY_BG   = "#111e35"
CARD_BG       = "#162035"

TEXT_PRIMARY   = "#e8f0fe"
TEXT_SECONDARY = "#94a3b8"
TEXT_MUTED     = "#4a5a75"
TEXT_SUBTLE    = "#2d3d55"

ACCENT_BLUE   = "#4f8ef7"
ACCENT_CYAN   = "#22d3ee"
ACCENT_RED    = "#fb7185"
ACCENT_GREEN  = "#34d399"
ACCENT_PURPLE = "#a78bfa"
ACCENT_YELLOW = "#fbbf24"
ACCENT_ORANGE = "#fb923c"

SUBJECTS_PALETTE = {
    "Sistemi e Reti":    {"bg": "#0f2545", "accent": "#3b82f6"},
    "Informatica":       {"bg": "#0e1f3e", "accent": "#60a5fa"},
    "Telecomunicazioni": {"bg": "#0a2d22", "accent": "#10b981"},
    "Matematica":        {"bg": "#0f2535", "accent": "#22d3ee"},
    "Lingua inglese":    {"bg": "#1e1040", "accent": "#a78bfa"},
    "Italiano":          {"bg": "#3a1018", "accent": "#fb7185"},
    "Storia":            {"bg": "#2a1505", "accent": "#f97316"},
    "Scienze":           {"bg": "#0f2a12", "accent": "#4ade80"},
    "Fisica":            {"bg": "#0a1e30", "accent": "#06b6d4"},
    "Educazione Fisica": {"bg": "#2a1e08", "accent": "#fbbf24"},
    "Religione":         {"bg": "#1a2510", "accent": "#84cc16"},
    "default":           {"bg": "#14202e", "accent": "#4a5a75"},
}

BORDER_COLOR        = "#1a2540"
BORDER_COLOR_LIGHT  = "#253550"
BORDER_RADIUS       = 18
BORDER_RADIUS_SMALL = 12

CHAT_SIDEBAR_WIDTH  = 300

# Icone
ICON_CALENDAR      = "📅"
ICON_STUDENT       = "👨‍🎓"
ICON_TEACHER       = "👨‍🏫"
ICON_AI            = "🤖"
ICON_CHECK         = "✅"
ICON_VERIFY        = "📝"
ICON_INTERROGATION = "🎤"
ICON_SAVE          = "💾"
ICON_RESET         = "🧹"
ICON_SUGGEST       = "💡"
ICON_PLUS          = "➕"
WARNING            = "⚠️"
ICON_CLASS         = "🏫"


class ChatMessageStyle:
    user_bg = "#163256"
    ai_bg   = "#1e2d45"


class GridStyle:
    cell_height   = 50
    mini_height   = 28
    row_spacing   = 4
    border_radius = 10
