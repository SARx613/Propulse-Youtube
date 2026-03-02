import os
from pathlib import Path

from yt_dlp import YoutubeDL


def _shorts_match_filter(info_dict, *, incomplete: bool = False):
    """
    Filtre personnalisé pour ne garder que les vidéos de 60s ou moins.

    yt-dlp, dans cette version, attend une *fonction* pour `match_filter`
    (et non une simple chaîne). On renvoie :
    - None  -> garder la vidéo
    - str   -> raison de rejet (la vidéo sera ignorée)
    """
    # Quand les infos sont incomplètes, on ne filtre pas encore.
    duration = info_dict.get("duration")
    if duration is None:
        return None

    if duration <= 300:
        return None

    return "duration > 60s (pas un Short)"


def download_new_shorts(channel_url: str) -> None:
    """
    MVP : télécharge tous les nouveaux Shorts d'une chaîne.

    - Utilise yt-dlp avec un fichier d'archive pour éviter les doublons
    - Filtre sur la durée (<= 60s) pour cibler les Shorts
    - Sauvegarde les vidéos dans le dossier 'downloads/'
    """

    base_dir = Path(__file__).resolve().parent
    downloads_dir = base_dir / "downloads"
    archive_file = base_dir / "archive.txt"

    os.makedirs(downloads_dir, exist_ok=True)

    ydl_opts = {
        # Modèle du chemin de sortie
        "outtmpl": str(
            downloads_dir / "%(uploader)s/%(upload_date)s_%(id)s_%(title)s.%(ext)s"
        ),
        # Évite de re-télécharger une vidéo déjà vue
        "download_archive": str(archive_file),
        # Noms de fichiers plus simples
        "restrictfilenames": True,
        # Format : vidéo mp4 de bonne qualité
        "format": "mp4",
        # Filtre Short : on fournit une fonction (API Python)
        "match_filter": _shorts_match_filter,
        # Un peu de logs dans la console
        "verbose": True,
    }

    print(f"Téléchargement des nouveaux Shorts depuis : {channel_url}")

    with YoutubeDL(ydl_opts) as ydl:
        # yt-dlp sait gérer directement l'URL de la chaîne
        ydl.download([channel_url])

    print("Terminé.")


if __name__ == "__main__":
    # Exemple : téléchargement sur une seule chaîne.
    # Dans l'usage normal, c'est le watcher qui appelle cette fonction
    # pour chaque chaîne listée dans channels.txt.
    download_new_shorts("https://www.youtube.com/@ShiYunshan")

