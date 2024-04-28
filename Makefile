run: ./oura_to_db.py ./venv test.env
	env `cat test.env` ./venv/bin/python3 ./oura_to_db.py

serve: ./oura_to_db.py serve.py
	env `cat test.env` PATH=$PATH:./venv/bin ./start.sh

./venv:
	python3 -mvenv ./venv

pip: requirements.txt ./venv
	./venv/bin/pip install -r requirements.txt

test.env:
	echo missing required test.env

.PHONY: run pip
