from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'courses'

urlpatterns = [
    # Campus discovery feed
    path('', views.campus_feed, name='campus_feed'),

    # User dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Course management
    path('course/<int:pk>/', views.course_detail, name='course_detail'),
    path('course/<int:pk>/delete/', views.course_delete, name='course_delete'),
    path('course/<int:pk>/toggle-public/', views.course_toggle_public, name='course_toggle_public'),
    path('course/ai-generate/', views.generate_ai_syllabus, name='generate_ai_syllabus'),
    path('course/generate-ai-syllabus/', views.generate_ai_syllabus, name='ai_generate_course'),
    path('course/<int:course_pk>/import-playlist/', views.import_youtube_playlist, name='import_youtube_playlist'),

    # Modules
    path('course/<int:course_pk>/module/create/', views.module_create, name='module_create'),
    path('module/<int:pk>/delete/', views.module_delete, name='module_delete'),

    # Lessons
    path('module/<int:module_pk>/lesson/create/', views.lesson_create, name='lesson_create'),
    path('lesson/<int:pk>/delete/', views.lesson_delete, name='lesson_delete'),
    path('lesson/<int:pk>/', views.lesson_view, name='lesson_view'),
    path('lesson/<int:pk>/save-notes/', views.lesson_save_notes, name='lesson_save_notes'),
    path('lesson/<int:pk>/toggle-complete/', views.lesson_toggle_complete, name='lesson_toggle_complete'),
    path('lesson/<int:pk>/timestamp/add/', views.lesson_add_timestamp, name='lesson_add_timestamp'),
    path('lesson/<int:pk>/timestamp/sync/', views.lesson_sync_youtube_chapters, name='lesson_sync_youtube_chapters'),
    path('lesson/<int:pk>/timestamp/paste/', views.lesson_paste_timestamps, name='lesson_paste_timestamps'),
    path('timestamp/<int:pk>/delete/', views.lesson_delete_timestamp, name='lesson_delete_timestamp'),

    # Auth
    path('signup/', views.signup_view, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='courses/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='courses:campus_feed'), name='logout'),
]

