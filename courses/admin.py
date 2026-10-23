from django.contrib import admin
from .models import Course, Module, Lesson, LessonTimestamp


class LessonTimestampInline(admin.TabularInline):
    model = LessonTimestamp
    extra = 1
    fields = ('time_seconds', 'label')


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ('title', 'lesson_type', 'order', 'is_completed', 'youtube_url', 'google_drive_url', 'external_url')
    show_change_link = True


class ModuleInline(admin.TabularInline):
    model = Module
    extra = 1
    fields = ('title', 'order')
    show_change_link = True


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'is_public', 'total_lessons_count', 'progress_display', 'created_at', 'updated_at')
    list_filter = ('is_public', 'created_at', 'user')
    search_fields = ('title', 'description', 'user__username')
    list_editable = ('is_public',)
    inlines = [ModuleInline]

    @admin.display(description='Progress')
    def progress_display(self, obj):
        return f"{obj.progress_percentage}% ({obj.completed_lessons_count}/{obj.total_lessons_count})"


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'lessons_count')
    list_filter = ('course',)
    search_fields = ('title', 'course__title')
    list_editable = ('order',)
    inlines = [LessonInline]

    @admin.display(description='Lessons Count')
    def lessons_count(self, obj):
        return obj.lessons.count()


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'get_course', 'lesson_type', 'order', 'is_completed')
    list_filter = ('lesson_type', 'is_completed', 'module__course')
    search_fields = ('title', 'notes', 'module__title', 'module__course__title')
    list_editable = ('order', 'is_completed')
    inlines = [LessonTimestampInline]

    @admin.display(description='Course')
    def get_course(self, obj):
        return obj.module.course.title


@admin.register(LessonTimestamp)
class LessonTimestampAdmin(admin.ModelAdmin):
    list_display = ('formatted_time', 'label', 'lesson', 'get_course')
    list_filter = ('lesson__module__course',)
    search_fields = ('label', 'lesson__title')

    @admin.display(description='Course')
    def get_course(self, obj):
        return obj.lesson.module.course.title
