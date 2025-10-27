run: ./oura_to_db.py ./venv test.env
	env `cat test.env` ./venv/bin/python3 ./oura_to_db.py

serve: ./oura_to_db.py ./serve.py
	env `cat test.env` PYTHONPATH= PATH=$(PATH):./venv/bin ./start.sh

deploy:
	git push github 
	open https://dashboard.render.com/web/srv-comiockf7o1s73f581v0

./venv:
	python3 -mvenv ./venv

pip: requirements.txt ./venv
	./venv/bin/pip install -r requirements.txt

test.env:
	echo missing required test.env

.PHONY: run pip deploy
