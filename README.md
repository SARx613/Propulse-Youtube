# Youtube Shorts – MVP téléchargement automatique

Ce mini-projet télécharge automatiquement les **nouveaux Shorts YouTube** de la chaîne :

`https://www.youtube.com/@ShiYunshan`

Il utilise `yt-dlp` et un fichier d'archive pour **ne pas retélécharger** les vidéos déjà traitées.

---

## 1. Installation

Dans ce dossier :

```bash
cd "/Users/simonamar-roisenberg/Desktop/Youtube Shorts"
python3 -m venv .venv
source .venv/bin/activate  # macOS / Linux
pip install -r requirements.txt
```

---

## 2. Lancer un téléchargement manuel

```bash
cd "/Users/simonamar-roisenberg/Desktop/Youtube Shorts"
source .venv/bin/activate
python shorts_downloader.py
```

Les vidéos seront téléchargées dans le dossier `downloads/` avec une structure du type :

- `downloads/<NomDeLaChaîne>/<date>_<id>_<titre>.mp4`

Seules les vidéos de **durée <= 60s** sont téléchargées (Shorts).

Un fichier `archive.txt` garde la trace des vidéos déjà téléchargées.

---

## 3. Surveiller plusieurs chaînes avec `channels.txt`

Tu peux lister plusieurs chaînes dans le fichier `channels.txt` à la racine du projet.

Format :

- une chaîne par ligne
- soit un handle : `@ShiYunshan`
- soit une URL complète : `https://www.youtube.com/@ShiYunshan`
- lignes vides ou commençant par `#` sont ignorées

Exemple :

```text
@ShiYunshan
@AutreCreateur
https://www.youtube.com/@EncoreUnAutre
```

Le watcher lira ce fichier à chaque passe et vérifiera toutes les chaînes listées.

---

## 4. Mode "trigger" simple (watcher en continu)

Tu peux lancer un petit watcher qui vérifie automatiquement la chaîne toutes les **300 secondes** et télécharge les nouveaux Shorts dès qu'ils apparaissent.

```bash
cd "/Users/simonamar-roisenberg/Desktop/Youtube Shorts"
source .venv/bin/activate
python shorts_watcher.py
```

Tant que ce script tourne, chaque nouvel upload (Short ≤ 60s) sur **toutes les chaînes de `channels.txt`** sera détecté et téléchargé automatiquement (grâce au fichier `archive.txt`, rien n'est téléchargé deux fois).

---

## 5. Automatiser avec cron (optionnel)

Sur macOS, tu peux utiliser `cron` pour lancer le script régulièrement.

1. Ouvre l'éditeur de crontab :

```bash
crontab -e
```

2. Ajoute une ligne pour lancer le script toutes les 5 minutes (par exemple) :

```bash
*/5 * * * * cd "/Users/simonamar-roisenberg/Desktop/Youtube Shorts" && /usr/bin/env bash -c 'source .venv/bin/activate && python shorts_downloader.py' >> shorts_cron.log 2>&1
```

Pense à adapter le chemin vers Python/ton venv si besoin.

---

## 6. Upload vers TA chaîne YouTube

Le script `upload_to_youtube.py` permet d'uploader automatiquement les vidéos
téléchargées (dans `downloads/`) sur **ta** chaîne YouTube.

APIs utilisées :

- **YouTube Data API v3** via `google-api-python-client`
- Authentification OAuth2 via :
  - `google-auth-oauthlib`
  - `google-auth-httplib2`

Étapes de configuration :

1. Aller sur la Google Cloud Console (`console.cloud.google.com`).
2. Créer un projet (si nécessaire).
3. Activer **YouTube Data API v3**.
4. Créer des identifiants **OAuth 2.0** de type "Application de bureau".
5. Télécharger le JSON et le sauvegarder dans ce dossier sous le nom `client_secrets.json`.
6. Dans le venv, lancer une première fois :

   ```bash
   python upload_to_youtube.py
   ```

   Une fenêtre de navigateur va s'ouvrir pour te connecter et autoriser l'accès à ta chaîne.

Le script :

- parcourt tous les `.mp4` dans `downloads/`
- reconstruit le nom du créateur et le titre original à partir du nom de fichier
- crée un titre de la forme :

  `@NomDeLaChaine - Titre original`

- garde une trace des fichiers déjà uploadés dans `uploaded_videos.txt`.

---

## 7. Remarques

- Ces scripts reposent sur `yt-dlp` et l'API YouTube, qui peuvent changer dans le temps.
- Respecte les **Conditions d'utilisation de YouTube** : utilise ce système uniquement pour ta chaîne ou des contenus pour lesquels tu as les droits explicites.

