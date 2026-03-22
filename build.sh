#/bin/bash
wine python -m PyInstaller --noconsole --onefile --name rich3_patch --icon=icon.png --add-data "EVENTVOC;EVENTVOC" --add-data "NEWSVOC;NEWSVOC" --add-data "SCREEN;SCREEN" run_all.py