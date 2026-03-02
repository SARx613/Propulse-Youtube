import time
from datetime import datetime
from pathlib import Path

from shorts_downloader import download_new_shorts


INTERVAL_SECONDS = 60
CHANNELS_FILE = Path(__file__).resolve().parent / "channels.txt"


def load_channels() -> list[str]:
    """
    Lit la liste des chaînes dans channels.txt.

    Format attendu :
    - une chaîne par ligne
    - peut être soit un handle (@NomDeChaine) soit une URL complète
    - lignes vides ou commençant par # sont ignorées
    """
    channels: list[str] = []

    if not CHANNELS_FILE.exists():
        print(f"Aucun fichier {CHANNELS_FILE.name} trouvé, création avec un exemple.")
        CHANNELS_FILE.write_text("@ShiYunshan\n", encoding="utf-8")

    for raw_line in CHANNELS_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("@"):
            channels.append(f"https://www.youtube.com/{line}")
        else:
            channels.append(line)

    return channels


def download_all_channels_once() -> None:
    """
    Télécharge une fois les nouveaux Shorts pour toutes les chaînes
    listées dans channels.txt (sans boucle infinie).
    Pensé pour être utilisé dans un job GitHub Actions.
    """
    print(f"Téléchargement one-shot depuis les chaînes de {CHANNELS_FILE.name}.")
    channels = load_channels()
    if not channels:
        print("Aucune chaîne définie dans channels.txt.")
        return

    for channel_url in channels:
        print(f"- Téléchargement pour la chaîne : {channel_url}")
        try:
            download_new_shorts(channel_url)
        except Exception as exc:
            print(f"Erreur pendant le téléchargement pour {channel_url} : {exc}")


def watch_channels_forever() -> None:
    """
    Boucle simple qui vérifie régulièrement toutes les chaînes de channels.txt
    et déclenche le téléchargement des nouveaux Shorts pour chacune.

    Grâce au fichier d'archive de yt-dlp, seules les nouvelles vidéos
    sont téléchargées à chaque passage.
    """
    print(f"Watcher démarré. Lecture des chaînes depuis {CHANNELS_FILE.name}.")

    while True:
        now = datetime.now().isoformat(timespec="seconds")
        print(f"[{now}] Nouvelle passe de vérification.")

        channels = load_channels()
        if not channels:
            print("Aucune chaîne définie dans channels.txt.")
        else:
            for channel_url in channels:
                print(f"- Vérification de la chaîne : {channel_url}")
                try:
                    download_new_shorts(channel_url)
                except Exception as exc:
                    print(f"Erreur pendant le téléchargement pour {channel_url} : {exc}")

        print(f"Pause de {INTERVAL_SECONDS} secondes avant la prochaine vérification.")
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    watch_channels_forever()

