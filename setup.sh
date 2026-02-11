
if ! command -v python3 &> /dev/null
then
    echo "Python3 is not installed. Install Python3 and run the script again."
    exit 1
fi

python3 -m venv .venv

source .venv/bin/activate

pip install --upgrade pip

pip install -r requirements.txt
