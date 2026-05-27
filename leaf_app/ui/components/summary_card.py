import customtkinter as ctk
import tkinter as tk
from ui.theme import Colors, Fonts, Layout

class SummaryCard(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=Colors.SURFACE, corner_radius=Layout.CORNER_RADIUS, border_width=1, border_color=Colors.LINE, **kwargs)
        
        self.pack_propagate(False)
        self.title = ctk.CTkLabel(self, text="Resumo da análise", font=Fonts.body_bold(), text_color=Colors.INK)
        self.title.pack(anchor="w", padx=20, pady=(15, 10))
        
        # Area grid
        self.grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.grid_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Box 1: Area Afetada
        self.box1 = ctk.CTkFrame(self.grid_frame, fg_color=Colors.PAGE_BG, corner_radius=10, border_width=1, border_color=Colors.LINE)
        self.box1.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        ctk.CTkLabel(self.box1, text="⌁ Área afetada", font=Fonts.small(), text_color=Colors.INK_SECONDARY).pack(anchor="w", padx=15, pady=(10, 5))
        self.affected_val = ctk.CTkLabel(self.box1, text="0%", font=Fonts.header2(), text_color=Colors.PRIMARY)
        self.affected_val.pack(anchor="w", padx=15)
        ctk.CTkLabel(self.box1, text="da área foliar total", font=Fonts.small(), text_color=Colors.MUTED).pack(anchor="w", padx=15)
        
        # Box 2: Severidade
        self.box2 = ctk.CTkFrame(self.grid_frame, fg_color=Colors.PAGE_BG, corner_radius=10, border_width=1, border_color=Colors.LINE)
        self.box2.grid(row=0, column=1, sticky="nsew", padx=5)
        
        ctk.CTkLabel(self.box2, text="♢ Severidade", font=Fonts.small(), text_color=Colors.INK_SECONDARY).pack(anchor="w", padx=15, pady=(10, 5))
        self.severity_val = ctk.CTkLabel(self.box2, text="N/A", font=Fonts.header2(), text_color=Colors.PRIMARY)
        self.severity_val.pack(anchor="w", padx=15)
        
        # Barra fake de severidade usando TK Canvas (mais leve para graficos custom)
        self.sev_canvas = tk.Canvas(self.box2, height=10, bg="#E5E7EB", highlightthickness=0)
        self.sev_canvas.pack(fill="x", padx=15, pady=10)
        # O canvas precisa de bind de resize para desenhar
        self.sev_canvas.bind("<Configure>", self._draw_severity_bar)
        self.sev_total = 0.0
        
        # Box 3: Confiança
        self.box3 = ctk.CTkFrame(self.grid_frame, fg_color=Colors.PAGE_BG, corner_radius=10, border_width=1, border_color=Colors.LINE)
        self.box3.grid(row=0, column=2, sticky="nsew", padx=(5, 0))
        
        ctk.CTkLabel(self.box3, text="✺ Confiança", font=Fonts.small(), text_color=Colors.INK_SECONDARY).pack(anchor="w", padx=15, pady=(10, 5))
        self.conf_val = ctk.CTkLabel(self.box3, text="0%", font=Fonts.header2(), text_color=Colors.INK)
        self.conf_val.pack(anchor="w", padx=15)
        self.conf_bar = ctk.CTkProgressBar(self.box3, progress_color=Colors.PRIMARY, height=10)
        self.conf_bar.pack(fill="x", padx=15, pady=10)
        self.conf_bar.set(0)

    def _draw_severity_bar(self, event=None):
        self.sev_canvas.delete("all")
        w = self.sev_canvas.winfo_width()
        h = self.sev_canvas.winfo_height()
        if w <= 1: return
        
        part = w / 4
        self.sev_canvas.create_rectangle(0, 0, part, h, fill=Colors.SEVERITY_GREEN, outline="")
        self.sev_canvas.create_rectangle(part, 0, part*2, h, fill=Colors.SEVERITY_YELLOW, outline="")
        self.sev_canvas.create_rectangle(part*2, 0, part*3, h, fill=Colors.SEVERITY_ORANGE, outline="")
        self.sev_canvas.create_rectangle(part*3, 0, w, h, fill="#DDE3E6", outline="")
        
        # Marcador
        x = (self.sev_total / 100.0) * w
        x = max(5, min(x, w-5))
        self.sev_canvas.create_polygon(x-5, 0, x+5, 0, x, 10, fill="#000")

    def update_data(self, total: float, sev_label: str, sev_color: str, confidence: float):
        self.sev_total = total
        self.affected_val.configure(text=f"{total:.0f}%")
        self.severity_val.configure(text=sev_label, text_color=sev_color)
        
        self._draw_severity_bar()
            
        self.conf_val.configure(text=f"{confidence:.0f}%")
        self.conf_bar.set(confidence / 100.0)
