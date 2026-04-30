from django.urls import path
from . import views

urlpatterns = [
    # Landing page (public)
    path('about/', views.landing, name='landing'),

    # Auth
    path('register/', views.register_view, name='register'),
    path('logout/',   views.logout_view,   name='logout'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Staff portal
    path('staff/',             views.staff_dashboard,  name='staff_dashboard'),
    path('staff/volunteers/',  views.staff_volunteers, name='staff_volunteers'),
    path('staff/import/',      views.staff_import_csv, name='staff_import_csv'),
    path('staff/add-company/', views.quick_add_company, name='staff_add_company'),
    path('staff/assign/',      views.quick_assign,      name='staff_assign'),
    path('staff/invite/',      views.quick_invite,      name='staff_invite'),
    path('staff/create-admin/', views.create_admin,     name='staff_create_admin'),

    # Companies
    path('companies/',                                        views.company_list,        name='company_list'),
    path('companies/<int:pk>/',                               views.company_detail,      name='company_detail'),
    path('companies/<int:pk>/contact/',                       views.log_contact_attempt, name='log_contact_attempt'),
    path('companies/<int:pk>/visit/',                         views.log_visit,           name='log_visit'),
    path('companies/<int:pk>/visit/<int:note_pk>/edit/',      views.edit_visit_note,     name='edit_visit_note'),

    # Badges
    path('badges/', views.badge_list, name='badge_list'),

    # Leaderboard
    path('leaderboard/', views.leaderboard, name='leaderboard'),

    # Messages
    path('messages/',              views.message_list,   name='message_list'),
    path('messages/new/',          views.message_create,  name='message_create'),
    path('messages/<int:pk>/',     views.message_detail,  name='message_detail'),
]
