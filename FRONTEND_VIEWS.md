# Frontend Views & UI Specifications

## 1. Global Styling & UI Theme
- **Framework:** Tailwind CSS (Load via standard script CDN tag in the base template layout).
- **Theme Aesthetics:** Clean, modern "SaaS-style" application. Slate dark backgrounds or crisp slate white views with deep indigo accents (`bg-indigo-600`, `text-slate-900`).

## 2. Page & Template Layouts to Generate

### A. Base Layout (`base.html`)
- Persistent structural wrapper.
- Contains a global navigation top bar with:
  - Application Branding ("EduCraft" or "CourseMaker").
  - Links to: `Campus Feed`, `My Dashboard`.
  - Simple conditional display: Show logged-in username & logout button, or a login button.

### B. Student Dashboard (`dashboard.html`)
- Displays a grid layout showing the user's custom courses.
- Each course is styled as a card displaying: Title, description snapshot, a visual horizontal progress bar, and a badge denoting if it's "Private" or "Public Campus Shared".
- Features a prominent Call-to-Action button: `+ Create New Course` opening a simple modal form.

### C. The Split-Screen Learning Engine (`lesson_view.html`)
This is the core workspace page. It divides the desktop browser window into a clean split-pane:
- **Left Panel (Width: 60%): Study Resource**
  - Read `lesson_type` from context.
  - If `YOUTUBE`: Strip the raw watch link and render an optimized HTML `<iframe>` video container (`src="https://youtube.com<VIDEO_ID>"`).
  - If `PDF`: Render an iframe embedding the PDF file directly, or show a structured download panel if file storage is local.
  - If `LINK`: Render a clean, safe external text redirection link styled as a button layout.
- **Right Panel (Width: 40%): Study Space**
  - A clean, focus-mode workspace displaying a text area bound to the `notes` model field.
  - Includes a quick interactive AJAX or standard HTML form submit button saying `💾 Save Study Notes` to save content real-time without refreshing or breaking the video context.
  - Features an intuitive "Lesson Complete" checkbox to update progress state instantly.
