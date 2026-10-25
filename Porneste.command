#!/bin/zsh
# Porneste aplicatia; Terminalul ramane deschis doar daca apare o eroare
cd -- "${0:A:h}" || exit 1
export LANG=en_US.UTF-8 LC_CTYPE=UTF-8
export PATH="/opt/local/bin:/usr/local/bin:$PATH"
if [[ ! -x .venv/bin/python ]]; then
  echo 'Lipseste mediul Python. Ruleaza o data: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt'
  read '?Apasa Enter pentru inchidere.'
  exit 1
fi
mkdir -p data
[[ -f data/pornire.log ]] && tail -n 3000 data/pornire.log > data/pornire.tmp && mv data/pornire.tmp data/pornire.log
print -r -- "Pornire: $(date)" >> data/pornire.log
.venv/bin/python main.py "$@" >> data/pornire.log 2>&1
result=$?
if (( result != 0 )); then
  echo 'Aplicatia s-a oprit cu eroare. Ultimele randuri din data/pornire.log:'
  tail -n 20 data/pornire.log
  read '?Apasa Enter pentru inchidere.'
fi
osascript -e 'tell application "Terminal" to close (every window whose name contains "Porneste.command")' >/dev/null 2>&1 &
exit "$result"
