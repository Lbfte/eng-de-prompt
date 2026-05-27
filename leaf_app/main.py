import sys
import os

# Adiciona o diretório atual ao sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk
from main_window import LeafAppWindow

def main():
    # Inicializar CustomTkinter
    ctk.set_appearance_mode("dark")  # ou "light"
    ctk.set_default_color_theme("green")
    
    app = LeafAppWindow()
    app.mainloop()

if __name__ == "__main__":
    main()
