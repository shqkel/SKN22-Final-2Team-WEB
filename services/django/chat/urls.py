from django.urls import path

from . import api_views

urlpatterns = [
    path("sessions/", api_views.sessions_view, name="chat-sessions"),
    path("sessions/<uuid:session_id>/", api_views.session_detail_view, name="chat-session-detail"),
    path("sessions/<uuid:session_id>/messages/", api_views.session_messages_view, name="chat-session-messages"),
]
