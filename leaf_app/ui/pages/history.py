import customtkinter as ctk
import tkinter.filedialog as filedialog
import pandas as pd
from ui.theme import Fonts, Colors, Layout
from ui.state import app_state

class HistoryPage(ctk.CTkFrame):
    PAGE_ID = "history"
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        
        # Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(0, 20), padx=20)
        
        ctk.CTkLabel(self.header_frame, text="Histórico de análises", font=Fonts.header2(), text_color=Colors.INK).pack(anchor="w")
        
        # Tabela Container
        self.table_container = ctk.CTkScrollableFrame(self, fg_color=Colors.SURFACE, corner_radius=Layout.CORNER_RADIUS, border_width=1, border_color=Colors.LINE)
        self.table_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Botões
        self.buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.buttons_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.btn_clear = ctk.CTkButton(self.buttons_frame, text="🗑️ Limpar Histórico", fg_color="transparent", text_color=Colors.INK_SECONDARY, border_width=1, border_color=Colors.LINE, hover_color=Colors.PAGE_BG, command=self._clear_history)
        self.btn_clear.pack(side="left", padx=(0, 10))
        
        self.btn_export = ctk.CTkButton(self.buttons_frame, text="📥 Exportar Histórico (CSV)", fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_DARK, command=self._export_csv)
        self.btn_export.pack(side="left")
        
        self.refresh()
        
    def refresh(self):
        # Limpar tabela
        for widget in self.table_container.winfo_children():
            widget.destroy()
            
        history = app_state.get("analysis_history", [])
        
        if not history:
            ctk.CTkLabel(self.table_container, text="Nenhuma análise foi registrada nesta sessão.", text_color=Colors.MUTED).pack(pady=40)
            return
            
        # Título Colunas
        headers = ["Imagem", "Herbivoria", "Severidade", "Método"]
        header_frame = ctk.CTkFrame(self.table_container, fg_color=Colors.PAGE_BG, corner_radius=6)
        header_frame.pack(fill="x", pady=(0, 10))
        
        for idx, text in enumerate(headers):
            header_frame.grid_columnconfigure(idx, weight=1)
            ctk.CTkLabel(header_frame, text=text, font=Fonts.body_bold(), text_color=Colors.INK).grid(row=0, column=idx, sticky="w", padx=10, pady=5)
            
        # Linhas
        for row_idx, entry in enumerate(history):
            row_frame = ctk.CTkFrame(self.table_container, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)
            
            for col_idx, key in enumerate(headers):
                row_frame.grid_columnconfigure(col_idx, weight=1)
                ctk.CTkLabel(row_frame, text=str(entry.get(key, "")), font=Fonts.small(), text_color=Colors.INK_SECONDARY).grid(row=0, column=col_idx, sticky="w", padx=10, pady=5)

    def _clear_history(self):
        app_state["analysis_history"] = []
        self.refresh()
        
    def _export_csv(self):
        history = app_state.get("analysis_history", [])
        if not history: return
        
        filepath = filedialog.asksaveasfilename(
            title="Salvar Histórico",
            defaultextension=".csv",
            filetypes=[("Arquivos CSV", "*.csv")],
            initialfile="leaf_historico.csv"
        )
        if filepath:
            df = pd.DataFrame(history)
            df.to_csv(filepath, index=False, encoding="utf-8-sig")
