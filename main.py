import warnings
warnings.filterwarnings("ignore")

import flet as ft
import auth

from styles import (
    PRIMARY_BG,
    SECONDARY_BG,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    ACCENT_BLUE,
    ACCENT_CYAN,
    ACCENT_PURPLE,
    BORDER_RADIUS,
)

from calendario import avvia_calendario


# ═══════════════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════════════

def mostra_login(page: ft.Page, is_student: bool, on_success):

    titolo = "Studente" if is_student else "Docente"
    colore = ACCENT_BLUE if is_student else ACCENT_PURPLE

    errore = ft.Text(
        "",
        color="red",
        size=12,
    )

    # LOGIN FUNCTION

    def login(e):

        username = user_input.value.strip()
        password = pass_input.value.strip()

        if username == "" or password == "":

            errore.value = "Inserisci username e password"
            page.update()
            return

        try:

            ok = auth.login_user(
                username,
                password,
                "studente" if is_student else "docente"
            )

            if ok:

                dialog.open = False
                page.update()

                on_success(is_student)

            else:

                errore.value = "Credenziali errate"
                page.update()

        except Exception as ex:

            errore.value = f"Errore: {str(ex)}"
            page.update()

    # INPUT USERNAME

    user_input = ft.TextField(

        label="Username",

        width=320,

        color=TEXT_PRIMARY,

        border_color=colore,

        focused_border_color=colore,

        prefix_icon=ft.icons.PERSON_OUTLINE,
    )

    # INPUT PASSWORD

    pass_input = ft.TextField(

        label="Password",

        width=320,

        password=True,

        can_reveal_password=True,

        color=TEXT_PRIMARY,

        border_color=colore,

        focused_border_color=colore,

        prefix_icon=ft.icons.LOCK_OUTLINE,

        on_submit=login,
    )

    # DIALOG LOGIN

    dialog = ft.AlertDialog(

        modal=True,

        bgcolor=SECONDARY_BG,

        shape=ft.RoundedRectangleBorder(
            radius=BORDER_RADIUS
        ),

        content=ft.Container(

            width=380,

            padding=25,

            content=ft.Column(

                controls=[

                    ft.Text(
                        f"Accesso {titolo}",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_PRIMARY,
                    ),

                    ft.Text(
                        "Inserisci le credenziali",
                        size=13,
                        color=TEXT_SECONDARY,
                    ),

                    ft.Container(height=10),

                    user_input,

                    pass_input,

                    errore,

                    ft.Container(height=5),

                    ft.ElevatedButton(

                        text="ENTRA",

                        width=320,

                        height=50,

                        bgcolor=colore,

                        color="white",

                        on_click=login,
                    ),
                ],

                spacing=15,

                tight=True,

                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
    )

    page.dialog = dialog

    dialog.open = True

    page.update()


# ═══════════════════════════════════════════════════════════════
# CARD
# ═══════════════════════════════════════════════════════════════

def crea_card(
    page,
    icona,
    titolo,
    sottotitolo,
    descrizione,
    colore_bg,
    colore_border,
    colore_hover,
    on_click
):

    card = ft.Container(

        width=330,

        height=270,

        bgcolor=colore_bg,

        border_radius=BORDER_RADIUS,

        border=ft.border.all(
            2,
            colore_border
        ),

        padding=30,

        ink=True,

        on_click=on_click,

        content=ft.Column(

            controls=[

                ft.Text(
                    icona,
                    size=55,
                ),

                ft.Text(
                    titolo,
                    size=22,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),

                ft.Text(
                    sottotitolo,
                    size=12,
                    italic=True,
                    color=ACCENT_CYAN,
                ),

                ft.Container(height=10),

                ft.Text(
                    descrizione,
                    size=13,
                    color=TEXT_SECONDARY,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],

            spacing=8,

            alignment=ft.MainAxisAlignment.CENTER,

            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    )

    # HOVER EFFECT

    def hover(e):

        if e.data == "true":

            card.bgcolor = colore_hover

        else:

            card.bgcolor = colore_bg

        page.update()

    card.on_hover = hover

    return card


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main(page: ft.Page):

    # PAGE SETTINGS

    page.title = "🏫 Piattaforma Scolastica AI"

    page.theme_mode = ft.ThemeMode.DARK

    page.bgcolor = PRIMARY_BG

    page.window_width = 1400

    page.window_height = 900

    page.padding = 0

    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    # HOME

    def mostra_home():

        page.clean()

        # LOGIN SUCCESS

        def login_success(is_student: bool):

            avvia_calendario(
                page,
                is_student=is_student,
                on_back=mostra_home,
            )

        # CARD STUDENTE

        card_studente = crea_card(

            page,

            "👨‍🎓",

            "Studente",

            "Vista Studente",

            "Orario • Registro • Verifiche • AI Chat",

            "#0b1d2a",

            ACCENT_BLUE,

            "#12324a",

            lambda e: mostra_login(
                page,
                True,
                login_success
            )
        )

        # CARD DOCENTE

        card_docente = crea_card(

            page,

            "👨‍🏫",

            "Docente",

            "Vista Docente",

            "Registro • Assenze • Verifiche • Gestione",

            "#1b1029",

            ACCENT_PURPLE,

            "#2a1740",

            lambda e: mostra_login(
                page,
                False,
                login_success
            )
        )

        # HEADER

        header = ft.Column(

            controls=[

                ft.Text(
                    "🏫",
                    size=70,
                ),

                ft.Text(
                    "Piattaforma Scolastica AI",
                    size=38,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),

                ft.Text(
                    "Sistema intelligente per studenti e docenti",
                    size=15,
                    color=TEXT_SECONDARY,
                ),
            ],

            spacing=5,

            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # MAIN LAYOUT

        layout = ft.Container(

            expand=True,

            alignment=ft.Alignment(0, 0),

            content=ft.Column(

                controls=[

                    header,

                    ft.Container(height=40),

                    ft.Row(

                        controls=[
                            card_studente,
                            card_docente,
                        ],

                        alignment=ft.MainAxisAlignment.CENTER,

                        spacing=40,
                    )
                ],

                alignment=ft.MainAxisAlignment.CENTER,

                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

        page.add(layout)

        page.update()

    # START APP

    mostra_home()


# ═══════════════════════════════════════════════════════════════
# AVVIO
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":

    ft.app(target=main)