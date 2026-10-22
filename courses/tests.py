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
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Python Course')
        self.assertNotContains(response, 'Bob Secret Course')

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
            'is_public': True
        })
        self.assertEqual(response.status_code, 302)
        new_course = Course.objects.get(title='New Django Mastery')
        self.assertEqual(new_course.user, self.user)

    def test_course_detail_public_access(self):
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

