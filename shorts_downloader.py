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

    # YouTube Shorts: <= 60 secondes
    if duration <= 60:
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
    cookies_file = base_dir / "youtube_cookies.txt"

    os.makedirs(downloads_dir, exist_ok=True)

    # Options de base, communes local + CI
    ydl_opts: dict = {
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
        # Activer un runtime JS (YouTube extraction devient plus stricte).
        # Local : tu peux ignorer si tu n'as pas Node/QuickJS.
        "js_runtimes": {"node": {}},
        # Un peu de logs dans la console
        "verbose": True,
    }

    # Si un fichier cookies est fourni (GitHub Actions), on l'utilise
    if cookies_file.exists():
        ydl_opts["cookiefile"] = str(cookies_file)

    # --- Options avancées YouTube (PO Token, client mweb, remote-components) ---
    #
    # Tout est contrôlé par des variables d'environnement pour que tu puisses
    # facilement activer/désactiver ces mécanismes en local ou en CI.

    extractor_args: dict = {}

    # 1) Client mweb + PO Token (recommandé par yt-dlp pour YouTube en 2025+)
    #
    #   YT_PO_TOKEN : valeur du PO Token au format attendu par yt-dlp
    #   (la doc recommande "mweb+PO_TOKEN_VALUE").
    #
    #   En pratique :
    #     export YT_PO_TOKEN="mweb+...ton-token..."
    #
    po_token_env = os.getenv("YT_PO_TOKEN")
    if po_token_env:
        extractor_args.setdefault("youtube", {})
        # Forcer le client mweb
        extractor_args["youtube"].setdefault("player_client", []).append("mweb")
        # PO Token pour ce client
        extractor_args["youtube"].setdefault("po_token", []).append(po_token_env)

    if extractor_args:
        ydl_opts["extractor_args"] = extractor_args

    # 2) Remote components (EJS) pour résoudre les challenges JS si nécessaire
    #
    #   YT_REMOTE_COMPONENTS, ex: "ejs:github" ou "ejs:npm"
    #
    remote_components_env = os.getenv("YT_REMOTE_COMPONENTS")
    if remote_components_env:
        rc_map: dict = {}
        for part in remote_components_env.split(","):
            part = part.strip()
            if not part:
                continue
            if ":" not in part:
                continue
            kind, value = part.split(":", 1)
            kind = kind.strip()
            value = value.strip()
            if not kind or not value:
                continue
            rc_map.setdefault(kind, []).append(value)
        if rc_map:
            ydl_opts["remote_components"] = rc_map

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

