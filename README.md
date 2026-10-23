# CourseMaker LMS — Complete Development Guide

A distraction-free, modern Learning Management System (LMS) designed for self-directed students, engineers, and creators to curate structured study tracks, import entire YouTube playlists, take markdown notes alongside videos, jump across chapters, and export/import curriculum tracks.

---

## 📑 Table of Contents
1. [Tech Stack & Architecture](#tech-stack--architecture)
2. [Project File Structure](#project-file-structure)
3. [Local Development Setup](#local-development-setup)
4. [Data Models & Schema](#data-models--schema)
5. [Core Features & Utilities](#core-features--utilities)
   - [YouTube Playlist Batch Importer](#youtube-playlist-batch-importer)
   - [Plyr.js Split-Screen Player](#plyrjs-split-screen-player)
   - [JSON Course & Module Export / Import](#json-course--module-export--import)
   - [AI Syllabus Generator (Hidden UI / Intact Backend)](#ai-syllabus-generator)
6. [API & URL Routing Reference](#api--url-routing-reference)
7. [Automated Testing](#automated-testing)
8. [Free Production Deployment (Vercel + Neon)](#free-production-deployment-vercel--neon)
9. [Backup & Migration Commands](#backup--migration-commands)

---

## 1. Tech Stack & Architecture

- **Backend**: Python 3.12+, Django 6.1 (WSGI & Serverless-ready)
- **Database**:
  - Local Dev: SQLite3 (`db.sqlite3`)
  - Production: Cloud PostgreSQL via **Neon.tech** with SSL & zero connection latency
- **Frontend / Styling**:
  - Tailwind CSS CDN
  - **Catppuccin Mocha** palette (Dark/Light theme toggle with `localStorage` persistence)
  - Typography: Google Inter (body) & JetBrains Mono / Nerd Font (code & timestamps)
- **Video & Study Player**:
  - **Plyr.js 3.7.8** (16:9 responsive wrapper with native controls: CC, speeds, quality)
  - Interactive timestamp seeking via Plyr JS API
  - Auto-saving Markdown notes via AJAX
- **Static Asset Serving**: WhiteNoise 6.12 (compressed manifest caching)
- **Deployment Platform**: Vercel Serverless Functions (`@vercel/python`, `@vercel/static-build`)

---

## 2. Project File Structure

```text
crse/
├── build_files.sh              # Vercel build script (pip install, collectstatic, auto-migrate)
├── vercel.json                 # Vercel serverless routing & build configuration
├── Procfile                    # Production entrypoint (for Heroku/Render if used)
├── requirements.txt            # Frozen production Python dependencies
├── .env.example                # Template for environment variables
├── manage.py                   # Django management utility
│
├── coursemaker/                # Django project root configuration
│   ├── __init__.py
│   ├── asgi.py
│   ├── wsgi.py                 # Exports standard 'application' and Vercel 'app'
│   ├── urls.py                 # Top-level URL dispatcher
│   └── settings.py             # Configured for WhiteNoise, dj-database-url, Neon SSL
│
└── courses/                    # Core LMS Application
    ├── admin.py                # Django Admin models registration
    ├── apps.py
    ├── forms.py                # CourseForm, ModuleForm, LessonForm, SignUpForm
    ├── models.py               # Course, Module, Lesson, LessonTimestamp
    ├── urls.py                 # Application routes (namespaced 'courses:*')
    ├── views.py                # View controllers with owner-scoped permissions
    ├── tests.py                # 29 automated unit & integration test cases
    ├── utils.py                # YouTube multi-strategy playlist scraper & JSON serializer
    ├── youtube_utils.py        # Chapter extractor & timestamp line parser
    │
    └── templates/courses/      # Responsive Tailwind HTML Templates
        ├── base.html           # Master layout with Catppuccin theme & global nav
        ├── dashboard.html      # User workspace, course cards, modals (create/import)
        ├── course_detail.html  # Curriculum structure builder & module importer
        ├── lesson_view.html    # Split-screen study focus mode with Plyr.js & notes
        ├── login.html          # Authentication login page
        └── signup.html         # User registration page
```

---

## 3. Local Development Setup

### Prerequisites
- Python 3.12 or higher
- Git

### Step-by-Step Setup

1. **Clone or enter the project directory**:
   ```bash
   cd "/run/media/radwan/RadwaN/AI Project/crse"
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   Create a `.env` file in the root directory (or copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```
   Add your optional keys if desired:
   ```env
   SECRET_KEY=local-dev-secret-key-12345
   DEBUG=True
   ALLOWED_HOSTS=127.0.0.1,localhost
   YOUTUBE_API_KEY=
   AI_API_KEY=
   ```

5. **Run database migrations**:
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser (for Django Admin access)**:
   ```bash
   python manage.py createsuperuser
   ```

7. **Start the local development server**:
   ```bash
   python manage.py runserver
   ```
   Open your browser at `http://127.0.0.1:8000/`.

---

## 4. Data Models & Schema

The relational schema is defined in [`courses/models.py`](file:///run/media/radwan/RadwaN/AI%20Project/crse/courses/models.py):

```mermaid
erDiagram
    User ||--o{ Course : "owns"
    Course ||--o{ Module : "contains"
    Module ||--o{ Lesson : "contains"
    Lesson ||--o{ LessonTimestamp : "has"

    User {
        int id PK
        string username
        string password
        string email
    }

    Course {
        int id PK
        int user_id FK
        string title
        text description
        boolean is_public
        datetime created_at
        datetime updated_at
    }

    Module {
        int id PK
        int course_id FK
        string title
        int order
    }

    Lesson {
        int id PK
        int module_id FK
        string title
        string lesson_type
        string youtube_url
        string external_url
        file pdf_file
        text notes
        boolean is_completed
        int order
    }

    LessonTimestamp {
        int id PK
        int lesson_id FK
        int time_seconds
        string label
        datetime created_at
    }
```

### Key Business Logic
- **Ownership Isolation**: Every course is tied to `user_id`. Views verify `course.user == request.user`. Non-owners receive `403 Forbidden`.
- **Dynamic Progress**: `course.progress_percentage` calculates `(completed_lessons / total_lessons) * 100` dynamically across all modules.
- **YouTube Embedding**: `lesson.youtube_embed_id` uses regex patterns supporting standard watch links, `/shorts/`, `youtu.be`, and `/embed/` URLs.

---

## 5. Core Features & Utilities

### YouTube Playlist Batch Importer
Located in [`courses/utils.py`](file:///run/media/radwan/RadwaN/AI%20Project/crse/courses/utils.py#L47-L180):
- Accepts any playlist URL (including watch links with `&list=...` parameters) or raw playlist IDs (`PL...`).
- Uses multi-tier extraction:
  1. Official YouTube Data API v3 (if `YOUTUBE_API_KEY` is present).
  2. Direct Web Scraper fallback extracting both modern YouTube `lockupViewModel` and classic `playlistVideoRenderer` payloads.
  3. Seamlessly populates structured `Module` and `Lesson` records.

### Plyr.js Split-Screen Player
Located in [`courses/templates/courses/lesson_view.html`](file:///run/media/radwan/RadwaN/AI%20Project/crse/courses/templates/courses/lesson_view.html):
- Replaced standard iframes with **Plyr.js 3.7.8**.
- Maintains an exact 16:9 aspect ratio across responsive viewports.
- Integrated chapter navigator allowing instant seeking with `window.studyPlayer.currentTime = timeSeconds`.
- Markdown study notes save automatically via AJAX (`lesson_save_notes`).
- Keyboard shortcuts: `Space` (Play/Pause), `M` (Mute), `F` (Fullscreen), `N` (Next Lesson), `P` (Prev Lesson).

### JSON Course & Module Export / Import
Located in [`courses/utils.py`](file:///run/media/radwan/RadwaN/AI%20Project/crse/courses/utils.py#L465-L600) and [`courses/views.py`](file:///run/media/radwan/RadwaN/AI%20Project/crse/courses/views.py#L82-L175):
- **Course Export**: Generates a portable `<course-title>.json` file containing all nested modules, lessons, notes, and timestamps.
- **Course Import**: Upload any Course or Module JSON file via the Dashboard modal to clone or restore full courses.
- **Module Export**: Generates `<module-title>.json` for sharing individual chapters.
- **Module Import**: Upload into any course structure to append modules and lessons seamlessly.

### AI Syllabus Generator
Located in [`courses/utils.py`](file:///run/media/radwan/RadwaN/AI%20Project/crse/courses/utils.py#L320-L460) and [`courses/views.py`](file:///run/media/radwan/RadwaN/AI%20Project/crse/courses/views.py#L480-L540):
- Generates tailored multi-week curriculums from prompt topics.
- **Current State**: UI buttons and modals are commented out in [`dashboard.html`](file:///run/media/radwan/RadwaN/AI%20Project/crse/courses/templates/courses/dashboard.html). The backend remains 100% functional and can be re-enabled at any time by uncommenting the HTML modal and buttons.

---

## 6. API & URL Routing Reference

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/` | GET | Required | User's private learning dashboard (redirects unauthenticated to `/login/`) |
| `/dashboard/` | GET, POST | Required | Dashboard view and manual course creation |
| `/course/<id>/` | GET | Owner | Course structure builder & module list |
| `/course/<id>/export/` | GET | Owner | Download Course JSON backup |
| `/course/import/` | POST | Required | Upload Course JSON file to create new course |
| `/course/<id>/delete/` | POST | Owner | Delete course and all its modules/lessons |
| `/course/<course_id>/import-playlist/` | POST | Owner | Batch import YouTube playlist into a module |
| `/course/<course_id>/module/create/` | POST | Owner | Add a new module |
| `/course/<course_id>/module/import/` | POST | Owner | Upload Module JSON into this course |
| `/module/<id>/export/` | GET | Owner | Download Module JSON |
| `/module/<id>/delete/` | POST | Owner | Delete module |
| `/module/<module_id>/lesson/create/` | POST | Owner | Add lesson (YouTube, PDF, or Link) |
| `/lesson/<id>/` | GET | Owner | Split-screen study focus workspace (Plyr player + notes) |
| `/lesson/<id>/save-notes/` | POST | Owner | AJAX endpoint saving markdown notes |
| `/lesson/<id>/toggle-complete/` | POST | Owner | AJAX endpoint toggling lesson completion |
| `/lesson/<id>/timestamp/add/` | POST | Owner | Add custom timestamp bookmark |
| `/lesson/<id>/timestamp/sync/` | POST | Owner | Auto-fetch YouTuber chapters from video description |
| `/lesson/<id>/timestamp/paste/` | POST | Owner | Parse multiline copied timestamps |
| `/signup/` | GET, POST | Public | User registration |
| `/login/` | GET, POST | Public | User authentication |
| `/logout/` | POST | Required | Sign out (redirects to `/login/`) |

---

## 7. Automated Testing

All unit tests and integration tests reside in [`courses/tests.py`](file:///run/media/radwan/RadwaN/AI%20Project/crse/courses/tests.py).

To execute the test suite:
```bash
python manage.py test
```

### Test Coverage Highlights:
- **Model Tests**: Relationships, string representations, video ID extraction regex.
- **Permission Tests**: Unauthorized user redirects, non-owner course/lesson access denials (403 Forbidden).
- **Workspace Tests**: Plyr split-screen rendering, AJAX notes auto-save, completion progress calculations.
- **Automation Tests**: YouTube playlist parser, playlist permission checks.
- **Export / Import Tests**: JSON structure validation, course restore, module insertion, and owner verification.

---

## 8. Free Production Deployment (Vercel + Neon)

### Step 1: Push Code to GitHub
```bash
git branch -M main
git remote add origin https://github.com/<YOUR-USERNAME>/<YOUR-REPO>.git
git push -u origin main
```

### Step 2: Create a Free Neon PostgreSQL Database
1. Go to [Neon.tech](https://neon.tech) and create a free project.
2. Under **Connection Details**, copy your `DATABASE_URL`:
   ```text
   postgres://username:password@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

### Step 3: Deploy on Vercel
1. Log in to [Vercel](https://vercel.com) with GitHub.
2. Click **"Add New..."** &rarr; **"Project"** &rarr; Select your GitHub repository.
3. In **Environment Variables**, add:
   - `DATABASE_URL`: *(Your Neon PostgreSQL connection string)*
   - `SECRET_KEY`: *(Any random 50+ character string)*
   - `DEBUG`: `False`
4. Click **"Deploy"**.

Vercel will execute [`build_files.sh`](file:///run/media/radwan/RadwaN/AI%20Project/crse/build_files.sh), automatically run migrations on your Neon database, compile static assets with WhiteNoise, and launch your live application at `https://<your-project>.vercel.app`.

---

## 9. Backup & Migration Commands

### Export Local Database Records (JSON dump)
```bash
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission --indent 2 > local_backup.json
```

### Load Backup into Neon Database
```bash
DATABASE_URL="postgres://..." python manage.py loaddata local_backup.json
```

