import tkinter as tk
from tkinter import ttk
import requests
from PIL import Image, ImageTk, ImageDraw, ImageFont
from io import BytesIO
import threading
import math

API_URL = "http://localhost:5001/books"

# ─── Color Palette ───────────────────────────────────────────────
BG_PAGE       = "#F0F2F8"
BG_WHITE      = "#FFFFFF"
BG_CARD       = "#FFFFFF"
BG_HEADER     = "#FFFFFF"
BG_SEARCH     = "#F0F2F8"
BG_TAG        = "#EEF2FF"
BG_FOOTER     = "#1E1E2E"

ACCENT        = "#FF63AC"
ACCENT_DARK   = "#F089AD"
ACCENT_LIGHT  = "#EEF2FF"
TEXT_DARK     = "#1E1E2E"
TEXT_MID      = "#4A4A6A"
TEXT_MUTED    = "#9090A8"
TEXT_PRICE    = "#2A9D8F"
TEXT_TAG      = "#6C63FF"
BORDER        = "#E8E8F0"
STAR_COLOR    = "#F4A261"
HOVER_BORDER  = "#6C63FF"
SHADOW        = "#E0E0EE"

FONT_TITLE    = ("Georgia", 22, "bold")
FONT_SUB      = ("Segoe UI", 10)
FONT_SEARCH   = ("Segoe UI", 12)
FONT_SECTION  = ("Segoe UI", 14, "bold")
FONT_BOOK_T   = ("Segoe UI", 10, "bold")
FONT_AUTHOR   = ("Segoe UI", 9)
FONT_PRICE    = ("Segoe UI", 11, "bold")
FONT_TAG      = ("Segoe UI", 8)
FONT_FOOTER   = ("Segoe UI", 9)
FONT_BADGE    = ("Segoe UI", 8, "bold")
FONT_BTN      = ("Segoe UI", 9, "bold")


def make_rounded_image(img, radius=12):
    """Apply rounded corners to a PIL image."""
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), img.size], radius=radius, fill=255)
    result = Image.new("RGBA", img.size, (0, 0, 0, 0))
    result.paste(img.convert("RGBA"), mask=mask)
    return result


def make_placeholder(w=110, h=155, title="", radius=12):
    """Create a gradient-style placeholder image."""
    img = Image.new("RGB", (w, h), "#DDD8F5")
    draw = ImageDraw.Draw(img)
    # Decorative lines
    for i in range(0, h, 20):
        draw.line([(0, i), (w, i)], fill="#C8C0EE", width=1)
    # Book icon
    cx, cy = w // 2, h // 2 - 10
    draw.rectangle([cx-18, cy-22, cx+18, cy+22], fill="#B0A8E0", outline="#9088CC", width=2)
    draw.line([cx, cy-22, cx, cy+22], fill="#9088CC", width=2)
    return make_rounded_image(img, radius)


def stars_widget(parent, rating=4.2, bg=BG_CARD):
    """Return a frame with star rating display."""
    frame = tk.Frame(parent, bg=bg)
    full = int(rating)
    half = 1 if (rating - full) >= 0.5 else 0
    for i in range(5):
        if i < full:
            c = STAR_COLOR
        elif i == full and half:
            c = STAR_COLOR
        else:
            c = "#D0D0E0"
        tk.Label(frame, text="★", fg=c, bg=bg,
                 font=("Segoe UI", 9)).pack(side="left")
    tk.Label(frame, text=f"  {rating:.1f}", fg=TEXT_MUTED,
             font=("Segoe UI", 8), bg=bg).pack(side="left")
    return frame


# ─── Main App ─────────────────────────────────────────────────────
class BookApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Book Store")
        self.root.geometry("900x680")
        self.root.configure(bg=BG_PAGE)
        self.root.resizable(True, True)

        self.books = []
        self.image_cache = {}
        self.card_widgets = []
        self.current_filter = "All"

        self._build_ui()
        self._load_books()

    # ── Build UI ──────────────────────────────────────────────────
    def _build_ui(self):
        # ── Header ───────────────────────────────────────────────
        header = tk.Frame(self.root, bg=BG_HEADER, pady=14)
        header.pack(fill="x", padx=0)
        # Bottom border of header
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

        inner_h = tk.Frame(header, bg=BG_HEADER)
        inner_h.pack(fill="x", padx=28)

        left_h = tk.Frame(inner_h, bg=BG_HEADER)
        left_h.pack(side="left")

        title_row = tk.Frame(left_h, bg=BG_HEADER)
        title_row.pack(anchor="w")
        tk.Label(title_row, text="📚", font=("Segoe UI", 20),
                 bg=BG_HEADER).pack(side="left")
        tk.Label(title_row, text=" Book Store",
                 font=FONT_TITLE, fg=TEXT_DARK,
                 bg=BG_HEADER).pack(side="left")

        tk.Label(left_h, text="Discover your next favourite read",
                 font=FONT_SUB, fg=TEXT_MUTED,
                 bg=BG_HEADER).pack(anchor="w", pady=(2, 0))

        # Avatar button
        right_h = tk.Frame(inner_h, bg=BG_HEADER)
        right_h.pack(side="right")
        avatar = tk.Label(right_h, text=" ⚙ ", font=("Segoe UI", 13),
                          fg=TEXT_MID, bg=BG_HEADER, cursor="hand2")
        avatar.pack(side="right", padx=6)
        tk.Label(right_h, text="My List (0)", font=("Segoe UI", 9),
                 fg=ACCENT, bg=BG_HEADER, cursor="hand2").pack(side="right", padx=8)

        # ── Search bar ───────────────────────────────────────────
        search_wrap = tk.Frame(self.root, bg=BG_PAGE, pady=14)
        search_wrap.pack(fill="x", padx=28)

        search_frame = tk.Frame(search_wrap, bg=BG_SEARCH,
                                highlightbackground=BORDER,
                                highlightthickness=1)
        search_frame.pack(fill="x")

        tk.Label(search_frame, text="🔍", font=("Segoe UI", 12),
                 bg=BG_SEARCH, fg=TEXT_MUTED).pack(side="left", padx=(12, 4), pady=8)

        self.search_var = tk.StringVar()
        entry = tk.Entry(search_frame, textvariable=self.search_var,
                         font=FONT_SEARCH, relief="flat", bg=BG_SEARCH,
                         fg=TEXT_DARK, insertbackground=ACCENT,
                         bd=0)
        entry.pack(side="left", fill="x", expand=True, ipady=9, pady=4)
        entry.insert(0, "Search by title or author...")
        entry.config(fg=TEXT_MUTED)
        entry.bind("<FocusIn>",  self._on_search_focus)
        entry.bind("<FocusOut>", self._on_search_blur)
        entry.bind("<KeyRelease>", self._search_books)

        self.search_entry = entry

        # Clear button
        self.clear_btn = tk.Label(search_frame, text="✕", font=("Segoe UI", 10),
                                   bg=BG_SEARCH, fg=TEXT_MUTED, cursor="hand2",
                                   padx=10)
        self.clear_btn.pack(side="right")
        self.clear_btn.bind("<Button-1>", self._clear_search)

        # ── Filter chips ─────────────────────────────────────────
        filter_wrap = tk.Frame(self.root, bg=BG_PAGE, pady=4)
        filter_wrap.pack(fill="x", padx=28)

        self.filters = ["All", "Fiction", "Non-Fiction", "Sci-Fi",
                        "Mystery", "Romance", "Biography"]
        self.filter_btns = {}
        for tag in self.filters:
            btn = tk.Label(filter_wrap, text=tag, font=FONT_TAG,
                           cursor="hand2", padx=12, pady=5,
                           relief="flat")
            btn.pack(side="left", padx=(0, 6))
            btn.bind("<Button-1>", lambda e, t=tag: self._set_filter(t))
            self.filter_btns[tag] = btn
        self._set_filter("All")

        # ── Section header ───────────────────────────────────────
        sec = tk.Frame(self.root, bg=BG_PAGE, pady=6)
        sec.pack(fill="x", padx=28)

        self.section_label = tk.Label(sec, text="Featured for you",
                                       font=FONT_SECTION, fg=TEXT_DARK,
                                       bg=BG_PAGE)
        self.section_label.pack(side="left")

        tk.Label(sec, text="See all →", font=("Segoe UI", 9),
                 fg=ACCENT, bg=BG_PAGE, cursor="hand2").pack(side="right")

        self.count_label = tk.Label(sec, text="", font=("Segoe UI", 9),
                                     fg=TEXT_MUTED, bg=BG_PAGE)
        self.count_label.pack(side="right", padx=12)

        # ── Scrollable book grid ──────────────────────────────────
        grid_wrap = tk.Frame(self.root, bg=BG_PAGE)
        grid_wrap.pack(fill="both", expand=True, padx=10)

        self.canvas = tk.Canvas(grid_wrap, bg=BG_PAGE, highlightthickness=0)
        self.book_frame = tk.Frame(self.canvas, bg=BG_PAGE)

        vbar = ttk.Scrollbar(grid_wrap, orient="vertical",
                             command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vbar.set)

        vbar.pack(side="right", fill="y")
        self.canvas.pack(fill="both", expand=True)

        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.book_frame, anchor="nw")

        self.book_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.book_frame.bind("<MouseWheel>", self._on_mousewheel)

        # ── Footer ───────────────────────────────────────────────
        footer = tk.Frame(self.root, bg=BG_FOOTER, pady=10)
        footer.pack(fill="x", side="bottom")

        foot_inner = tk.Frame(footer, bg=BG_FOOTER)
        foot_inner.pack()

        tk.Label(foot_inner, text="📚 BOOKSTORE",
                 font=("Segoe UI", 10, "bold"),
                 fg="#FFFFFF", bg=BG_FOOTER).pack()
        tk.Label(foot_inner, text="Made with ♥ for Book Lovers",
                 font=FONT_FOOTER, fg="#9090A8", bg=BG_FOOTER).pack()

        link_row = tk.Frame(foot_inner, bg=BG_FOOTER)
        link_row.pack(pady=(4, 0))
        for lbl in ["Privacy", "·", "Terms", "·", "Support"]:
            c = "#9090A8" if lbl == "·" else "#B0B8D8"
            tk.Label(link_row, text=lbl, font=FONT_FOOTER,
                     fg=c, bg=BG_FOOTER,
                     cursor="hand2" if lbl != "·" else "").pack(side="left", padx=2)

    # ── Events ────────────────────────────────────────────────────
    def _on_frame_configure(self, e):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, e):
        self.canvas.itemconfig(self.canvas_window, width=e.width)
        if self.books:
            self._display_books(self._current_books())

    def _on_mousewheel(self, e):
        self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    def _on_search_focus(self, e):
        if self.search_entry.get() == "Search by title or author...":
            self.search_entry.delete(0, "end")
            self.search_entry.config(fg=TEXT_DARK)

    def _on_search_blur(self, e):
        if not self.search_entry.get():
            self.search_entry.insert(0, "Search by title or author...")
            self.search_entry.config(fg=TEXT_MUTED)

    def _clear_search(self, e=None):
        self.search_entry.delete(0, "end")
        self.search_entry.insert(0, "Search by title or author...")
        self.search_entry.config(fg=TEXT_MUTED)
        self._display_books(self.books)

    def _set_filter(self, tag):
        self.current_filter = tag
        for t, btn in self.filter_btns.items():
            if t == tag:
                btn.config(bg=ACCENT, fg="white",
                           highlightbackground=ACCENT,
                           highlightthickness=1)
            else:
                btn.config(bg=BG_TAG, fg=TEXT_TAG,
                           highlightbackground=BORDER,
                           highlightthickness=1)
        if self.books:
            self._display_books(self._current_books())

    # ── Data ──────────────────────────────────────────────────────
    def _load_books(self):
        def fetch():
            try:
                res = requests.get(API_URL, timeout=5)
                data = res.json()
                self.books = data.get("books", [])
            except Exception:
                self.books = self._demo_books()
            self.root.after(0, lambda: self._display_books(self.books))
        threading.Thread(target=fetch, daemon=True).start()

    def _demo_books(self):
        genres = ["Fiction", "Sci-Fi", "Mystery", "Romance",
                  "Non-Fiction", "Biography"]
        books = []
        titles = [
            ("The Midnight Library", "Matt Haig",       18.99, 4.6),
            ("Dune",                 "Frank Herbert",    14.99, 4.8),
            ("Gone Girl",            "Gillian Flynn",    12.99, 4.4),
            ("Educated",             "Tara Westover",    15.99, 4.7),
            ("The Alchemist",        "Paulo Coelho",     11.99, 4.5),
            ("Sapiens",              "Yuval Noah Harari",17.99, 4.6),
            ("Project Hail Mary",    "Andy Weir",        16.99, 4.9),
            ("The Vanishing Half",   "Brit Bennett",     13.99, 4.5),
            ("Atomic Habits",        "James Clear",      19.99, 4.8),
            ("The Name of the Wind", "Patrick Rothfuss", 14.49, 4.7),
            ("Normal People",        "Sally Rooney",     12.49, 4.3),
            ("Thinking Fast & Slow", "Daniel Kahneman",  20.99, 4.6),
        ]
        colors = ["#D8B4FE","#93C5FD","#6EE7B7","#FCA5A5",
                  "#FCD34D","#F9A8D4","#A5B4FC","#6EE7B7",
                  "#FDE68A","#BAE6FD","#DDD6FE","#BBF7D0"]
        for i, (title, author, price, rating) in enumerate(titles):
            books.append({
                "id": i+1,
                "title": title,
                "author": author,
                "price": price,
                "rating": rating,
                "genre": genres[i % len(genres)],
                "image_url": None,
                "_color": colors[i % len(colors)],
            })
        return books

    def _current_books(self):
        kw = self.search_var.get().lower()
        if kw == "search by title or author...":
            kw = ""
        result = self.books
        if self.current_filter != "All":
            result = [b for b in result
                      if b.get("genre","").lower() == self.current_filter.lower()]
        if kw:
            result = [b for b in result
                      if kw in b["title"].lower()
                      or kw in b.get("author","").lower()]
        return result

    def _search_books(self, e=None):
        self._display_books(self._current_books())

    # ── Display ───────────────────────────────────────────────────
    def _display_books(self, books):
        for w in self.book_frame.winfo_children():
            w.destroy()
        self.card_widgets.clear()

        self.count_label.config(
            text=f"{len(books)} book{'s' if len(books)!=1 else ''}")

        if not books:
            self._show_empty()
            return

        canvas_w = self.canvas.winfo_width() or 860
        card_w   = 160
        gap      = 14
        pad      = 16
        cols     = max(1, (canvas_w - 2*pad + gap) // (card_w + gap))

        for i, book in enumerate(books):
            row = i // cols
            col = i % cols
            card = self._make_card(self.book_frame, book)
            card.grid(row=row, column=col, padx=gap//2, pady=gap//2,
                      sticky="n")

    def _show_empty(self):
        wrap = tk.Frame(self.book_frame, bg=BG_PAGE)
        wrap.pack(expand=True, pady=60)
        tk.Label(wrap, text="🔍", font=("Segoe UI", 36),
                 bg=BG_PAGE, fg=TEXT_MUTED).pack()
        kw = self.search_var.get()
        if kw and kw != "Search by title or author...":
            msg = f'No books found matching "{kw}"'
        else:
            msg = "No books in this category"
        tk.Label(wrap, text=msg, font=("Segoe UI", 13),
                 fg=TEXT_MUTED, bg=BG_PAGE).pack(pady=8)

    def _make_card(self, parent, book):
        card = tk.Frame(parent, bg=BG_CARD, width=160,
                        highlightbackground=BORDER,
                        highlightthickness=1,
                        cursor="hand2")
        card.pack_propagate(False)
        card.config(height=290)

        # Hover effect
        def on_enter(e):
            card.config(highlightbackground=ACCENT,
                        highlightthickness=1)
        def on_leave(e):
            card.config(highlightbackground=BORDER,
                        highlightthickness=1)

        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

        # Image area
        img_frame = tk.Frame(card, bg=book.get("_color","#DDD8F5"),
                             height=160, width=160)
        img_frame.pack(fill="x")
        img_frame.pack_propagate(False)

        img_label = tk.Label(img_frame,
                             bg=book.get("_color","#DDD8F5"))
        img_label.pack(expand=True)

        # Genre badge
        genre = book.get("genre","")
        if genre:
            badge = tk.Label(img_frame, text=genre.upper(),
                             font=FONT_BADGE, fg="white",
                             bg=ACCENT, padx=6, pady=2)
            badge.place(x=8, y=8)

        # Load image asynchronously
        url = book.get("image_url")
        if url:
            self._async_load_image(url, img_label,
                                   book.get("_color","#DDD8F5"))
        else:
            ph = make_placeholder(160, 160,
                                  book["title"],
                                  book.get("_color","#DDD8F5"))
            photo = ImageTk.PhotoImage(ph)
            img_label.config(image=photo)
            img_label.image = photo

        # Info area
        info = tk.Frame(card, bg=BG_CARD, padx=10)
        info.pack(fill="both", expand=True, pady=(6,0))

        # Stars
        stars_widget(info, book.get("rating", 4.0), BG_CARD).pack(anchor="w")

        tk.Label(info, text=book["title"],
                 font=FONT_BOOK_T, fg=TEXT_DARK,
                 wraplength=138, justify="left",
                 bg=BG_CARD).pack(anchor="w", pady=(3,1))

        tk.Label(info, text=book.get("author",""),
                 font=FONT_AUTHOR, fg=TEXT_MUTED,
                 wraplength=138, justify="left",
                 bg=BG_CARD).pack(anchor="w")

        # Price + Add button
        bottom = tk.Frame(info, bg=BG_CARD)
        bottom.pack(fill="x", pady=(6,8))

        price_val = book.get("price", 0)
        tk.Label(bottom, text=f"${price_val:.2f}",
                 font=FONT_PRICE, fg=TEXT_PRICE,
                 bg=BG_CARD).pack(side="left", anchor="s")

        add_btn = tk.Label(bottom, text="+ Add",
                           font=FONT_BTN,
                           fg="white", bg=ACCENT,
                           padx=8, pady=3,
                           cursor="hand2")
        add_btn.pack(side="right")
        add_btn.bind("<Enter>",
                     lambda e: add_btn.config(bg=ACCENT_DARK))
        add_btn.bind("<Leave>",
                     lambda e: add_btn.config(bg=ACCENT))

        self.card_widgets.append(card)
        return card

    def _async_load_image(self, url, label, bg_color):
        def fetch():
            try:
                if url in self.image_cache:
                    photo = self.image_cache[url]
                else:
                    data = requests.get(url, timeout=6).content
                    img  = Image.open(BytesIO(data)).resize((160, 160))
                    img  = make_rounded_image(img, radius=0)
                    photo = ImageTk.PhotoImage(img)
                    self.image_cache[url] = photo
                self.root.after(0, lambda: (
                    label.config(image=photo, bg=bg_color),
                    setattr(label, "image", photo)
                ))
            except Exception:
                pass
        threading.Thread(target=fetch, daemon=True).start()


# ─── Run ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("Vertical.TScrollbar",
                    background="#D0D0E0",
                    troughcolor=BG_PAGE,
                    bordercolor=BG_PAGE,
                    arrowcolor=TEXT_MUTED,
                    width=8)
    app = BookApp(root)
    root.mainloop()