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

import google.auth.exceptions
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload


BASE_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
UPLOAD_ARCHIVE_FILE = BASE_DIR / "uploaded_videos.txt"

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

    # Si pas de credentials valides, on lance le flow OAuth
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())  # type: ignore[name-defined]
            except Exception:
                creds = None
        if not creds:
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


def upload_all_new_videos(max_uploads: Optional[int] = None) -> None:
    """
    Parcourt le dossier downloads/ et upload toutes les vidéos
    qui n'ont pas encore été marquées comme uploadées.
    """
    youtube = get_youtube_service()
    uploaded_ids = load_uploaded_ids()

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

    # Upload dans l'ordre souhaité, avec une limite éventuelle
    uploaded_count = 0
    for mp4, key in candidates:
        if max_uploads is not None and uploaded_count >= max_uploads:
            break

        new_video_id = upload_single_video(youtube, mp4)
        if new_video_id:
            uploaded_ids.add(key)
            save_uploaded_ids(uploaded_ids)
            uploaded_count += 1


if __name__ == "__main__":
    raw_max = os.getenv("MAX_UPLOADS_PER_RUN")
    max_uploads: Optional[int]
    try:
        max_uploads = int(raw_max) if raw_max else None
    except ValueError:
        max_uploads = None

    upload_all_new_videos(max_uploads=max_uploads)

