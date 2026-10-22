# System Architecture & Models Blueprint

## Database Schema (Django Models)

### 1. Course Model
- `user`: ForeignKey(User, on_delete=models.CASCADE, related_name='courses')
- `title`: CharField(max_length=255)
- `description`: TextField(blank=True)
- `is_public`: BooleanField(default=False)
- `created_at`: DateTimeField(auto_now_add=True)
- `updated_at`: DateTimeField(auto_now=True)

### 2. Module Model
- `course`: ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
- `title`: CharField(max_length=255)
- `order`: PositiveIntegerField(default=0)

### 3. Lesson Model
- `module`: ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
- `title`: CharField(max_length=255)
- `lesson_type`: CharField(max_length=10, choices=[('YOUTUBE', 'YouTube Video'), ('PDF', 'PDF Document'), ('LINK', 'Web Article')])
- `youtube_url`: URLField(blank=True, null=True)
- `external_url`: URLField(blank=True, null=True)
- `pdf_file`: FileField(upload_to='lesson_pdfs/', blank=True, null=True)
- `notes`: TextField(blank=True)
- `is_completed`: BooleanField(default=False)
- `order`: PositiveIntegerField(default=0)

## URL Structure Design
- `/` -> Campus public discovery feed.
- `/dashboard/` -> User's private workspace listing their created courses.
- `/course/<int:pk>/` -> Course structure editor (Add modules/lessons).
- `/lesson/<int:pk>/` -> The split-screen learning workspace interface.
