import customtkinter as ctk
from ui.theme import Colors, Fonts
from ui.sidebar import Sidebar
from ui.pages.dashboard import DashboardPage
from ui.pages.history import HistoryPage
from ui.pages.reports import ReportsPage
from ui.pages.settings import SettingsPage
from ui.pages.dataset_browser import DatasetBrowserPage
from ui.state import app_state, save_history

class LeafAppWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("L.E.A.F - Levantamento e Estimativa de Anomalias Foliares")
        self.geometry("1200x800")
        
        # Col 0 é a sidebar, Col 1 é o conteúdo
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        self.configure(fg_color=Colors.PAGE_BG)
        
        # Salvar histórico ao fechar a janela
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Sidebar
        self.sidebar = Sidebar(self, self.navigate, self.toggle_theme)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # Container principal
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)
        
        # Dict de páginas
        self.pages = {}
        
        # Inicializa as páginas (e esconde todas, menos a inicial)
        self.current_page = "dashboard"
        for PageClass in (DashboardPage, DatasetBrowserPage, HistoryPage, ReportsPage, SettingsPage):
            page_id = PageClass.PAGE_ID
            page_frame = PageClass(self.main_container)
            self.pages[page_id] = page_frame
            if page_id == self.current_page:
                page_frame.grid(row=0, column=0, sticky="nsew")
            else:
                page_frame.grid_remove()
        
    def navigate(self, page_id: str):
        if page_id in self.pages:
            # Esconde a pagina atual
            if self.current_page in self.pages:
                self.pages[self.current_page].grid_remove()
                
            self.current_page = page_id
            page = self.pages[page_id]
            
            if hasattr(page, "refresh"):
                page.refresh()
                
            page.grid(row=0, column=0, sticky="nsew")

    def _on_close(self):
        """Salva o histórico e encerra a aplicação."""
        save_history()
        self.destroy()
            
    def toggle_theme(self, is_dark: bool):
        ctk.set_appearance_mode("dark" if is_dark else "light")

    def navigate_and_analyze(self, page_id: str):
        """Navega ao Dashboard e dispara análise com imagens do dataset."""
        self.sidebar.current_page = page_id
        self.sidebar._update_button_styles()
        self.navigate(page_id)

        # Se houver imagens selecionadas do dataset, passá-las ao Dashboard
        dataset_files = app_state.get("dataset_selected_files", [])
        if dataset_files and page_id == "dashboard":
            dashboard = self.pages.get("dashboard")
            if dashboard:
                dashboard.selected_files = dataset_files
                dashboard.status_label.configure(text=f"{len(dataset_files)} imagem(ns) do dataset")
                dashboard._log(f"{len(dataset_files)} imagens carregadas do Banco de Imagens.")
                dashboard._on_analyze()
                app_state["dataset_selected_files"] = []  # limpar após uso
