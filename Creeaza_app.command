#!/bin/zsh
# Creeaza "Separare Clipuri.app" langa acest script: dublu click, iconita in Dock, fara Terminal.
# Aplicatia foloseste codul din acest folder, deci modificarile din main.py se vad imediat.
cd -- "${0:A:h}" || exit 1
dir="$PWD"
app="$dir/Separare Clipuri.app"
rm -rf "$app"
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources"
cat > "$app/Contents/MacOS/SeparareClipuri" <<SCRIPT
#!/bin/zsh
export LANG=en_US.UTF-8 LC_CTYPE=UTF-8
export PATH="/opt/local/bin:/usr/local/bin:\$PATH"
cd "$dir"
mkdir -p data
exec "$dir/.venv/bin/python" "$dir/main.py" "\$@" >> "$dir/data/pornire.log" 2>&1
SCRIPT
chmod +x "$app/Contents/MacOS/SeparareClipuri"
cat > "$app/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>Separare Clipuri</string>
<key>CFBundleDisplayName</key><string>Separare Clipuri</string>
<key>CFBundleIdentifier</key><string>ro.urdea.separareclipuri</string>
<key>CFBundleExecutable</key><string>SeparareClipuri</string>
<key>CFBundleIconFile</key><string>icon</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>1.0</string>
<key>NSHighResolutionCapable</key><true/>
</dict></plist>
PLIST
# iconita desenata de aplicatie, convertita in .icns
tmp=$(mktemp -d)
QT_QPA_PLATFORM=offscreen .venv/bin/python main.py --icon "$tmp/icon.png" 2>/dev/null
mkdir "$tmp/icon.iconset"
for s in 16 32 128 256 512; do
  sips -z $s $s "$tmp/icon.png" --out "$tmp/icon.iconset/icon_${s}x${s}.png" >/dev/null
  sips -z $((s*2)) $((s*2)) "$tmp/icon.png" --out "$tmp/icon.iconset/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$tmp/icon.iconset" -o "$app/Contents/Resources/icon.icns"
rm -rf "$tmp"
touch "$app"
echo "Gata: $app"
echo "Il poti trage in Dock sau in Applications (ca alias)."
