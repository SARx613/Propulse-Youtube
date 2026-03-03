"""
Upload des vidéos téléchargées vers TA chaîne YouTube.

Ce script suppose :
  - que les vidéos ont été téléchargées par shorts_downloader.py
  - que tu as configuré l'API YouTube Data v3 avec OAuth2

Étapes de configuration (une seule fois) :
  1. Aller sur https://console.cloud.google.com/
  2. Créer un projet (si pas déjà fait)
  3. Activer "YouTube Data API v3"
  4. Créer des identifiants OAuth 2.0 de type "Application de bureau"
  5. Télécharger le fichier JSON et le sauvegarder ici sous le nom :
       client_secrets.json
  6. Lancer ce script une première fois pour effectuer le "consent"
     (une fenêtre de navigateur va s'ouvrir, tu choisis ton compte YouTube
      et tu autorises l'accès).

Inspiré des exemples officiels Google.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from datetime import datetime

import google.auth.exceptions
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload


BASE_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
UPLOAD_ARCHIVE_FILE = BASE_DIR / "uploaded_videos.txt"
DAILY_UPLOADS_FILE = BASE_DIR / "daily_uploads.txt"

# Portée minimale pour uploader des vidéos sur TA chaîne
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_youtube_service():
    """
    Initialise le client YouTube Data API v3 avec OAuth2.
    Nécessite un fichier client_secrets.json dans le dossier courant.
    """
    creds = None
    token_file = BASE_DIR / "token.json"

    # Si un token existe déjà, on le réutilise
    if token_file.exists():
        try:
            from google.oauth2.credentials import Credentials

            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        except (google.auth.exceptions.GoogleAuthError, ValueError):
            creds = None

    # Si pas de credentials valides, on tente un refresh puis, en dernier recours,
    # on lance le flow OAuth (mais uniquement en local, pas en CI GitHub Actions).
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        if not creds:
            # Dans GitHub Actions, on NE DOIT PAS lancer de flow interactif
            # (pas de navigateur). On s'arrête donc avec un message explicite.
            if os.getenv("GITHUB_ACTIONS") == "true":
                raise RuntimeError(
                    "Impossible d'obtenir un token YouTube valide dans GitHub Actions.\n"
                    "Vérifie que le secret TOKEN_JSON contient le contenu complet de "
                    "ton fichier token.json généré en local après consent OAuth."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(BASE_DIR / "client_secrets.json"), SCOPES
            )
            creds = flow.run_local_server(port=0)
            token_file.write_text(creds.to_json(), encoding="utf-8")

    return build("youtube", "v3", credentials=creds)


def load_uploaded_ids() -> set[str]:
    if not UPLOAD_ARCHIVE_FILE.exists():
        return set()
    return {
        line.strip()
        for line in UPLOAD_ARCHIVE_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def save_uploaded_ids(ids: set[str]) -> None:
    UPLOAD_ARCHIVE_FILE.write_text(
        "\n".join(sorted(ids)) + "\n", encoding="utf-8"
    )


def load_daily_upload_counts() -> dict[str, int]:
    """
    Lit le nombre d'uploads par jour (clé = 'YYYY-MM-DD').
    Utilisé pour limiter le total quotidien (pour éviter le ban).
    """
    if not DAILY_UPLOADS_FILE.exists():
        return {}
    counts: dict[str, int] = {}
    for raw in DAILY_UPLOADS_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or " " not in line:
            continue
        date_str, count_str = line.split(" ", 1)
        try:
            counts[date_str] = int(count_str)
        except ValueError:
            continue
    return counts


def save_daily_upload_counts(counts: dict[str, int]) -> None:
    lines = [f"{day} {count}" for day, count in sorted(counts.items())]
    DAILY_UPLOADS_FILE.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def extract_ids_and_title_from_filename(path: Path) -> tuple[str, str, str]:
    """
    À partir du chemin du fichier téléchargé, essaie de reconstruire :
      - creator_handle ou nom (basé sur le dossier ou le pattern),
      - video_id
      - video_title (plus ou moins propre)

    Format actuel de download :
      downloads/%(uploader)s/%(upload_date)s_%(id)s_%(title)s.%(ext)s
    """
    uploader = path.parent.name  # dossier = nom de la chaîne (uploader)

    stem = path.stem  # "20260302_IrOO1wVQzyI_Why_your_hustle_is_breaking_you"
    parts = stem.split("_", 2)
    if len(parts) < 3:
        # fallback très simple
        return uploader, stem, stem

    _, video_id, title_part = parts
    # Remettre des espaces à la place des underscores restants
    title = title_part.replace("_", " ").strip()
    return uploader, video_id, title


def build_final_title(
    creator_name_or_handle: str,
    original_title: str,
) -> str:
    """
    Construit le titre final :
      "@Creator - Titre original"

    Si creator_name_or_handle ne commence pas par '@',
    on préfixe automatiquement.
    """
    handle = (
        creator_name_or_handle
        if creator_name_or_handle.startswith("@")
        else f"@{creator_name_or_handle}"
    )
    return f"{handle} - {original_title}"


def upload_single_video(youtube, video_path: Path) -> Optional[str]:
    """
    Upload une seule vidéo sur TA chaîne YouTube.
    Retourne l'ID de la vidéo YouTube créée, ou None en cas d'erreur.
    """
    creator_name, original_id, original_title = extract_ids_and_title_from_filename(
        video_path
    )
    final_title = build_final_title(creator_name, original_title)

    print(f"Upload de {video_path.name} avec le titre : {final_title}")

    body = {
        "snippet": {
            "title": final_title,
            "description": f"Repost de @{creator_name} – Vidéo originale : {original_title}",
            "categoryId": "22",  # People & Blogs (par défaut)
        },
        "status": {
            "privacyStatus": "public",  # change en "public" si tu veux
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)

    try:
        request = youtube.videos().insert(
            part="snippet,status", body=body, media_body=media
        )
        response = request.execute()
        video_id = response.get("id")
        print(f"Upload réussi, vidéo YouTube ID = {video_id}")
        return video_id
    except HttpError as e:
        print(f"Erreur HTTP pendant l'upload : {e}")
        return None


def upload_all_new_videos(
    max_uploads_per_run: Optional[int] = None,
    max_uploads_per_day: Optional[int] = None,
) -> None:
    """
    Parcourt le dossier downloads/ et upload toutes les vidéos
    qui n'ont pas encore été marquées comme uploadées.
    """
    youtube = get_youtube_service()
    uploaded_ids = load_uploaded_ids()

    # Charge le compteur quotidien (par date) pour limiter à X uploads/jour.
    today_str = datetime.now().date().isoformat()
    daily_counts = load_daily_upload_counts()
    daily_count = daily_counts.get(today_str, 0)

    if not DOWNLOADS_DIR.exists():
        print(f"Aucun dossier {DOWNLOADS_DIR} trouvé.")
        return

    # Récupère toutes les vidéos non encore uploadées
    candidates = []
    for mp4 in DOWNLOADS_DIR.rglob("*.mp4"):
        key = str(mp4.relative_to(DOWNLOADS_DIR))
        if key in uploaded_ids:
            continue
        candidates.append((mp4, key))

    # Trie par date de modification décroissante (plus récent en premier)
    candidates.sort(key=lambda item: item[0].stat().st_mtime, reverse=True)

    # Upload dans l'ordre souhaité, avec des limites éventuelles
    uploaded_count = 0
    for mp4, key in candidates:
        if max_uploads_per_run is not None and uploaded_count >= max_uploads_per_run:
            print(
                f"Limite par exécution atteinte ({max_uploads_per_run} vidéos). "
                "Arrêt de cette passe."
            )
            break
        if max_uploads_per_day is not None and daily_count >= max_uploads_per_day:
            print(
                f"Limite quotidienne atteinte pour {today_str} "
                f"({daily_count}/{max_uploads_per_day} vidéos)."
            )
            break

        new_video_id = upload_single_video(youtube, mp4)
        if new_video_id:
            uploaded_ids.add(key)
            save_uploaded_ids(uploaded_ids)
            uploaded_count += 1
            daily_count += 1
            daily_counts[today_str] = daily_count
            save_daily_upload_counts(daily_counts)


if __name__ == "__main__":
    # Limite par exécution (par défaut 50 si non définie)
    raw_per_run = os.getenv("MAX_UPLOADS_PER_RUN")
    max_per_run: Optional[int]
    try:
        max_per_run = int(raw_per_run) if raw_per_run else 50
    except ValueError:
        max_per_run = 50

    # Limite quotidienne (par défaut 100 si non définie)
    raw_per_day = os.getenv("MAX_UPLOADS_PER_DAY")
    max_per_day: Optional[int]
    try:
        max_per_day = int(raw_per_day) if raw_per_day else 100
    except ValueError:
        max_per_day = 100

    upload_all_new_videos(
        max_uploads_per_run=max_per_run,
        max_uploads_per_day=max_per_day,
    )

