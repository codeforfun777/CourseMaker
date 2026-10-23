import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import Course, Module, Lesson

User = get_user_model()


class CourseModelsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='teststudent', password='password123')
        self.course = Course.objects.create(
            user=self.user,
            title='CS101: Introduction to Computer Science',
            description='A beginner friendly course.',
            is_public=True
        )
        self.module1 = Module.objects.create(
            course=self.course,
            title='Module 1: Algorithms',
            order=1
        )
        self.lesson1 = Lesson.objects.create(
            module=self.module1,
            title='What is an Algorithm?',
            lesson_type=Lesson.LessonType.YOUTUBE,
            youtube_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            order=1,
            is_completed=True
        )
        self.lesson2 = Lesson.objects.create(
            module=self.module1,
            title='Sorting Cheatsheet',
            lesson_type=Lesson.LessonType.PDF,
            order=2,
            is_completed=False
        )

    def test_relationships_and_counts(self):
        self.assertEqual(self.user.courses.count(), 1)
        self.assertEqual(self.course.modules.count(), 1)
        self.assertEqual(self.module1.lessons.count(), 2)
        self.assertEqual(self.course.total_lessons_count, 2)
        self.assertEqual(self.course.completed_lessons_count, 1)
        self.assertEqual(self.course.progress_percentage, 50)

    def test_youtube_embed_id(self):
        self.assertEqual(self.lesson1.youtube_embed_id, 'dQw4w9WgXcQ')
        self.assertEqual(self.lesson1.youtube_embed_url, 'https://www.youtube.com/embed/dQw4w9WgXcQ')
        self.assertIsNone(self.lesson2.youtube_embed_id)

    def test_youtube_various_url_formats(self):
        variations = [
            ('https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s', 'dQw4w9WgXcQ'),
            ('https://youtu.be/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://www.youtube.com/embed/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://www.youtube.com/shorts/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://www.youtube.com/watch?v=Ro_MScTDfU4', 'Ro_MScTDfU4'),
        ]
        for url, expected_id in variations:
            lesson = Lesson(youtube_url=url)
            self.assertEqual(lesson.youtube_embed_id, expected_id, f"Failed for {url}")

    def test_google_drive_embed_url(self):
        variations = [
            (
                'https://drive.google.com/file/d/1A2B3C4D5E6F/view?usp=sharing',
                'https://drive.google.com/file/d/1A2B3C4D5E6F/preview'
            ),
            (
                'https://drive.google.com/open?id=1A2B3C4D5E6F',
                'https://drive.google.com/file/d/1A2B3C4D5E6F/preview'
            ),
            (
                'https://docs.google.com/document/d/1A2B3C4D5E6F/edit?usp=sharing',
                'https://docs.google.com/document/d/1A2B3C4D5E6F/preview'
            ),
            (
                'https://docs.google.com/presentation/d/1A2B3C4D5E6F/edit',
                'https://docs.google.com/presentation/d/1A2B3C4D5E6F/preview'
            ),
            (
                'https://docs.google.com/spreadsheets/d/1A2B3C4D5E6F/edit#gid=0',
                'https://docs.google.com/spreadsheets/d/1A2B3C4D5E6F/preview'
            ),
        ]
        for url, expected_embed in variations:
            lesson = Lesson(google_drive_url=url)
            self.assertEqual(lesson.google_drive_embed_url, expected_embed, f"Failed for {url}")

    def test_str_representations(self):
        self.assertEqual(str(self.course), 'CS101: Introduction to Computer Science')
        self.assertEqual(str(self.module1), 'CS101: Introduction to Computer Science - Module 1: Algorithms')
        self.assertEqual(str(self.lesson1), 'Module 1: Algorithms - What is an Algorithm?')


class CourseViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='alice', password='password123')
        self.other_user = User.objects.create_user(username='bob', password='password123')

        self.public_course = Course.objects.create(
            user=self.user,
            title='Public Python Course',
            description='Learn Python step by step.',
            is_public=True
        )
        self.private_course = Course.objects.create(
            user=self.other_user,
            title='Bob Secret Course',
            description='Private research notes.',
            is_public=False
        )

        self.module = Module.objects.create(
            course=self.public_course,
            title='Python Basics',
            order=1
        )
        self.lesson = Lesson.objects.create(
            module=self.module,
            title='Hello World in Python',
            lesson_type=Lesson.LessonType.YOUTUBE,
            youtube_url='https://www.youtube.com/watch?v=kqtD5dpn9C8',
            notes='Initial notes here',
            order=1
        )

    def test_campus_feed_view(self):
        response = self.client.get(reverse('courses:campus_feed'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('courses:dashboard'), response.url)

    def test_dashboard_redirects_unauthenticated(self):
        response = self.client.get(reverse('courses:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_authenticated(self):
        self.client.login(username='alice', password='password123')
        response = self.client.get(reverse('courses:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Python Course')

    def test_course_create_via_dashboard(self):
        self.client.login(username='alice', password='password123')
        response = self.client.post(reverse('courses:dashboard'), {
            'title': 'New Django Mastery',
            'description': 'Master Django fast',
        })
        self.assertEqual(response.status_code, 302)
        new_course = Course.objects.get(title='New Django Mastery')
        self.assertEqual(new_course.user, self.user)

    def test_course_detail_unauthenticated_redirects(self):
        response = self.client.get(reverse('courses:course_detail', args=[self.public_course.pk]))
        self.assertEqual(response.status_code, 302)

    def test_course_detail_owner_access(self):
        self.client.login(username='alice', password='password123')
        response = self.client.get(reverse('courses:course_detail', args=[self.public_course.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Python Basics')

    def test_course_detail_private_forbidden_for_other(self):
        self.client.login(username='alice', password='password123')
        response = self.client.get(reverse('courses:course_detail', args=[self.private_course.pk]))
        self.assertEqual(response.status_code, 403)

    def test_lesson_view_split_screen(self):
        self.client.login(username='alice', password='password123')
        response = self.client.get(reverse('courses:lesson_view', args=[self.lesson.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hello World in Python')
        self.assertContains(response, 'https://www.youtube.com/embed/kqtD5dpn9C8')
        self.assertContains(response, 'Save Study Notes')

    def test_lesson_create_google_drive_and_view(self):
        self.client.login(username='alice', password='password123')
        create_url = reverse('courses:lesson_create', args=[self.module.pk])
        response = self.client.post(create_url, {
            'title': 'Operating Systems Lecture Notes',
            'lesson_type': Lesson.LessonType.DRIVE,
            'google_drive_url': 'https://drive.google.com/file/d/1A2B3C4D5E6F/view?usp=sharing',
            'notes': 'Read chapter 3 before next lecture',
            'order': 2
        })
        self.assertEqual(response.status_code, 302)
        drive_lesson = Lesson.objects.filter(title='Operating Systems Lecture Notes').first()
        self.assertIsNotNone(drive_lesson)
        self.assertEqual(drive_lesson.lesson_type, Lesson.LessonType.DRIVE)
        self.assertEqual(drive_lesson.google_drive_embed_url, 'https://drive.google.com/file/d/1A2B3C4D5E6F/preview')

        # View in study mode
        view_url = reverse('courses:lesson_view', args=[drive_lesson.pk])
        view_response = self.client.get(view_url)
        self.assertEqual(view_response.status_code, 200)
        self.assertContains(view_response, 'Operating Systems Lecture Notes')
        self.assertContains(view_response, 'https://drive.google.com/file/d/1A2B3C4D5E6F/preview')
        self.assertContains(view_response, 'Open in Drive')

    def test_lesson_save_notes_ajax(self):
        self.client.login(username='alice', password='password123')
        url = reverse('courses:lesson_save_notes', args=[self.lesson.pk])
        payload = json.dumps({'notes': 'Updated study notes via real-time editor!'})
        response = self.client.post(
            url,
            data=payload,
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.notes, 'Updated study notes via real-time editor!')

    def test_lesson_toggle_complete_ajax(self):
        self.client.login(username='alice', password='password123')
        self.assertFalse(self.lesson.is_completed)
        url = reverse('courses:lesson_toggle_complete', args=[self.lesson.pk])
        response = self.client.post(
            url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['is_completed'])
        self.lesson.refresh_from_db()
        self.assertTrue(self.lesson.is_completed)

    def test_lesson_add_timestamp_ajax(self):
        self.client.login(username='alice', password='password123')
        url = reverse('courses:lesson_add_timestamp', args=[self.lesson.pk])
        payload = json.dumps({'time': '02:15', 'label': 'Variables & Data Types'})
        response = self.client.post(
            url,
            data=payload,
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['formatted_time'], '02:15')
        self.assertEqual(data['time_seconds'], 135)
        self.assertEqual(data['label'], 'Variables & Data Types')

    def test_lesson_delete_timestamp_ajax(self):
        from .models import LessonTimestamp
        self.client.login(username='alice', password='password123')
        ts = LessonTimestamp.objects.create(
            lesson=self.lesson,
            time_seconds=90,
            label='Introduction'
        )
        url = reverse('courses:lesson_delete_timestamp', args=[ts.pk])
        response = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(LessonTimestamp.objects.filter(pk=ts.pk).exists())

    def test_parse_timestamp_lines(self):
        from .youtube_utils import parse_timestamp_lines
        text = """
        0:00 Intro
        01:39 Variables
        02:28 - Data Types
        1:05:20 Conclusion
        """
        results = parse_timestamp_lines(text)
        self.assertEqual(len(results), 4)
        self.assertEqual(results[0], {'time_seconds': 0, 'label': 'Intro'})
        self.assertEqual(results[1], {'time_seconds': 99, 'label': 'Variables'})
        self.assertEqual(results[2], {'time_seconds': 148, 'label': 'Data Types'})
        self.assertEqual(results[3], {'time_seconds': 3920, 'label': 'Conclusion'})

    def test_lesson_paste_timestamps_ajax(self):
        self.client.login(username='alice', password='password123')
        url = reverse('courses:lesson_paste_timestamps', args=[self.lesson.pk])
        payload = json.dumps({'text': '00:00 Intro\n01:39 Variables'})
        response = self.client.post(
            url,
            data=payload,
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertGreaterEqual(len(data['timestamps']), 2)

    def test_generate_ai_syllabus_view(self):
        self.client.login(username='alice', password='password123')
        url = reverse('courses:generate_ai_syllabus')
        response = self.client.post(url, {
            'topic': 'Machine Learning Fundamentals',
            'timeline_duration': '2 Weeks',
            'resources_description': 'Supervised and Unsupervised Learning'
        })
        self.assertEqual(response.status_code, 302)
        generated_course = Course.objects.filter(user=self.user, title__icontains='Machine Learning').first()
        self.assertIsNotNone(generated_course)
        self.assertGreaterEqual(generated_course.modules.count(), 1)
        first_module = generated_course.modules.first()
        self.assertGreaterEqual(first_module.lessons.count(), 1)

    def test_import_youtube_playlist_view(self):
        self.client.login(username='alice', password='password123')
        url = reverse('courses:import_youtube_playlist', args=[self.public_course.pk])
        response = self.client.post(url, {
            'playlist_url': 'PL4cUxeGkcC9gC88BEo9Px3Mt6QkhNYU1p',
            'module_title': 'Custom React Playlist'
        })
        self.assertEqual(response.status_code, 302)
        imported_module = self.public_course.modules.filter(title='Custom React Playlist').first()
        self.assertIsNotNone(imported_module)
        self.assertGreaterEqual(imported_module.lessons.count(), 1)
        first_lesson = imported_module.lessons.first()
        self.assertEqual(first_lesson.lesson_type, Lesson.LessonType.YOUTUBE)
        self.assertTrue(first_lesson.youtube_url.startswith('https://www.youtube.com/watch?v='))

    def test_import_youtube_playlist_permission(self):
        # Bob should not be able to import playlist into Alice's course
        self.client.login(username='bob', password='password123')
        url = reverse('courses:import_youtube_playlist', args=[self.public_course.pk])
        response = self.client.post(url, {
            'playlist_url': 'PL4cUxeGkcC9gC88BEo9Px3Mt6QkhNYU1p'
        })
        self.assertEqual(response.status_code, 403)

    def test_course_export_view(self):
        self.client.login(username='alice', password='password123')
        url = reverse('courses:course_export', args=[self.public_course.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json; charset=utf-8')
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['title'], 'Public Python Course')
        self.assertEqual(data['export_type'], 'course')
        self.assertEqual(len(data['modules']), 1)
        self.assertEqual(data['modules'][0]['title'], 'Python Basics')
        self.assertEqual(len(data['modules'][0]['lessons']), 1)
        self.assertEqual(data['modules'][0]['lessons'][0]['title'], 'Hello World in Python')

    def test_course_export_forbidden_for_non_owner(self):
        self.client.login(username='bob', password='password123')
        url = reverse('courses:course_export', args=[self.public_course.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_course_import_view(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.login(username='alice', password='password123')
        payload = {
            "version": "1.0",
            "export_type": "course",
            "title": "Imported Go Track",
            "description": "Learn Go fast",
            "modules": [
                {
                    "title": "Go Fundamentals",
                    "order": 1,
                    "lessons": [
                        {
                            "title": "Tour of Go 1",
                            "lesson_type": "YOUTUBE",
                            "youtube_url": "https://www.youtube.com/watch?v=YS4e4q9oBaU",
                            "order": 1,
                            "timestamps": [
                                {"time_seconds": 30, "label": "Setup"}
                            ]
                        }
                    ]
                }
            ]
        }
        json_file = SimpleUploadedFile(
            "go_course.json",
            json.dumps(payload).encode('utf-8'),
            content_type="application/json"
        )
        url = reverse('courses:course_import')
        response = self.client.post(url, {'course_file': json_file})
        self.assertEqual(response.status_code, 302)
        imported_course = Course.objects.filter(user=self.user, title="Imported Go Track").first()
        self.assertIsNotNone(imported_course)
        self.assertEqual(imported_course.modules.count(), 1)
        first_mod = imported_course.modules.first()
        self.assertEqual(first_mod.title, "Go Fundamentals")
        self.assertEqual(first_mod.lessons.count(), 1)
        first_les = first_mod.lessons.first()
        self.assertEqual(first_les.title, "Tour of Go 1")
        self.assertEqual(first_les.timestamps.count(), 1)
        self.assertEqual(first_les.timestamps.first().label, "Setup")

    def test_module_export_view(self):
        self.client.login(username='alice', password='password123')
        url = reverse('courses:module_export', args=[self.module.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json; charset=utf-8')
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['title'], 'Python Basics')
        self.assertEqual(data['export_type'], 'module')
        self.assertEqual(len(data['lessons']), 1)

    def test_module_import_view(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.login(username='alice', password='password123')
        payload = {
            "version": "1.0",
            "export_type": "module",
            "title": "Advanced Python Decorators",
            "order": 2,
            "lessons": [
                {
                    "title": "Understanding Closures",
                    "lesson_type": "LINK",
                    "external_url": "https://example.com/closures",
                    "order": 1
                }
            ]
        }
        json_file = SimpleUploadedFile(
            "decorators.json",
            json.dumps(payload).encode('utf-8'),
            content_type="application/json"
        )
        url = reverse('courses:module_import', args=[self.public_course.pk])
        response = self.client.post(url, {'module_file': json_file})
        self.assertEqual(response.status_code, 302)
        new_mod = self.public_course.modules.filter(title="Advanced Python Decorators").first()
        self.assertIsNotNone(new_mod)
        self.assertEqual(new_mod.lessons.count(), 1)
        self.assertEqual(new_mod.lessons.first().title, "Understanding Closures")


class CourseAutomationUtilsTestCase(TestCase):
    def test_extract_youtube_playlist_id(self):
        from .utils import extract_youtube_playlist_id
        valid_cases = [
            ('PL4cUxeGkcC9gC88BEo9Px3Mt6QkhNYU1p', 'PL4cUxeGkcC9gC88BEo9Px3Mt6QkhNYU1p'),
            ('https://www.youtube.com/playlist?list=PL4cUxeGkcC9gC88BEo9Px3Mt6QkhNYU1p', 'PL4cUxeGkcC9gC88BEo9Px3Mt6QkhNYU1p'),
            ('https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLr6-S5450-48hUshVeb4xKx0Kk5h6KqYx', 'PLr6-S5450-48hUshVeb4xKx0Kk5h6KqYx'),
            ('http://youtu.be/watch?list=PLbpi6ZahtOH6Bv346L4e13_m27r07bB8t', 'PLbpi6ZahtOH6Bv346L4e13_m27r07bB8t'),
        ]
        for input_val, expected_id in valid_cases:
            self.assertEqual(extract_youtube_playlist_id(input_val), expected_id)

    def test_generate_ai_course_syllabus(self):
        from .utils import generate_ai_course_syllabus
        syllabus = generate_ai_course_syllabus('Python for Data Science', timeline_duration='1 Month')
        self.assertIn('course_title', syllabus)
        self.assertIn('modules', syllabus)
        self.assertGreaterEqual(len(syllabus['modules']), 1)
        for m in syllabus['modules']:
            self.assertTrue('title' in m or 'module_title' in m)
            self.assertIn('lessons', m)
            self.assertGreaterEqual(len(m['lessons']), 1)

    def test_fetch_youtube_playlist_videos(self):
        from .utils import fetch_youtube_playlist_videos
        result = fetch_youtube_playlist_videos('PL4cUxeGkcC9gC88BEo9Px3Mt6QkhNYU1p')
        self.assertIn('playlist_title', result)
        self.assertIn('videos', result)
        self.assertGreaterEqual(len(result['videos']), 1)
        first_video = result['videos'][0]
        self.assertIn('title', first_video)
        self.assertIn('video_id', first_video)
        self.assertIn('youtube_url', first_video)

