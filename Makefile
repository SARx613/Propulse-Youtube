PYTHON ?= python

.PHONY: help download upload run watch

help:
	@echo "Cibles disponibles :"
	@echo "  make download      - Télécharge les nouveaux Shorts (local)"
	@echo "  make upload        - Uploade jusqu'à 50 vidéos (local, max 100/jour)"
	@echo "  make run           - Télécharge puis uploade (batch local complet)"
	@echo "  make watch         - Lance le watcher infini (déconseillé en CI)"

download:
	$(PYTHON) shorts_downloader.py

upload:
	MAX_UPLOADS_PER_RUN=50 MAX_UPLOADS_PER_DAY=100 $(PYTHON) upload_to_youtube.py

run: download upload

watch:
	$(PYTHON) shorts_watcher.py
