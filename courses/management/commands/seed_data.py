from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from courses.models import Course, Module, Lesson, LessonTimestamp

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds sample courses, modules, and lessons for development demonstration'

    def handle(self, *args, **options):
        self.stdout.write('Seeding initial LMS data...')

        user, created = User.objects.get_or_create(
            username='demo_student',
            defaults={'email': 'student@campus.edu'}
        )
        if created:
            user.set_password('student123')
            user.save()
            self.stdout.write(self.style.SUCCESS('Created user: demo_student / student123'))

        # Course 1: Full-Stack Web Development
        course1, _ = Course.objects.get_or_create(
            user=user,
            title='Modern Full-Stack Web Architecture',
            defaults={
                'description': 'A comprehensive curriculum covering HTTP/3, Django backend systems, REST APIs, and modern responsive frontends.',
                'is_public': True,
            }
        )

        mod1, _ = Module.objects.get_or_create(
            course=course1,
            title='Module 1: Internet Architecture & Protocols',
            defaults={'order': 1}
        )

        l1, _ = Lesson.objects.get_or_create(
            module=mod1,
            title='How the Internet Works in 5 Minutes',
            defaults={
                'lesson_type': Lesson.LessonType.YOUTUBE,
                'youtube_url': 'https://www.youtube.com/watch?v=7_LPdttKXPc',
                'notes': '## Key Takeaways:\n- Packets travel across physical fiber optic backbones.\n- DNS translates domain names into IP addresses.\n- TCP guarantees packet ordering and delivery.',
                'is_completed': True,
                'order': 1,
            }
        )

        # Seed sample timestamps for Lesson 1
        LessonTimestamp.objects.get_or_create(
            lesson=l1,
            time_seconds=0,
            defaults={'label': 'Introduction & Physical Cables'}
        )
        LessonTimestamp.objects.get_or_create(
            lesson=l1,
            time_seconds=75,
            defaults={'label': 'IP Addresses & DNS Lookup'}
        )
        LessonTimestamp.objects.get_or_create(
            lesson=l1,
            time_seconds=170,
            defaults={'label': 'Packets, Routers & Network Traffic'}
        )
        LessonTimestamp.objects.get_or_create(
            lesson=l1,
            time_seconds=250,
            defaults={'label': 'TCP/IP Reliability & Wrap-up'}
        )

        Lesson.objects.get_or_create(
            module=mod1,
            title='MDN Web Architecture Overview',
            defaults={
                'lesson_type': Lesson.LessonType.LINK,
                'external_url': 'https://developer.mozilla.org/en-US/docs/Learn/Server-side/First_steps/Client-Server_overview',
                'notes': 'Review the client-server interaction diagrams for exam prep.',
                'is_completed': False,
                'order': 2,
            }
        )

        mod2, _ = Module.objects.get_or_create(
            course=course1,
            title='Module 2: Django Backend & ORM',
            defaults={'order': 2}
        )

        Lesson.objects.get_or_create(
            module=mod2,
            title='Django Framework Overview',
            defaults={
                'lesson_type': Lesson.LessonType.YOUTUBE,
                'youtube_url': 'https://www.youtube.com/watch?v=01nyW2pGjR8',
                'notes': '## Django Components\n- MVT pattern (Model-View-Template)\n- Built-in admin panel\n- Migrations handle database schema diffs automatically',
                'is_completed': False,
                'order': 1,
            }
        )

        # Course 2: Linear Algebra for AI
        course2, _ = Course.objects.get_or_create(
            user=user,
            title='Linear Algebra & Deep Learning Intuition',
            defaults={
                'description': 'Master vector spaces, matrix transformations, and eigenvalues required for neural network backpropagation.',
                'is_public': True,
            }
        )

        mod2_1, _ = Module.objects.get_or_create(
            course=course2,
            title='Unit 1: Vectors and Linear Transformations',
            defaults={'order': 1}
        )

        Lesson.objects.get_or_create(
            module=mod2_1,
            title='Vectors: What even are they?',
            defaults={
                'lesson_type': Lesson.LessonType.YOUTUBE,
                'youtube_url': 'https://www.youtube.com/watch?v=fNk_zzaMoSs',
                'notes': '3 perspectives on vectors: Physics (arrows), CS (lists of numbers), Math (anything you can add or scale).',
                'is_completed': True,
                'order': 1,
            }
        )

        self.stdout.write(self.style.SUCCESS('Successfully populated sample course tracks!'))

