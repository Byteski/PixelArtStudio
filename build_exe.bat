@echo off
call .venv\Scripts\activate
pip install -r requirements-dev.txt
pyinstaller --noconfirm --clean --windowed --name PixelArtStudio main.py
echo.
echo Build finished. Open dist\PixelArtStudio\PixelArtStudio.exe
pause
