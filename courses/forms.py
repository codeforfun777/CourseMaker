from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Course, Module, Lesson


class TailwindWidgetMixin:
    """Helper mixin to consistently apply Tailwind styling to form inputs with dark mode support."""
    def apply_tailwind(self):
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({
                    'class': 'h-4 w-4 rounded border-slate-300 dark:border-slate-600 dark:bg-slate-800 text-indigo-600 focus:ring-indigo-500'
                })
            elif isinstance(field.widget, (forms.Select,)):
                field.widget.attrs.update({
                    'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-800 dark:text-slate-100 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500'
                })
            elif isinstance(field.widget, (forms.Textarea,)):
                field.widget.attrs.update({
                    'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-800 dark:text-slate-100 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500',
                    'rows': 3,
                })
            elif isinstance(field.widget, (forms.FileInput,)):
                field.widget.attrs.update({
                    'class': 'w-full text-sm text-slate-500 dark:text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 dark:file:bg-indigo-950/60 file:text-indigo-700 dark:file:text-indigo-400 hover:file:bg-indigo-100 dark:hover:file:bg-indigo-900'
                })
            else:
                field.widget.attrs.update({
                    'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-800 dark:text-slate-100 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500'
                })


class CourseForm(TailwindWidgetMixin, forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g. Full-Stack Web Development, CS50 Exam Prep'}),
            'description': forms.Textarea(attrs={'placeholder': 'Brief summary of what this custom course covers...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_tailwind()


class ModuleForm(TailwindWidgetMixin, forms.ModelForm):
    class Meta:
        model = Module
        fields = ['title', 'order']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g. Chapter 1: Introduction to Algorithms'}),
            'order': forms.NumberInput(attrs={'placeholder': '0', 'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_tailwind()


class LessonForm(TailwindWidgetMixin, forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'lesson_type', 'youtube_url', 'external_url', 'pdf_file', 'notes', 'order']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g. Lecture 1: Big O Notation'}),
            'youtube_url': forms.URLInput(attrs={'placeholder': 'https://www.youtube.com/watch?v=...'}),
            'external_url': forms.URLInput(attrs={'placeholder': 'https://example.com/article'}),
            'notes': forms.Textarea(attrs={'placeholder': 'Initial study notes or key takeaways...'}),
            'order': forms.NumberInput(attrs={'placeholder': '0', 'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_tailwind()


class LessonNotesForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['notes']
        widgets = {
            'notes': forms.Textarea(attrs={
                'class': 'w-full h-full p-4 text-slate-800 dark:text-slate-100 bg-transparent border-0 resize-none focus:outline-none font-mono text-sm leading-relaxed',
                'placeholder': 'Type your Markdown study notes, timestamps, or lecture summaries here...',
            })
        }


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-800 dark:text-slate-100 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-800 dark:text-slate-100 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500'
            })
