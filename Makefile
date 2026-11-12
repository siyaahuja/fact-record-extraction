PY ?= python3
INPUT ?= sample_data
OUT ?= out

.PHONY: install run eval all determinism test clean

install:
	$(PY) -m pip install -r requirements.txt

run:
	$(PY) -m extraction run $(INPUT) --out $(OUT)

eval:
	$(PY) -m extraction run $(INPUT) --out $(OUT)
	$(PY) -m extraction eval $(INPUT) --out $(OUT)

determinism:
	$(PY) -m extraction determinism $(INPUT) --runs 3

test:
	$(PY) -m unittest discover -s tests -t .

clean:
	rm -rf .cache $(OUT) .determinism
