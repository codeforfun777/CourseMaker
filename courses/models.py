import re
from django.conf import settings
from django.db import models


class Course(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='courses',
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def total_lessons_count(self):
        return Lesson.objects.filter(module__course=self).count()

    @property
    def completed_lessons_count(self):
        return Lesson.objects.filter(module__course=self, is_completed=True).count()

    @property
    def progress_percentage(self):
        total = self.total_lessons_count
        if total == 0:
            return 0
        return int((self.completed_lessons_count / total) * 100)

    def get_first_lesson(self):
        """Returns the first lesson of the course, if any exists."""
        first_module = self.modules.first()
        if first_module:
            return first_module.lessons.first()
        return None


class Module(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='modules',
    )
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    @property
    def total_lessons_count(self):
        return self.lessons.count()

    @property
    def completed_lessons_count(self):
        return self.lessons.filter(is_completed=True).count()


class Lesson(models.Model):
    class LessonType(models.TextChoices):
        YOUTUBE = 'YOUTUBE', 'YouTube Video'
        DRIVE = 'DRIVE', 'Google Drive Document / PDF'
        PDF = 'PDF', 'PDF Document (Legacy)'
        LINK = 'LINK', 'Web Article'

    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name='lessons',
    )
    title = models.CharField(max_length=255)
    lesson_type = models.CharField(
        max_length=10,
        choices=LessonType.choices,
        default=LessonType.YOUTUBE,
    )
    youtube_url = models.URLField(blank=True, null=True)
    google_drive_url = models.URLField(max_length=500, blank=True, null=True)
    external_url = models.URLField(blank=True, null=True)
    pdf_file = models.FileField(upload_to='lesson_pdfs/', blank=True, null=True)
    notes = models.TextField(blank=True)
    is_completed = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.module.title} - {self.title}"

    @property
    def youtube_embed_id(self):
        """Extracts standard 11-char YouTube video ID if youtube_url is present."""
        if not self.youtube_url:
            return None
        # Match standard youtube watch, shorts, and youtu.be links
        patterns = [
            r'(?:v=|\/vi\/|youtu\.be\/|\/embed\/|\/shorts\/|\/v\/|^)([0-9A-Za-z_-]{11})(?:[&\/\?#]|$)',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.youtube_url)
            if match:
                return match.group(1)
        return None

    @property
    def youtube_embed_url(self):
        """Returns the embeddable YouTube URL."""
        video_id = self.youtube_embed_id
        if video_id:
            return f"https://www.youtube.com/embed/{video_id}"
        return None

    @property
    def google_drive_embed_url(self):
        """Converts Google Drive or Docs/Sheets/Slides link into an embeddable preview URL."""
        if not self.google_drive_url:
            return None
        url = self.google_drive_url.strip()

        # Google Docs / Sheets / Presentations
        docs_match = re.search(r'docs\.google\.com/(document|presentation|spreadsheets)/d/([a-zA-Z0-9_-]+)', url)
        if docs_match:
            doc_type = docs_match.group(1)
            doc_id = docs_match.group(2)
            return f"https://docs.google.com/{doc_type}/d/{doc_id}/preview"

        # Drive file URL: /file/d/<ID>
        file_match = re.search(r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)', url)
        if file_match:
            file_id = file_match.group(1)
            return f"https://drive.google.com/file/d/{file_id}/preview"

        # Drive open?id=<ID> or uc?id=<ID>
        id_match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
        if id_match and 'google.com' in url:
            file_id = id_match.group(1)
            return f"https://drive.google.com/file/d/{file_id}/preview"

        if 'preview' in url:
            return url

        return url

    def get_next_lesson(self):
        """Returns the next lesson within the course."""
        next_in_module = self.module.lessons.filter(order__gt=self.order).first()
        if next_in_module:
            return next_in_module
        next_module = self.module.course.modules.filter(order__gt=self.module.order).first()
        if next_module:
            return next_module.lessons.first()
        return None

    def get_previous_lesson(self):
        """Returns the previous lesson within the course."""
        prev_in_module = self.module.lessons.filter(order__lt=self.order).last()
        if prev_in_module:
            return prev_in_module
        prev_module = self.module.course.modules.filter(order__lt=self.module.order).last()
        if prev_module:
            return prev_module.lessons.last()
        return None


class LessonTimestamp(models.Model):
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='timestamps',
    )
    time_seconds = models.PositiveIntegerField(help_text="Timestamp in seconds")
    label = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['time_seconds', 'id']

    def __str__(self):
        return f"{self.formatted_time} - {self.label}"

    @property
    def formatted_time(self):
        hours = self.time_seconds // 3600
        minutes = (self.time_seconds % 3600) // 60
        seconds = self.time_seconds % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    @classmethod
    def parse_time_string(cls, time_str):
        """Parses MM:SS, H:MM:SS, or raw seconds into integer seconds."""
        time_str = str(time_str).strip()
        parts = time_str.split(':')
        try:
            if len(parts) == 1:
                return int(parts[0])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except (ValueError, TypeError):
            return 0
        return 0
