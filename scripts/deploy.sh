set -x
cd /home/pi
git clone https://github.com/sashgorokhov/stratux-companion.git
cd stratux-companion

sudo apt-get install -y python3-venv python3-dev gcc
python -m venv env
source env/bin/activate
pip install poetry
poetry install

sudo cp -f systemd/stratux_companion.service /lib/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable stratux_companion.service
sudo systemctl restart stratux_companion
