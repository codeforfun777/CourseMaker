# Product Requirement Document (PRD): Custom Course Maker LMS

## 1. Project Overview
A Personal Learning Management System (LMS) designed for self-learners and university students. The platform allows users to curate scattered educational resources (YouTube videos, PDFs, articles) into structured, modular courses with built-in note-taking features. Courses can be kept private or published to a public university campus feed.

## 2. Target Audience
- University students organizing exam prep materials.
- Self-learners building custom curricula out of scattered internet resources.

## 3. Core Features (MVP)
- **User Authentication:** Sign up, log in, log out (Standard Django Auth).
- **Course Builder Dashboard:** Create, update, and delete custom Courses.
- **Modular Structure:** Each course contains multiple Modules (chapters), and each module contains multiple Lessons.
- **Multi-Media Lessons:** Lessons support 3 types: YouTube Video, PDF Upload, or External Web Link.
- **Split-Screen Study Interface:** 
  - Left panel: Embedded video player, PDF viewer, or article link.
  - Right panel: Rich-text or Markdown workspace for real-time study notes.
- **Progress Tracking:** Checkboxes to mark lessons as complete, rendering a visual progress bar on the course dashboard.
- **Campus Sharing Feed:** A toggle to make a course "Public", adding it to a global campus discovery feed where other students can view it.

## 4. Tech Stack Constraints
- **Backend Framework:** Python 3.11+ / Django 5.x
- **Frontend / Styling:** Django Templates combined with Tailwind CSS (via CDN for MVP setup).
- **Database:** SQLite (local development) / PostgreSQL ready.
