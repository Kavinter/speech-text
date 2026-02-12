if ! command -v python3 &> /dev/null
then
    echo "Python3 is not installed. Install Python3 and run the script again."
    exit 1
fi

if ! command -v ffmpeg &> /dev/null
then
    echo "ffmpeg not found. Installing ffmpeg..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt update
        sudo apt install -y ffmpeg
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install ffmpeg
    else
        echo "Automatic ffmpeg installation not supported for this OS. Please install it manually."
        exit 1
    fi
fi

python3 -m venv .venv

source .venv/bin/activate

pip install --upgrade pip

pip install -r requirements.txt

echo "Setup completed successfully!"
