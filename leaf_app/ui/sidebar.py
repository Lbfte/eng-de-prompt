import customtkinter as ctk
import os
from typing import Callable
from PIL import Image
from ui.theme import Colors, Fonts

class Sidebar(ctk.CTkFrame):
    def __init__(self, master, navigate_callback: Callable[[str], None], toggle_theme_callback: Callable[[bool], None]):
        super().__init__(master, width=280, corner_radius=0, fg_color=Colors.SURFACE)
        
        self.navigate_callback = navigate_callback
        self.toggle_theme_callback = toggle_theme_callback
        self.current_page = "dashboard"
        
        # Ocultar o comportamento padrão de shrink do frame
        self.grid_propagate(False)
        
        # Logo / Brand
        self.brand_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.brand_frame.grid(row=0, column=0, padx=20, pady=(30, 20), sticky="ew")
        
        # Carregar logo.png real (1:1 recortada)
        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logo.png")
        if os.path.exists(logo_path):
            pil_logo = Image.open(logo_path)
            self._logo_img = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(50, 50))
            self.logo_label = ctk.CTkLabel(self.brand_frame, image=self._logo_img, text="")
        else:
            self.logo_label = ctk.CTkLabel(self.brand_frame, text="🌿", font=(Fonts.FAMILY, 40))
        self.logo_label.pack(side="left", padx=(0, 10))
        
        self.title_frame = ctk.CTkFrame(self.brand_frame, fg_color="transparent")
        self.title_frame.pack(side="left", fill="both", expand=True)
        
        self.brand_title = ctk.CTkLabel(
            self.title_frame, 
            text="LEAF", 
            font=Fonts.header2(), 
            text_color=Colors.PRIMARY
        )
        self.brand_title.pack(anchor="w")
        
        self.brand_subtitle = ctk.CTkLabel(
            self.title_frame, 
            text="Análise Foliar", 
            font=Fonts.small(), 
            text_color=Colors.MUTED
        )
        self.brand_subtitle.pack(anchor="w")
        
        # Linha separadora
        self.separator = ctk.CTkFrame(self, height=1, fg_color=Colors.LINE)
        self.separator.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        # Menu
        self.menu_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.menu_frame.grid(row=2, column=0, sticky="nsew", padx=15)
        self.grid_rowconfigure(2, weight=1)  # Menu frame takes the empty space
        
        self.buttons = {}
        
        menu_items = [
            ("dashboard", "Início", "🏠"),
            ("dataset", "Banco de Imagens", "🗂️"),
            ("history", "Histórico", "🕒"),
            ("reports", "Relatórios", "📊"),
            ("settings", "Configurações", "⚙️")
        ]
        
        for idx, (page_id, label, icon) in enumerate(menu_items):
            btn = ctk.CTkButton(
                self.menu_frame,
                text=f"  {icon}  {label}",
                font=Fonts.body_bold(),
                fg_color="transparent",
                text_color=Colors.INK_SECONDARY,
                hover_color=Colors.SURFACE_HOVER,
                anchor="w",
                height=40,
                corner_radius=8,
                command=lambda p=page_id: self._on_nav_click(p)
            )
            btn.pack(fill="x", pady=2)
            self.buttons[page_id] = btn
            
        # Avatar e Theme Switch
        self.user_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.user_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=20)
        
        self.user_separator = ctk.CTkFrame(self.user_frame, height=1, fg_color=Colors.LINE)
        self.user_separator.pack(fill="x", pady=(0, 15))
        
        self.theme_switch = ctk.CTkSwitch(
            self.user_frame,
            text="Tema Escuro",
            font=Fonts.body(),
            command=self._on_theme_toggle,
            button_color=Colors.PRIMARY,
            progress_color=Colors.PRIMARY_SOFT
        )
        # O estado padrao do CTk é dark, então vamos iniciar com 1 (on)
        self.theme_switch.select()
        self.theme_switch.pack(anchor="w", pady=(0, 10))
        
        self.user_info = ctk.CTkLabel(
            self.user_frame,
            text="👤 Pesquisador",
            font=Fonts.body_bold(),
            text_color=Colors.INK
        )
        self.user_info.pack(anchor="w")
        
        self._update_button_styles()

    def _on_nav_click(self, page_id: str):
        if self.current_page == page_id:
            return
        self.current_page = page_id
        self._update_button_styles()
        self.navigate_callback(page_id)
        
    def _update_button_styles(self):
        for pid, btn in self.buttons.items():
            if pid == self.current_page:
                btn.configure(
                    fg_color=Colors.PRIMARY_SOFT,
                    text_color=Colors.PRIMARY,
                    hover_color=Colors.PRIMARY_SOFT
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=Colors.INK_SECONDARY,
                    hover_color=Colors.SURFACE_HOVER
                )
                
    def _on_theme_toggle(self):
        is_dark = self.theme_switch.get() == 1
        self.toggle_theme_callback(is_dark)
