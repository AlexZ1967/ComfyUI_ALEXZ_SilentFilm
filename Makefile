CONDA_ENV ?= p313-torch214-cu132
CONDA_RUN = conda run -n $(CONDA_ENV)

.PHONY: python-test js-check js-test ts-check frontend-build test

python-test:
	$(CONDA_RUN) pytest -q tests

js-test:
	$(CONDA_RUN) node tests/test_silent_film_preview.mjs
	$(CONDA_RUN) node tests/test_silent_film_emulsion.mjs
	$(CONDA_RUN) node tests/test_silent_film_cadence_visibility.mjs
	$(CONDA_RUN) node tests/test_video_io.mjs
	$(CONDA_RUN) node tests/test_video_frame_select.mjs

js-check:
	$(CONDA_RUN) node scripts/check_js_syntax.mjs web

ts-check:
	$(CONDA_RUN) npm run ts-check

frontend-build:
	$(CONDA_RUN) npm run frontend-build

test: python-test js-check js-test ts-check
