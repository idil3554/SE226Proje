import tkinter as tk
from tkinter import ttk
import webbrowser


def open_listen_link(url):

    if url:
        webbrowser.open(url)


def simulate_backend_response():


    placeholder_label.pack_forget()

    results_scroll_frame.pack(fill="both", expand=True)

    album_name_label.config(text="Aegean Rain")
    album_meta_label.config(text="2026 • 5 songs • Azure Soundscapes")
    album_tags_label.config(text="Tags: melancholic, rainy day, izmir, calm")

    cover_canvas.create_rectangle(0, 0, 150, 150, fill="#282828", outline="")
    cover_canvas.create_text(75, 75, text="Cover Art\n(600x600)", fill="#B3B3B3", justify="center")

    for widget in tracks_inner_frame.winfo_children():
        widget.destroy()

    mock_tracks = [
        {"name": "Beginning", "artist": "Ludovico Einaudi",
         "url": "https://www.last.fm/music/Ludovico+Einaudi/_/Beginning"},
        {"name": "Hong Kong", "artist": "Gorillaz", "url": "https://www.last.fm/music/Gorillaz/_/Hong+Kong"},
        {"name": "Sentimental", "artist": "Porcupine Tree",
         "url": "https://www.last.fm/music/Porcupine+Tree/_/Sentimental"},
        {"name": "Overprotected", "artist": "Britney Spears",
         "url": "https://www.last.fm/music/Britney+Spears/_/Overprotected"},
        {"name": "The Planets, Op. 32: IV. Jupiter", "artist": "Gustav Holst",
         "url": "https://www.last.fm/music/Gustav+Holst/_/The+Planets,+Op.+32:+IV.+Jupiter"}
    ]

    for index, track in enumerate(mock_tracks, start=1):
        track_row = tk.Frame(tracks_inner_frame, bg="#121212", pady=5)
        track_row.pack(fill="x", pady=2)

        # Sıra Numarası
        num_lbl = tk.Label(track_row, text=str(index), font=("Helvetica", 10), fg="#B3B3B3", bg="#121212", width=3,
                           anchor="w")
        num_lbl.pack(side="left")

        # Şarkı Adı ve Sanatçı (Alt alta durması için küçük bir iç frame)
        info_frame = tk.Frame(track_row, bg="#121212")
        info_frame.pack(side="left", fill="x", expand=True, padx=10)

        name_lbl = tk.Label(info_frame, text=track["name"], font=("Helvetica", 11, "bold"), fg="#FFFFFF", bg="#121212",
                            anchor="w")
        name_lbl.pack(fill="x")

        artist_lbl = tk.Label(info_frame, text=track["artist"], font=("Helvetica", 9), fg="#B3B3B3", bg="#121212",
                              anchor="w")
        artist_lbl.pack(fill="x")

        listen_btn = tk.Button(
            track_row, text="Listen", font=("Helvetica", 9, "bold"),
            bg="#282828", fg="#FFFFFF", activebackground="#3E3E3E", activeforeground="#FFFFFF",
            bd=0, padx=12, pady=4, cursor="hand2",
            command=lambda u=track["url"]: open_listen_link(u)
        )
        listen_btn.pack(side="right", padx=5)

    save_btn.pack(fill="x", pady=(20, 0))
    status_label.config(text="Album generated successfully!")


def on_generate_click():
    status_label.config(text="Gemini is thinking...")

    root.after(1000, simulate_backend_response)


root = tk.Tk()
root.title("Album Cover Studio")
root.geometry("1100x700")
root.configure(bg="#121212")

root.columnconfigure(0, weight=4)  # Sol panel genişlik oranı
root.columnconfigure(1, weight=6)  # Sağ panel genişlik oranı
root.rowconfigure(0, weight=1)

style = ttk.Style()
style.theme_use('clam')
style.configure('TLabel', background='#181818', foreground='#FFFFFF', font=('Helvetica', 10))
style.configure('TCombobox', fieldbackground='#282828', background='#282828', foreground='#FFFFFF')
style.configure('TSpinbox', fieldbackground='#282828', background='#282828', foreground='#FFFFFF')

# ================= SOL PANEL (Giriş Alanları) =================
left_frame = tk.Frame(root, bg="#181818", padx=25, pady=25)
left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

title_label = tk.Label(left_frame, text="Album Cover Studio", font=("Helvetica", 20, "bold"), fg="#FFFFFF",
                       bg="#181818")
title_label.pack(anchor="w", pady=(0, 5))

subtitle_label = tk.Label(left_frame, text="Describe your mood, enjoy the generated tracklist.", font=("Helvetica", 10),
                          fg="#B3B3B3", bg="#181818")
subtitle_label.pack(anchor="w", pady=(0, 25))

mood_label = tk.Label(left_frame, text="Your Mood (English or Turkish):", font=("Helvetica", 10, "bold"), fg="#1DB954",
                      bg="#181818")
mood_label.pack(anchor="w", pady=(5, 5))

mood_text = tk.Text(left_frame, height=8, width=35, bg="#282828", fg="#FFFFFF", insertbackground="white",
                    font=("Helvetica", 10), bd=0, padx=10, pady=10)
mood_text.insert("1.0",
                 "I was looking at the sea in Izmir. It was raining softly, and an old song was playing through my headphones. I felt both peaceful and melancholic.")
mood_text.pack(fill="x", pady=(0, 15))

genre_label = ttk.Label(left_frame, text="Genre:", style='TLabel')
genre_label.pack(anchor="w", pady=(5, 2))
genres = ["Pop", "Rock", "Hip-Hop / Rap", "Electronic", "Indie", "R&B / Soul", "Jazz", "Metal", "Türk Pop", "Klasik"]
genre_combobox = ttk.Combobox(left_frame, values=genres, state="readonly")
genre_combobox.set("Rock")
genre_combobox.pack(fill="x", pady=(0, 15))

era_label = ttk.Label(left_frame, text="Era:", style='TLabel')
era_label.pack(anchor="w", pady=(5, 2))
eras = ["1970s", "1980s", "1990s", "2000s", "2010s", "2020s"]
era_combobox = ttk.Combobox(left_frame, values=eras, state="readonly")
era_combobox.set("2000s")
era_combobox.pack(fill="x", pady=(0, 15))

track_label = ttk.Label(left_frame, text="Track Count (6-14):", style='TLabel')
track_label.pack(anchor="w", pady=(5, 2))
track_spinbox = ttk.Spinbox(left_frame, from_=6, to=14, state="readonly")
track_spinbox.set(10)
track_spinbox.pack(fill="x", pady=(0, 30))

generate_btn = tk.Button(left_frame, text="GENERATE ALBUM", font=("Helvetica", 12, "bold"), bg="#1DB954", fg="#FFFFFF",
                         activebackground="#1ed760", activeforeground="#FFFFFF", bd=0, pady=12, cursor="hand2",
                         command=on_generate_click)
generate_btn.pack(fill="x", pady=(0, 15))

status_label = tk.Label(left_frame, text="Ready", font=("Helvetica", 9, "italic"), fg="#B3B3B3", bg="#181818")
status_label.pack(anchor="w")

right_frame = tk.Frame(root, bg="#121212", padx=25, pady=25)
right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

placeholder_label = tk.Label(right_frame, text="Generated tracklist will be shown here.",
                             font=("Helvetica", 14, "italic"), fg="#535353", bg="#121212")
placeholder_label.pack(expand=True)

results_scroll_frame = tk.Frame(right_frame, bg="#121212")

header_frame = tk.Frame(results_scroll_frame, bg="#121212")
header_frame.pack(fill="x", anchor="w", pady=(0, 20))

cover_canvas = tk.Canvas(header_frame, width=150, height=150, bg="#282828", bd=0, highlightthickness=0)
cover_canvas.pack(side="left", padx=(0, 20))

album_info_frame = tk.Frame(header_frame, bg="#121212")
album_info_frame.pack(side="left", fill="both", expand=True)

album_type_lbl = tk.Label(album_info_frame, text="ALBUM (GENERATED BY AI)", font=("Helvetica", 8, "bold"), fg="#B3B3B3",
                          bg="#121212")
album_type_lbl.pack(anchor="w", pady=(5, 0))

album_name_label = tk.Label(album_info_frame, text="", font=("Helvetica", 24, "bold"), fg="#FFFFFF", bg="#121212")
album_name_label.pack(anchor="w")

album_meta_label = tk.Label(album_info_frame, text="", font=("Helvetica", 10), fg="#FFFFFF", bg="#121212")
album_meta_label.pack(anchor="w", pady=(2, 2))

album_tags_label = tk.Label(album_info_frame, text="", font=("Helvetica", 9, "italic"), fg="#1DB954", bg="#121212")
album_tags_label.pack(anchor="w")

tracks_title = tk.Label(results_scroll_frame, text="#   Title", font=("Helvetica", 10, "bold"), fg="#B3B3B3",
                        bg="#121212")
tracks_title.pack(anchor="w", pady=(10, 5))

tracks_inner_frame = tk.Frame(results_scroll_frame, bg="#121212")
tracks_inner_frame.pack(fill="both", expand=True)

save_btn = tk.Button(
    results_scroll_frame, text="SAVE ALBUM (JSON + PNG)", font=("Helvetica", 11, "bold"),
    bg="#1DB954", fg="#FFFFFF", activebackground="#1ed760", activeforeground="#FFFFFF",
    bd=0, pady=10, cursor="hand2"
)


root.mainloop()