import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import warnings
import threading
import json
import os
from tkinter import filedialog
import requests
from PIL import Image, ImageTk
import io
from urllib.parse import quote


warnings.filterwarnings("ignore", category=FutureWarning)

USING_NEW_SDK = None

try:
    from google import genai
    _ = genai.Client
    USING_NEW_SDK = True
except (ImportError, AttributeError):
    try:
        import google.generativeai as genai_legacy
        USING_NEW_SDK = False
    except ImportError:
        USING_NEW_SDK = None

GEMINI_MODEL_NAME = "gemini-2.5-flash"
LASTFM_BASE_URL = "https://ws.audioscrobbler.com/2.0/"

GEMINI_API_KEY = "AQ.Ab8RN6JHHTvngCQycJ91t6eTWEBPeA1LYB36mQYGeAm2__b3WA"  # Buraya Google AI Studio'dan aldığın anahtarı yapıştır
LASTFM_API_KEY = "1dc7d6f0c651506352ecba5987bd7a62"  # Buraya Last.fm'den aldığın API anahtarını yapıştır


class GeminiAlbumGenerationError(Exception):
    pass

def open_listen_link(url):
    if url:
        webbrowser.open(url)
    else:
        messagebox.showwarning("Link Not Found", "This track does not have a Last.fm page.")

def build_gemini_prompt(journal_text, genre, era, track_count):
    return f"""
You are a music industry expert and creative album concept generator.

Create a fictional album concept based on the user's journal entry and selected parameters.
Return ONLY one valid raw JSON object.
Do not include markdown code fences.
Do not include explanations.
Do not include comments.
Do not include any text before or after the JSON.

The JSON object must match this schema exactly:

{{
  "album_name": "string",
  "artist_name": "string",
  "year": "string",
  "label": "string",
  "mood_description": "string",
  "cover_prompt": "string",
  "lastfm_tags": ["string", "string", "string", "string"]
}}

User input:
- Journal / mood text: "{journal_text}"
- Selected genre: "{genre}"
- Selected era: "{era}"
- Requested track count: {track_count}

Rules:
1. album_name, artist_name, year, and label must be fictional.
2. year must be a realistic year from the selected era: "{era}".
3. mood_description must be one clear sentence describing the album vibe.
4. cover_prompt must be a detailed visual prompt suitable for AI album cover generation.
5. lastfm_tags must contain 4 to 6 lowercase Last.fm-compatible music or mood tags.
6. lastfm_tags must match the journal mood, selected genre, and selected era.
8. For Turkish music, use tags such as "turkish pop", "turkish", "arabesque", "anatolian rock", or "turkish rock" when appropriate.
9. Do not use real album names.
10. Do not use real record label names.
11. Return only valid JSON.
"""




def clean_gemini_json_text(text):
    if not text:
        raise GeminiAlbumGenerationError("Gemini returned an empty response.")
    text = text.strip()
    if text.startswith("```"):
        text = text.replace("```json", "")
        text = text.replace("```JSON", "")
        text = text.replace("```", "")
        text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise GeminiAlbumGenerationError(
            "Gemini response does not contain a valid JSON object."
        )

    return text[start:end + 1].strip()

def validate_album_metadata(data):
    required_fields = [
        "album_name",
        "artist_name",
        "year",
        "label",
        "mood_description",
        "cover_prompt",
        "lastfm_tags"
    ]
    for field in required_fields:
        if field not in data:
            raise GeminiAlbumGenerationError(
                f"Missing required field in Gemini response: {field}"
            )
    string_fields = [
        "album_name",
        "artist_name",
        "year",
        "label",
        "mood_description",
        "cover_prompt",
    ]
    for field in string_fields:
        if not isinstance(data[field], str):
            raise GeminiAlbumGenerationError(
                f"Field '{field}' must be a string."
            )
    if not isinstance(data["lastfm_tags"], list):
        raise GeminiAlbumGenerationError("lastfm_tags must be a list.")

    cleaned_tags = []

    for tag in data["lastfm_tags"]:
        if isinstance(tag, str) and tag.strip():
            cleaned_tags.append(tag.strip().lower())
    if len(cleaned_tags) < 1:
        raise GeminiAlbumGenerationError(
            "Gemini did not return usable Last.fm tags."
        )
    data["lastfm_tags"] = cleaned_tags[:6]

    return data


class IndexCastError:
    pass


def generate_album_metadata_via_requests(journal_text, genre, era, track_count, api_key):
    """Google kütüphanesine ihtiyaç duymadan doğrudan HTTP POST ile Gemini API'yi tetikler."""
    if not api_key or api_key.strip() in ["", "YOUR_GEMINI_API_KEY_HERE"]:
        raise Exception("Gemini API key is missing. Please update it in the code.")

    if not journal_text or not journal_text.strip():
        raise Exception("Journal text cannot be empty.")

    prompt = build_gemini_prompt(journal_text.strip(), genre, era, track_count)

    # Kütüphanesiz REST API adresi
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()

    response_data = response.json()
    try:
        raw_text = response_data['candidates'][0]['content']['parts'][0]['text'].strip()
    except (KeyError, IndexCastError):
        raise Exception("Failed to parse response structure from Gemini API.")

    cleaned_text = clean_gemini_json_text(raw_text)
    metadata = json.loads(cleaned_text)
    return validate_album_metadata(metadata)

def normalize_track(track_name, artist_name, url):
    return {"name": track_name, "artist": artist_name, "url": url}

def fetch_tracks_by_tag(tag, limit=10):
    if not tag:
        return []

    params = {
        "method": "tag.gettoptracks",
        "tag": tag,
        "limit": limit,
        "api_key": LASTFM_API_KEY,
        "format": "json"
    }

    headers = {
        "User-Agent": "AlbumCoverStudio/1.0"
    }
    try:
        response = requests.get(
            LASTFM_BASE_URL,
            params=params,
            headers=headers,
            timeout=15
        )
        response.raise_for_status()

        data = response.json()
        raw_tracks = data.get("tracks", {}).get("track", [])

        tracks = []

        for item in raw_tracks:
            track_name = item.get("name")
            artist_data = item.get("artist")
            url = item.get("url")

            if isinstance(artist_data, dict):
                artist_name = artist_data.get("name")
            else:
                artist_name = artist_data

            if track_name and artist_name:
                tracks.append(
                    normalize_track(track_name, artist_name, url)
                )

        return tracks

    except requests.RequestException as error:
        print(f"Last.fm tag request failed for tag '{tag}': {error}")
        return []

    except ValueError:
        print("Last.fm tag response could not be parsed as JSON.")
        return []

def fetch_tracks_by_artist(artist_name, limit=10):
    """Last.fm artist.gettoptracks endpoint'ini kullanarak sanatçı şarkılarını çeker."""
    if not artist_name:
        return []

    params = {
        "method": "artist.gettoptracks",
        "artist": artist_name,
        "limit": limit,
        "api_key": LASTFM_API_KEY,
        "format": "json"
    }
    headers = {"User-Agent": "AlbumCoverStudio/1.0"}
    try:
        response = requests.get(LASTFM_BASE_URL, params=params, headers=headers, timeout=15)
        response.raise_for_status()

        data = response.json()
        raw_tracks = data.get("toptracks", {}).get("track", [])

        tracks = []
        for item in raw_tracks:
            track_name = item.get("name")
            artist_data = item.get("artist")
            url = item.get("url")

            if isinstance(artist_data, dict):
                artist_name_from_api = artist_data.get("name", artist_name)
            else:
                artist_name_from_api = artist_name

            if track_name and artist_name_from_api:
                tracks.append(normalize_track(track_name, artist_name_from_api, url))
        return tracks
    except Exception as error:
        print(f"Last.fm artist request failed for artist '{artist_name}': {error}")
        return []

def remove_duplicate_tracks(tracks):
    unique_tracks = []
    seen_tracks = set()

    for track in tracks:
        track_name = track.get("name", "").strip().lower()
        artist_name = track.get("artist", "").strip().lower()

        unique_key = f"{track_name} - {artist_name}"

        if track_name and artist_name and unique_key not in seen_tracks:
            seen_tracks.add(unique_key)
            unique_tracks.append(track)

    return unique_tracks

def get_tracks_from_tags(tags, target_count):
    """Birden fazla etiket sonucunu birleştirir ve tekilleştirir."""
    if not isinstance(tags, list):
        tags = [str(tags)]

    all_tracks = []
    for tag in tags:
        tag_tracks = fetch_tracks_by_tag(tag=tag, limit=target_count * 2)
        all_tracks.extend(tag_tracks)

    unique_tracks = remove_duplicate_tracks(all_tracks)
    return unique_tracks[:target_count]

def build_tracklist(tags, target_count, artist_hint=""):

    final_tracks = []

    if artist_hint:
        artist_tracks = fetch_tracks_by_artist(artist_name=artist_hint, limit=target_count)
        final_tracks.extend(artist_tracks)

    if len(final_tracks) < target_count:
        tag_tracks = get_tracks_from_tags(tags=tags, target_count=target_count)
        combined_tracks = final_tracks + tag_tracks
        final_tracks = remove_duplicate_tracks(combined_tracks)

    return final_tracks[:target_count]

def generate_cover(gemini_prompt, genre):
    """Pollinations.ai üzerinden albüm kapağını üretir."""
    combined_prompt = f"Album cover art, {gemini_prompt}, {genre} visual style, highly detailed, square format."
    encoded = quote(combined_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=600&height=600&nologo=true"

    response = requests.get(url, timeout=90)
    response.raise_for_status()
    return Image.open(io.BytesIO(response.content)).convert("RGB")

def update_status(text):
    root.after(0, lambda: status_label.config(text=text))

def display_results(album_data_param, tracklist_param, cover_image_param):
    global tk_cover_art
    placeholder_label.pack_forget()
    results_scroll_frame.pack(fill="both", expand=True)

    album_name_label.config(text=album_data_param.get("album_name", "Unknown Album"))
    album_meta_label.config(text=f"{album_data_param.get('year', '2026')} • {len(tracklist_param)} songs • {album_data_param.get('label', 'Indie')}")
    album_tags_label.config(text=f"Tags: {', '.join(album_data_param.get('lastfm_tags', []))}")

    if cover_image_param:
        resized_img = cover_image_param.resize((150, 150), Image.Resampling.LANCZOS)
        tk_cover_art = ImageTk.PhotoImage(resized_img)
        cover_canvas.delete("all")
        cover_canvas.create_image(0, 0, anchor="nw", image=tk_cover_art)

    for widget in tracks_inner_frame.winfo_children():
        widget.destroy()

    for index, track in enumerate(tracklist_param, start=1):
        track_row = tk.Frame(tracks_inner_frame, bg="#121212", pady=5)
        track_row.pack(fill="x", pady=2)

        num_lbl = tk.Label(track_row, text=str(index), font=("Helvetica", 10), fg="#B3B3B3", bg="#121212", width=3, anchor="w")
        num_lbl.pack(side="left")

        info_frame = tk.Frame(track_row, bg="#121212")
        info_frame.pack(side="left", fill="x", expand=True, padx=10)

        name_lbl = tk.Label(info_frame, text=track.get("name", "Unknown"), font=("Helvetica", 11, "bold"), fg="#FFFFFF", bg="#121212", anchor="w")
        name_lbl.pack(fill="x")

        artist_lbl = tk.Label(info_frame, text=track.get("artist", "Unknown"), font=("Helvetica", 9), fg="#B3B3B3", bg="#121212", anchor="w")
        artist_lbl.pack(fill="x")

        listen_btn = tk.Button(
            track_row, text="Listen", font=("Helvetica", 9, "bold"),
            bg="#282828", fg="#FFFFFF", activebackground="#3E3E3E", activeforeground="#FFFFFF",
            bd=0, padx=12, pady=4, cursor="hand2",
            command=lambda u=track.get("url"): open_listen_link(u)
        )
        listen_btn.pack(side="right", padx=5)

    save_btn.pack(fill="x", pady=(20, 0))


def generate_album():
    generate_btn.config(state="disabled")
    thread = threading.Thread(target=generate_album_worker)
    thread.daemon = True
    thread.start()


def generate_album_worker():

    global album_data, tracklist, cover_image
    try:
        update_status("🤖 Gemini is thinking...")

        album_data = generate_album_metadata_via_requests(
            journal_text=mood_text.get("1.0", "end-1c"),
            genre=genre_combobox.get(),
            era=era_combobox.get(),
            track_count=int(track_spinbox.get()),
            api_key=GEMINI_API_KEY
        )

        update_status("🎵 Fetching tracks...")
        tracklist = build_tracklist(
            tags=album_data["lastfm_tags"],
            target_count=int(track_spinbox.get()),
            artist_hint=album_data.get("artist_name", "")
        )

        update_status("🎨 Generating cover...")
        cover_image = generate_cover(
            album_data["cover_prompt"],
            genre_combobox.get()
        )

        update_status("✅ Album ready!")
        root.after(0, lambda: display_results(album_data, tracklist, cover_image))

    except Exception as e:
        update_status(f"❌ Error: {e}")
    finally:
        root.after(0, lambda: generate_btn.config(state="normal"))

def save_album():

    if not album_data or cover_image is None:
        update_status("⚠️ Generate an album first.")
        return

    folder = filedialog.askdirectory(
        title="Select folder"
    )

    if not folder:
        return
    json_path = os.path.join(folder, "album.json")

    with open(
        json_path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            {
                "album_name": album_data["album_name"],
                "artist_name": album_data["artist_name"],
                "year": album_data["year"],
                "label": album_data["label"],
                "mood_description": album_data["mood_description"],
                "cover_prompt": album_data["cover_prompt"],
                "lastfm_tags": album_data["lastfm_tags"],
                "tracklist": tracklist
            },
            f,
            ensure_ascii=False,
            indent=2
        )

    png_path = os.path.join(folder, "cover.png")

    cover_image.save(png_path)
    root.after(0, lambda: display_results(album_data, tracklist, cover_image))
    update_status("✅ Album saved successfully!")


root = tk.Tk()
root.title("Album Cover Studio")
root.geometry("1100x750")
root.configure(bg="#121212")

style = ttk.Style()
style.theme_use('clam')

# Genel Etiket Ayarları
style.configure('TLabel', background='#121212', foreground='#FFFFFF', font=('Helvetica', 10, 'bold'))

# ----------------------------------------------------
# COMBOBOX VE SPINBOX İÇİN KOYU MOD AYARLARI
# ----------------------------------------------------
# Giriş alanlarının arka planını koyu füme (#212124), yazılarını beyaz yapar
style.configure('TCombobox',
                fieldbackground='#212124',
                background='#212124',
                foreground='#FFFFFF',
                arrowcolor='#FFFFFF')

style.configure('TSpinbox',
                fieldbackground='#212124',
                background='#212124',
                foreground='#FFFFFF',
                arrowcolor='#FFFFFF')

# Seçim yaparken parlayan alanların (focus) renk ayarları
style.map('TCombobox',
          fieldbackground=[('readonly', '#212124')],
          foreground=[('readonly', '#FFFFFF')])

style.map('TSpinbox',
          fieldbackground=[('readonly', '#212124')],
          foreground=[('readonly', '#FFFFFF')])

# Combobox'a tıklandığında açılan listenin (dropdown pop-up) renklerini koyu mod yapmak için:
root.option_add('*TCombobox*Listbox.background', '#212124')
root.option_add('*TCombobox*Listbox.foreground', '#FFFFFF')
root.option_add('*TCombobox*Listbox.selectBackground', '#25a18e') # Seçilen satırın parlama rengi
root.option_add('*TCombobox*Listbox.selectForeground', '#FFFFFF')
root.option_add('*TCombobox*Listbox.font', ('Helvetica', 10))

# Ana Başlık Şeridi
top_title_frame = tk.Frame(root, bg="#121212", padx=20, pady=10)
top_title_frame.pack(fill="x")

title_label = tk.Label(top_title_frame, text="Album Cover Studio", font=("Helvetica", 20, "bold"), fg="#FFFFFF", bg="#121212")
title_label.pack(anchor="w")
subtitle_label = tk.Label(top_title_frame, text="Describe your mood, enjoy the generated tracklist.", font=("Helvetica", 10), fg="#B3B3B3", bg="#121212")
subtitle_label.pack(anchor="w")

# ----------------------------------------------------
# 1. EN ÜST KATMAN: FİLTRELEME ŞEYSİ (Yan Yana)
# ----------------------------------------------------
filter_bar_frame = tk.Frame(root, bg="#181818", padx=20, pady=15, bd=1, relief="flat")
filter_bar_frame.pack(fill="x", padx=20, pady=5)

# Tür Seçimi
genre_sub_frame = tk.Frame(filter_bar_frame, bg="#181818")
genre_sub_frame.pack(side="left", expand=True, fill="x", padx=10)
genre_label = ttk.Label(genre_sub_frame, text="Genre:", style='TLabel')
genre_label.config(background='#181818')
genre_label.pack(anchor="w", pady=(0, 2))
genres = ["Pop", "Rock", "Hip-Hop / Rap", "Electronic", "Indie", "R&B / Soul", "Jazz", "Metal", "Türk Pop", "Klasik"]
genre_combobox = ttk.Combobox(genre_sub_frame, values=genres, state="readonly")
genre_combobox.set("Rock")
genre_combobox.pack(fill="x")

# Dönem Seçimi
era_sub_frame = tk.Frame(filter_bar_frame, bg="#181818")
era_sub_frame.pack(side="left", expand=True, fill="x", padx=10)
era_label = ttk.Label(era_sub_frame, text="Era:", style='TLabel')
era_label.config(background='#181818')
era_label.pack(anchor="w", pady=(0, 2))
eras = ["1970s", "1980s", "1990s", "2000s", "2010s", "2020s"]
era_combobox = ttk.Combobox(era_sub_frame, values=eras, state="readonly")
era_combobox.set("2000s")
era_combobox.pack(fill="x")

# Şarkı Sayısı Seçimi
track_sub_frame = tk.Frame(filter_bar_frame, bg="#181818")
track_sub_frame.pack(side="left", expand=True, fill="x", padx=10)
track_label = ttk.Label(track_sub_frame, text="Track Count (6-14):", style='TLabel')
track_label.config(background='#181818')
track_label.pack(anchor="w", pady=(0, 2))
track_spinbox = ttk.Spinbox(track_sub_frame, from_=6, to=14, state="readonly")
track_spinbox.set(10)
track_spinbox.pack(fill="x")

# ----------------------------------------------------
# 2. ORTA KATMAN: SONUÇLAR VE ŞARKI ÖNERİLERİ
# ----------------------------------------------------
middle_results_frame = tk.Frame(root, bg="#121212", padx=20, pady=10)
middle_results_frame.pack(fill="both", expand=True, padx=20, pady=5)

# Sol Kısım: Albüm Detayları ve Kapak Resmi
left_output_frame = tk.Frame(middle_results_frame, bg="#121212", width=200)
left_output_frame.pack(side="left", fill="y", padx=(0, 20))

cover_canvas = tk.Canvas(left_output_frame, width=150, height=150, bg="#282828", bd=0, highlightthickness=0)
cover_canvas.pack(pady=(10, 10))

album_type_lbl = tk.Label(left_output_frame, text="ALBUM (GENERATED BY AI)", font=("Helvetica", 8, "bold"), fg="#B3B3B3", bg="#121212")
album_type_lbl.pack(anchor="w")

album_name_label = tk.Label(left_output_frame, text="", font=("Helvetica", 14, "bold"), fg="#FFFFFF", bg="#121212", justify="left", wraplength=180)
album_name_label.pack(anchor="w", pady=(2, 2))

album_meta_label = tk.Label(left_output_frame, text="", font=("Helvetica", 9), fg="#B3B3B3", bg="#121212")
album_meta_label.pack(anchor="w")

album_tags_label = tk.Label(left_output_frame, text="", font=("Helvetica", 9, "italic"), fg="#25a18e", bg="#121212", justify="left", wraplength=180)
album_tags_label.pack(anchor="w", pady=(5, 0))

# Sağ Kısım: Genişleyen Şarkı Listesi Mockup Alanı
right_tracks_frame = tk.Frame(middle_results_frame, bg="#121212")
right_tracks_frame.pack(side="right", fill="both", expand=True)

placeholder_label = tk.Label(right_tracks_frame, text="Generated tracklist will be shown here.", font=("Helvetica", 12, "italic"), fg="#535353", bg="#121212")
placeholder_label.pack(expand=True)

results_scroll_frame = tk.Frame(right_tracks_frame, bg="#121212")

tracks_title = tk.Label(results_scroll_frame, text="#   Title & Artist", font=("Helvetica", 10, "bold"), fg="#B3B3B3", bg="#121212")
tracks_title.pack(anchor="w", pady=(0, 5))

# Kaydırılabilir Şarkı Satırları Kutusu
tracks_inner_frame = tk.Frame(results_scroll_frame, bg="#121212")
tracks_inner_frame.pack(fill="both", expand=True)

save_btn = tk.Button(
    results_scroll_frame, text="SAVE ALBUM (JSON + PNG)", font=("Helvetica", 11, "bold"),
    bg="#25a18e", fg="#FFFFFF", activebackground="#208778", activeforeground="#FFFFFF",
    bd=0, pady=8, cursor="hand2", command=save_album
)

# ----------------------------------------------------
# 3. EN ALT KATMAN: MOOD METİN ALANI VE BUTON (Şerit Halinde)
# ----------------------------------------------------
bottom_input_frame = tk.Frame(root, bg="#181818", padx=20, pady=15)
bottom_input_frame.pack(fill="x", side="bottom")

# Mood Sol Blok
mood_entry_container = tk.Frame(bottom_input_frame, bg="#181818")
mood_entry_container.pack(side="left", fill="both", expand=True, padx=(0, 15))

mood_label = tk.Label(mood_entry_container, text="Your Mood (English or Turkish):", font=("Helvetica", 10, "bold"), fg="#25a18e", bg="#181818")
mood_label.pack(anchor="w", pady=(0, 4))

mood_text = tk.Text(mood_entry_container, height=3, bg="#282828", fg="#FFFFFF", insertbackground="white", font=("Helvetica", 10), bd=0, padx=10, pady=8, wrap="word")
mood_text.insert("1.0", "I was looking at the sea in Izmir. It was raining softly, and an old song was playing through my headphones. I felt both peaceful and melancholic.")
mood_text.pack(fill="both", expand=True)

# Buton ve Statü Sağ Blok
button_container = tk.Frame(bottom_input_frame, bg="#181818")
button_container.pack(side="right", fill="y", anchor="e")

generate_btn = tk.Button(
    button_container, text="GENERATE ALBUM", font=("Helvetica", 12, "bold"), bg="#25a18e", fg="#FFFFFF",
    activebackground="#208778", activeforeground="#FFFFFF", bd=0, padx=25, cursor="hand2", command=generate_album
)
generate_btn.pack(fill="both", expand=True, pady=(0, 5))

status_label = tk.Label(button_container, text="Ready", font=("Helvetica", 9, "italic"), fg="#B3B3B3", bg="#181818")
status_label.pack(anchor="w")

# TEST
album_data = {}
tracklist = []
cover_image = None
tk_cover_art = None

if __name__ == "__main__":
    root.mainloop()


