# AI Syllabus Generator & YouTube Playlist Automation Specifications

## 1. AI Course Timeline Generator
### Workflow Engine
- Add an `ai_generate_course` view and modal form to the Dashboard.
- **Inputs:** `topic` (Text), `resources_description` (Text), and `timeline_duration` (Choice: 1 Week, 2 Weeks, 1 Month, 3 Months).
- **Backend Action:** Send a structured prompt to the AI API (Gemini/OpenAI) requesting a strict JSON response.
- **Expected JSON Schema from AI:**
  ```json
  {
    "modules": [
      {
        "title": "Module Name",
        "lessons": [
          {"title": "Lesson Name", "lesson_type": "LINK", "external_url": "Placeholder URL or Resource Hint"}
        ]
      }
    ]
  }
  ```
- **Database Entry:** The system must parse this JSON payload and automatically create rows in the `Module` and `Lesson` tables linked to the user's new Course.

## 2. YouTube Playlist Batch Importer
### Workflow Engine
- Inside the Course Builder view, add an "Import Whole YouTube Playlist" feature button.
- **Input:** A standard YouTube Playlist URL (e.g., `https://youtube.com`).
- **Backend Action:** 
  1. Extract the `list` ID parameter from the URL using a regex block.
  2. Make an internal backend GET call to the YouTube Data API v3 (`playlistItems` endpoint).
  3. Loop through the API response array items to extract the `snippet.title` and build a watch video URL: `https://youtube.com`.
- **Database Entry:** Create a *new single Module* named after the playlist title, and dynamically inject every individual video inside it as a sequential `Lesson` object type `YOUTUBE` with their respective index orders.
