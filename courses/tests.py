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
