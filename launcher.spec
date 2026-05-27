# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

# Arquivos de dados locais a serem incluídos
added_files = [
    ('leaf_app/metrics.py', '.'),
    ('leaf_app/image_processor.py', '.'),
    ('leaf_app/background_removal.py', '.'),
    ('leaf_app/dataset_manager.py', '.'),
    ('leaf_app/icon.ico', '.'),
    ('leaf_app/logo.png', '.'),
    ('leaf_app/ui/theme.py', 'ui'),
    ('leaf_app/ui/state.py', 'ui'),
    ('leaf_app/ui/sidebar.py', 'ui'),
    ('leaf_app/ui/pages/dashboard.py', 'ui/pages'),
    ('leaf_app/ui/pages/history.py', 'ui/pages'),
    ('leaf_app/ui/pages/reports.py', 'ui/pages'),
    ('leaf_app/ui/pages/settings.py', 'ui/pages'),
    ('leaf_app/ui/pages/dataset_browser.py', 'ui/pages'),
    ('leaf_app/ui/components/preview_card.py', 'ui/components'),
    ('leaf_app/ui/components/metric_card.py', 'ui/components'),
    ('leaf_app/ui/components/summary_card.py', 'ui/components'),
]

hidden_imports = [
    'customtkinter',
    'cv2',
    'numpy',
    'pandas',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'kagglehub',
]

a = Analysis(
    ['leaf_app/main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['streamlit'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LEAF',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='leaf_app/icon.ico',
)
