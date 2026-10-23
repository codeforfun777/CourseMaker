<div align="center">

# ⚡ CourseMaker LMS

**A distraction-free, modern personal learning workspace for developers and self-directed students.**

Curate structured study tracks, import entire YouTube playlists in one click, take Markdown notes alongside video lectures, jump to chapters via interactive timestamps, and backup everything with JSON export/import.

[**🌐 Live Demo**](https://course-maker-two.vercel.app) • [**✨ Features**](#-key-features) • [**🚀 Quickstart**](#-quickstart) • [**🛠️ Tech Stack**](#-tech-stack)

<br/>

</div>

---

## 🌟 Key Features

### 📚 Personal Learning Workspace
- **Distraction-Free Dashboard**: Track your enrolled and authored courses, active tracks, and overall completion percentages.
- **Private & Scoped Accounts**: Each user has an isolated workspace with encrypted authentication. Courses are private to each user.

### 📺 1-Click YouTube Playlist Importer
- Import entire YouTube playlists instantly by pasting any playlist URL (`youtube.com/playlist?list=...` or watch links with `&list=...`).
- Automatically extracts all video titles and video IDs and creates structured curriculum modules and playable lessons.

### 🎥 Cinema Focus Player (Plyr.js)
- Responsive **16:9** media player powered by **Plyr.js**.
- Complete playback controls: **Playback speed (0.5x–2x)**, **native CC / Subtitles**, and **quality selection**.
- Keyboard shortcuts: `Space` (Play/Pause), `M` (Mute), `F` (Fullscreen), `N` (Next Lesson), `P` (Previous Lesson).

### ⏱️ Interactive Video Chapters & Timestamps
- **Auto-Sync Chapters**: One-click sync to extract official YouTuber video chapters directly from video descriptions.
- **Paste Timestamps**: Paste raw description text (e.g. `01:25 Introduction`) and parse them into interactive bookmarks.
- **Instant Seek**: Click any timestamp bookmark to seek immediately to that second in the player.

### 📝 Real-Time Split-Screen Study Notes
- Dedicated Markdown notes editor alongside the video player.
- **Auto-save via AJAX**: Notes save seamlessly in the background without refreshing or pausing the video.

### 📥 JSON Course & Module Export / Import
- **Course Backup**: Export any course to a portable `.json` file containing all modules, lessons, notes, and timestamps.
- **Module Sharing**: Export individual modules or import JSON curriculum tracks into any existing course.

### 🎨 Catppuccin Mocha Dark Theme
- Sleek dark and light theme inspired by the **Catppuccin Mocha** palette.
- Persistent theme selection saved in browser `localStorage`.
- Monospace styling with **JetBrains Mono** font for code and timestamps.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.12, Django 6.1
- **Database**:
  - Local: SQLite3
  - Production: Cloud PostgreSQL via **Neon.tech** (Serverless with SSL)
- **Frontend**: Tailwind CSS, Plyr.js 3.7.8, Inter & JetBrains Mono typography
- **Deployment**: Vercel Serverless Functions (`@vercel/python`, `@vercel/static-build`)
- **Static Assets**: WhiteNoise (Compressed Manifest Caching)

---

## 🚀 Quickstart (Local Development)

### 1. Clone the repository
```bash
git clone https://github.com/codeforfun777/CourseMaker.git
cd CourseMaker
```

### 2. Create and activate a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run migrations and start the server
```bash
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser.

---

## 🌐 Production Deployment

The project is pre-configured for free deployment on **Vercel** with a **Neon.tech** cloud PostgreSQL database:

1. Push your repository to GitHub.
2. Create a free project on [Neon.tech](https://neon.tech) and copy your `DATABASE_URL`.
3. Import the repository in [Vercel](https://vercel.com) and add the environment variables:
   - `DATABASE_URL`: *(Your Neon PostgreSQL connection string)*
   - `SECRET_KEY`: *(Any random secret string)*
   - `DEBUG`: `False`
4. Click **Deploy**. Vercel will auto-run migrations and host your website with free SSL.

---

## 📄 License
This project is open-source and available under the MIT License.
