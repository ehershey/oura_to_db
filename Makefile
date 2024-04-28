run: ./oura_to_db.py ./venv
	./venv/bin/python3 ./oura_to_db.py

./venv: requirements.txt
	python -mvenv ./venv

.PHONY: run
