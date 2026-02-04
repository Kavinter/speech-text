
if ! command -v python3 &> /dev/null
then
    echo "Python3 nije instaliran. Instaliraj Python3 i pokreni skriptu ponovo."
    exit 1
fi

python3 -m venv venv

source venv/bin/activate

pip install --upgrade pip

pip install -r requirements.txt

echo "Setup završen! Aktiviraj venv sa 'source venv/bin/activate' i pokreni skriptu."
