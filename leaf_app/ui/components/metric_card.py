import customtkinter as ctk
from ui.theme import Colors, Fonts, Layout

class MetricCard(ctk.CTkFrame):
    def __init__(self, master, title, icon, color, soft_color, **kwargs):
        super().__init__(master, fg_color=Colors.SURFACE, corner_radius=Layout.CORNER_RADIUS, border_width=1, border_color=Colors.LINE, **kwargs)
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.color = color
        self.soft_color = soft_color
        
        # Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        # Não temos suporte a SVG no CTk nativo sem libs pesadas, vamos usar icones emoji/unicode grandes
        self.icon_label = ctk.CTkLabel(
            self.header_frame, 
            text=icon, 
            font=(Fonts.FAMILY, 24), 
            fg_color=soft_color, 
            text_color=color, 
            width=46, height=46, corner_radius=23
        )
        self.icon_label.pack(side="left")
        
        self.title_label = ctk.CTkLabel(self.header_frame, text=title, font=Fonts.body_bold(), text_color=Colors.INK_SECONDARY)
        self.title_label.pack(side="left", padx=15)
        
        # Value
        self.value_label = ctk.CTkLabel(self, text="0%", font=Fonts.header1(), text_color=color)
        self.value_label.pack(anchor="w", padx=20)
        
        self.desc_label = ctk.CTkLabel(self, text="Área afetada", font=Fonts.small(), text_color=Colors.INK_SECONDARY)
        self.desc_label.pack(anchor="w", padx=20)
        
        # Pill
        self.pill_frame = ctk.CTkFrame(self, fg_color=Colors.PAGE_BG, corner_radius=6, border_width=1, border_color=Colors.LINE)
        self.pill_frame.pack(anchor="w", padx=20, pady=(15, 20))
        self.pill_label = ctk.CTkLabel(self.pill_frame, text="  N/A  ", font=Fonts.small(), text_color=Colors.INK_SECONDARY)
        self.pill_label.pack(padx=8, pady=2)

    def update_data(self, pct: float, label: str):
        self.value_label.configure(text=f"{pct:.0f}%")
        self.pill_label.configure(text=f"  {label}  ")
