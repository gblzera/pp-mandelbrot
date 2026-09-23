#!/usr/bin/env bash
# Markdown -> PDF sem LaTeX: pandoc monta o HTML, Chrome headless imprime.
#   Uso: ./scripts/pdf.sh docs/marco1.md
set -euo pipefail
cd "$(dirname "$0")/.."
MD=${1:?uso: ./scripts/pdf.sh docs/arquivo.md}
BASE=${MD%.md}
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
pandoc "$MD" -f gfm -t html5 --standalone --embed-resources \
       --css docs/estilo.css --metadata title="" -o "$BASE.html"
"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
          --print-to-pdf="$BASE.pdf" "file://$PWD/$BASE.html" 2>/dev/null
rm -f "$BASE.html"
echo "gerado: $BASE.pdf  ($(pdfinfo "$BASE.pdf" 2>/dev/null | awk '/^Pages/{print $2}') páginas)"
