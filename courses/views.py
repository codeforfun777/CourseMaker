import json
import logging
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from .forms import CourseForm, ModuleForm, LessonForm, LessonNotesForm, SignUpForm
from .models import Course, Module, Lesson, LessonTimestamp
from .youtube_utils import extract_youtube_chapters, parse_timestamp_lines
from .utils import (
    generate_ai_course_syllabus,
    fetch_youtube_playlist_videos,
    serialize_course,
    serialize_module,
    import_course_from_dict,
    import_module_from_dict
)

logger = logging.getLogger(__name__)


def campus_feed(request):
    """Campus discovery feed has been disabled; redirects to user dashboard."""
    return redirect('courses:dashboard')


@login_required
def dashboard(request):
    """User's private workspace displaying created courses with progress."""
    courses = Course.objects.filter(user=request.user).prefetch_related('modules__lessons')
    course_form = CourseForm()

    if request.method == 'POST':
        course_form = CourseForm(request.POST)
        if course_form.is_valid():
            new_course = course_form.save(commit=False)
            new_course.user = request.user
            new_course.save()
            messages.success(request, f'Course "{new_course.title}" was successfully created!')
            return redirect('courses:course_detail', pk=new_course.pk)

    total_courses = courses.count()
    completed_courses = sum(1 for c in courses if c.total_lessons_count > 0 and c.progress_percentage == 100)
    in_progress_courses = total_courses - completed_courses

    return render(request, 'courses/dashboard.html', {
        'courses': courses,
        'course_form': course_form,
        'total_courses': total_courses,
        'completed_courses': completed_courses,
        'in_progress_courses': in_progress_courses,
    })


@login_required
def course_detail(request, pk):
    """Course structure editor allowing users to organize modules and lessons."""
    course = get_object_or_404(Course.objects.prefetch_related('modules__lessons'), pk=pk)
    if course.user != request.user:
        return HttpResponseForbidden("You do not have permission to view this course.")

    is_owner = True
    module_form = ModuleForm()
    lesson_form = LessonForm()

    return render(request, 'courses/course_detail.html', {
        'course': course,
        'modules': course.modules.all(),
        'is_owner': is_owner,
        'module_form': module_form,
        'lesson_form': lesson_form,
    })


@login_required
@require_POST
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk, user=request.user)
    title = course.title
    course.delete()
    messages.success(request, f'Course "{title}" was deleted.')
    return redirect('courses:dashboard')


@login_required
def course_export(request, pk):
    """Exports an entire course including modules, lessons, notes, and timestamps to JSON."""
    course = get_object_or_404(Course, pk=pk, user=request.user)
    data = serialize_course(course)
    course_slug = slugify(course.title) or f"course_{course.pk}"
    filename = f"{course_slug}.json"

    response = HttpResponse(
        json.dumps(data, indent=2, ensure_ascii=False),
        content_type='application/json; charset=utf-8'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@require_POST
def course_import(request):
    """Imports a course from an uploaded JSON file."""
    uploaded_file = request.FILES.get('course_file')
    if not uploaded_file:
        messages.error(request, "Please select a JSON file to import.")
        return redirect('courses:dashboard')

    try:
        content = uploaded_file.read().decode('utf-8-sig')
        course_data = json.loads(content)
        if not isinstance(course_data, dict):
            messages.error(request, "Invalid course file format: expected a JSON object.")
            return redirect('courses:dashboard')

        new_course = import_course_from_dict(request.user, course_data)
        messages.success(request, f'Course "{new_course.title}" was successfully imported with {new_course.modules.count()} modules!')
        return redirect('courses:course_detail', pk=new_course.pk)
    except Exception as e:
        logger.error(f"Error importing course: {e}")
        messages.error(request, f"Failed to import course: {str(e)}")
        return redirect('courses:dashboard')


@login_required
def module_export(request, pk):
    """Exports a single module and its lessons/timestamps to JSON."""
    module = get_object_or_404(Module, pk=pk, course__user=request.user)
    data = serialize_module(module)
    mod_slug = slugify(module.title) or f"module_{module.pk}"
    filename = f"{mod_slug}.json"

    response = HttpResponse(
        json.dumps(data, indent=2, ensure_ascii=False),
        content_type='application/json; charset=utf-8'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@require_POST
def module_import(request, course_pk):
    """Imports a module from an uploaded JSON file into an existing course."""
    course = get_object_or_404(Course, pk=course_pk, user=request.user)
    uploaded_file = request.FILES.get('module_file')
    if not uploaded_file:
        messages.error(request, "Please select a JSON module file to import.")
        return redirect('courses:course_detail', pk=course.pk)

    try:
        content = uploaded_file.read().decode('utf-8-sig')
        module_data = json.loads(content)
        if not isinstance(module_data, dict):
            messages.error(request, "Invalid module file format: expected a JSON object.")
            return redirect('courses:course_detail', pk=course.pk)

        # If user uploaded a full course JSON file, import all its modules into this course
        if module_data.get('export_type') == 'course' and 'modules' in module_data:
            imported_count = 0
            for m_item in module_data.get('modules', []):
                import_module_from_dict(course, m_item)
                imported_count += 1
            messages.success(request, f"Imported {imported_count} modules into '{course.title}'!")
        else:
            new_module = import_module_from_dict(course, module_data)
            messages.success(request, f'Module "{new_module.title}" was imported successfully with {new_module.lessons.count()} lessons!')

        return redirect('courses:course_detail', pk=course.pk)
    except Exception as e:
        logger.error(f"Error importing module: {e}")
        messages.error(request, f"Failed to import module: {str(e)}")
        return redirect('courses:course_detail', pk=course.pk)


@login_required
@require_POST
def course_toggle_public(request, pk):
    course = get_object_or_404(Course, pk=pk, user=request.user)
    course.is_public = not course.is_public
    course.save()
    status_str = "public and shared to Campus Feed" if course.is_public else "private"
    messages.info(request, f'Course is now {status_str}.')
    return redirect('courses:course_detail', pk=course.pk)


@login_required
@require_POST
def module_create(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk)
    if course.user != request.user:
        return HttpResponseForbidden("Permission denied.")
    form = ModuleForm(request.POST)
    if form.is_valid():
        module = form.save(commit=False)
        module.course = course
        # Automatically assign order if default 0 and other modules exist
        if module.order == 0:
            module.order = course.modules.count() + 1
        module.save()
        messages.success(request, f'Module "{module.title}" added!')
    else:
        messages.error(request, 'Failed to add module. Please check your input.')
    return redirect('courses:course_detail', pk=course.pk)


@login_required
@require_POST
def module_delete(request, pk):
    module = get_object_or_404(Module, pk=pk, course__user=request.user)
    course_pk = module.course.pk
    module.delete()
    messages.success(request, 'Module deleted.')
    return redirect('courses:course_detail', pk=course_pk)


@login_required
@require_POST
def lesson_create(request, module_pk):
    module = get_object_or_404(Module, pk=module_pk, course__user=request.user)
    form = LessonForm(request.POST, request.FILES)
    if form.is_valid():
        lesson = form.save(commit=False)
        lesson.module = module
        if lesson.order == 0:
            lesson.order = module.lessons.count() + 1
        lesson.save()
        messages.success(request, f'Lesson "{lesson.title}" added!')
    else:
        messages.error(request, f'Failed to create lesson: {form.errors.as_text()}')
    return redirect('courses:course_detail', pk=module.course.pk)


@login_required
@require_POST
def lesson_delete(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk, module__course__user=request.user)
    course_pk = lesson.module.course.pk
    lesson.delete()
    messages.success(request, 'Lesson deleted.')
    return redirect('courses:course_detail', pk=course_pk)


@login_required
def lesson_view(request, pk):
    """The split-screen workspace interface dividing study resource and notes."""
    lesson = get_object_or_404(
        Lesson.objects.select_related('module__course__user'),
        pk=pk
    )
    course = lesson.module.course
    if course.user != request.user:
        return HttpResponseForbidden("You do not have permission to view this lesson.")

    is_owner = True

    # If it's a YouTube video and has no timestamps yet, try to auto-fetch YouTuber chapters once
    if lesson.lesson_type == Lesson.LessonType.YOUTUBE and not lesson.timestamps.exists() and lesson.youtube_url:
        try:
            chapters = extract_youtube_chapters(lesson.youtube_url)
            for ch in chapters:
                LessonTimestamp.objects.get_or_create(
                    lesson=lesson,
                    time_seconds=ch['time_seconds'],
                    defaults={'label': ch['label']}
                )
        except Exception:
            pass

    notes_form = LessonNotesForm(instance=lesson)

    # Prefetch modules and lessons for Udemy/Coursera sidebar
    course_modules = course.modules.prefetch_related('lessons').all()

    return render(request, 'courses/lesson_view.html', {
        'lesson': lesson,
        'course': course,
        'module': lesson.module,
        'is_owner': is_owner,
        'notes_form': notes_form,
        'next_lesson': lesson.get_next_lesson(),
        'prev_lesson': lesson.get_previous_lesson(),
        'course_modules': course_modules,
    })


@require_POST
def lesson_save_notes(request, pk):
    """AJAX or form-based notes saving without interrupting the video/study session."""
    lesson = get_object_or_404(Lesson, pk=pk)

    # Only course owner or logged in owner can edit notes
    if request.user.is_authenticated and lesson.module.course.user == request.user:
        # Check if content is sent via JSON payload or form POST
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                notes_text = data.get('notes', '')
            except json.JSONDecodeError:
                return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        else:
            notes_text = request.POST.get('notes', '')

        lesson.notes = notes_text
        lesson.save(update_fields=['notes'])

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({'status': 'success', 'message': 'Notes saved'})
        
        messages.success(request, 'Notes saved successfully!')
        return redirect('courses:lesson_view', pk=lesson.pk)

    return HttpResponseForbidden("Permission denied.")


@require_POST
def lesson_toggle_complete(request, pk):
    """Toggles lesson completion state with AJAX or regular POST response."""
    lesson = get_object_or_404(Lesson, pk=pk)

    if request.user.is_authenticated and lesson.module.course.user == request.user:
        lesson.is_completed = not lesson.is_completed
        lesson.save(update_fields=['is_completed'])

        course = lesson.module.course
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({
                'status': 'success',
                'is_completed': lesson.is_completed,
                'progress_percentage': course.progress_percentage,
                'completed_lessons': course.completed_lessons_count,
                'total_lessons': course.total_lessons_count,
            })

        return redirect('courses:lesson_view', pk=lesson.pk)

    return HttpResponseForbidden("Permission denied.")


@require_POST
def lesson_add_timestamp(request, pk):
    """Adds a named video timestamp bookmark to a lesson."""
    lesson = get_object_or_404(Lesson, pk=pk)

    if not (request.user.is_authenticated and lesson.module.course.user == request.user):
        return HttpResponseForbidden("Permission denied.")

    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            time_str = data.get('time', '').strip()
            label = data.get('label', '').strip()
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    else:
        time_str = request.POST.get('time', '').strip()
        label = request.POST.get('label', '').strip()

    if not label:
        return JsonResponse({'status': 'error', 'message': 'Label is required'}, status=400)

    time_seconds = LessonTimestamp.parse_time_string(time_str)

    timestamp = LessonTimestamp.objects.create(
        lesson=lesson,
        time_seconds=time_seconds,
        label=label
    )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({
            'status': 'success',
            'id': timestamp.id,
            'formatted_time': timestamp.formatted_time,
            'time_seconds': timestamp.time_seconds,
            'label': timestamp.label,
        })

    messages.success(request, f'Timestamp "{timestamp.label}" added!')
    return redirect('courses:lesson_view', pk=lesson.pk)


@require_POST
def lesson_delete_timestamp(request, pk):
    """Deletes a video timestamp."""
    timestamp = get_object_or_404(LessonTimestamp, pk=pk)
    lesson = timestamp.lesson

    if not (request.user.is_authenticated and lesson.module.course.user == request.user):
        return HttpResponseForbidden("Permission denied.")

    timestamp.delete()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({'status': 'success'})

    messages.success(request, 'Timestamp removed.')
    return redirect('courses:lesson_view', pk=lesson.pk)


@require_POST
def lesson_sync_youtube_chapters(request, pk):
    """Fetches YouTuber's official chapters/timestamps directly from the YouTube video."""
    lesson = get_object_or_404(Lesson, pk=pk)

    if not (request.user.is_authenticated and lesson.module.course.user == request.user):
        return HttpResponseForbidden("Permission denied.")

    if not lesson.youtube_url:
        return JsonResponse({'status': 'error', 'message': 'No YouTube URL provided'}, status=400)

    chapters = extract_youtube_chapters(lesson.youtube_url)
    added_count = 0

    for ch in chapters:
        obj, created = LessonTimestamp.objects.get_or_create(
            lesson=lesson,
            time_seconds=ch['time_seconds'],
            defaults={'label': ch['label']}
        )
        if created:
            added_count += 1

    all_ts = [
        {
            'id': ts.id,
            'formatted_time': ts.formatted_time,
            'time_seconds': ts.time_seconds,
            'label': ts.label,
        }
        for ts in lesson.timestamps.all()
    ]

    return JsonResponse({
        'status': 'success',
        'added_count': added_count,
        'timestamps': all_ts,
    })


@require_POST
def lesson_paste_timestamps(request, pk):
    """Parses multiline timestamp text (e.g. copied from YouTuber description)."""
    lesson = get_object_or_404(Lesson, pk=pk)

    if not (request.user.is_authenticated and lesson.module.course.user == request.user):
        return HttpResponseForbidden("Permission denied.")

    text = ""
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            text = data.get('text', '')
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    else:
        text = request.POST.get('text', '')

    parsed = parse_timestamp_lines(text)
    added_count = 0

    for item in parsed:
        obj, created = LessonTimestamp.objects.get_or_create(
            lesson=lesson,
            time_seconds=item['time_seconds'],
            defaults={'label': item['label']}
        )
        if created:
            added_count += 1

    all_ts = [
        {
            'id': ts.id,
            'formatted_time': ts.formatted_time,
            'time_seconds': ts.time_seconds,
            'label': ts.label,
        }
        for ts in lesson.timestamps.all()
    ]

    return JsonResponse({
        'status': 'success',
        'added_count': added_count,
        'timestamps': all_ts,
    })


def signup_view(request):
    """User registration view."""
    if request.user.is_authenticated:
        return redirect('courses:dashboard')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome to CourseMaker, {user.username}!')
            return redirect('courses:dashboard')
    else:
        form = SignUpForm()

    return render(request, 'courses/signup.html', {'form': form})


@login_required
@require_POST
def generate_ai_syllabus(request):
    """
    AI Syllabus Generator:
    Accepts topic, resource description, and timeline duration.
    Invokes the AI curriculum engine and creates a Course with structured Modules and Lessons.
    """
    topic = request.POST.get('topic', '').strip()
    resources_description = request.POST.get('resources_description', '').strip()
    timeline_duration = request.POST.get('timeline_duration', '1 Month').strip()

    if not topic:
        messages.error(request, "Please provide a course topic to generate an AI syllabus.")
        return redirect('courses:dashboard')

    try:
        syllabus = generate_ai_course_syllabus(
            topic=topic,
            resources_description=resources_description,
            timeline_duration=timeline_duration
        )

        course_title = syllabus.get('course_title') or f"{topic} ({timeline_duration})"
        course_desc = syllabus.get('course_description') or resources_description or f"AI-generated study track for {topic}."

        new_course = Course.objects.create(
            user=request.user,
            title=course_title,
            description=course_desc,
            is_public=False
        )

        modules_data = syllabus.get('modules', [])
        total_lessons_added = 0

        for m_idx, mod_item in enumerate(modules_data, start=1):
            mod_title = mod_item.get('title') or f"Module {m_idx}"
            module = Module.objects.create(
                course=new_course,
                title=mod_title,
                order=m_idx
            )

            lessons_to_create = []
            for l_idx, les_item in enumerate(mod_item.get('lessons', []), start=1):
                l_type = les_item.get('lesson_type', 'LINK').upper()
                if l_type not in ('YOUTUBE', 'PDF', 'LINK'):
                    l_type = 'LINK'

                ext_url = les_item.get('external_url') or les_item.get('url', '')
                yt_url = les_item.get('youtube_url', '') if l_type == 'YOUTUBE' else ''

                lessons_to_create.append(
                    Lesson(
                        module=module,
                        title=les_item.get('title', f"Lesson {l_idx}"),
                        lesson_type=l_type,
                        external_url=ext_url or None,
                        youtube_url=yt_url or None,
                        order=l_idx
                    )
                )

            if lessons_to_create:
                Lesson.objects.bulk_create(lessons_to_create)
                total_lessons_added += len(lessons_to_create)

        messages.success(
            request,
            f'✨ Successfully generated course "{new_course.title}" with {len(modules_data)} modules and {total_lessons_added} lessons!'
        )
        return redirect('courses:course_detail', pk=new_course.pk)

    except Exception as e:
        logger.error(f"Error in generate_ai_syllabus: {e}")
        messages.error(request, f"Unable to generate syllabus: {str(e)}")
        return redirect('courses:dashboard')


ai_generate_course = generate_ai_syllabus


@login_required
@require_POST
def import_youtube_playlist(request, course_pk):
    """
    YouTube Playlist Batch Importer:
    Accepts a YouTube Playlist URL or ID, queries the YouTube API,
    and creates a new Module containing each video as a sequential Lesson (type YOUTUBE).
    """
    course = get_object_or_404(Course, pk=course_pk)
    if course.user != request.user:
        return HttpResponseForbidden("Permission denied.")

    playlist_url = request.POST.get('playlist_url', '').strip()
    custom_module_title = request.POST.get('module_title', '').strip()

    if not playlist_url:
        messages.error(request, "Please provide a valid YouTube Playlist URL or ID.")
        return redirect('courses:course_detail', pk=course.pk)

    try:
        playlist_data = fetch_youtube_playlist_videos(playlist_url)
        videos = playlist_data.get('videos', [])

        if not videos:
            messages.error(request, "No playable videos found in the specified YouTube playlist.")
            return redirect('courses:course_detail', pk=course.pk)

        # Determine module title
        mod_title = custom_module_title or playlist_data.get('playlist_title') or "Imported YouTube Playlist"

        # Determine next module order
        max_order = course.modules.aggregate(models.Max('order'))['order__max'] or 0
        new_module_order = max_order + 1

        module = Module.objects.create(
            course=course,
            title=mod_title,
            order=new_module_order
        )

        lessons = []
        for v in videos:
            lessons.append(
                Lesson(
                    module=module,
                    title=v.get('title', 'Video Lesson'),
                    lesson_type=Lesson.LessonType.YOUTUBE,
                    youtube_url=v.get('youtube_url'),
                    order=v.get('order', len(lessons) + 1)
                )
            )

        Lesson.objects.bulk_create(lessons)

        messages.success(
            request,
            f'🎬 Successfully imported {len(lessons)} videos from playlist into new module "{module.title}"!'
        )

    except ValueError as ve:
        messages.error(request, str(ve))
    except Exception as e:
        logger.error(f"Error importing YouTube playlist: {e}")
        messages.error(request, f"Failed to import YouTube playlist: {str(e)}")

    return redirect('courses:course_detail', pk=course.pk)
