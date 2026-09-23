"""apps/cms/urls.py"""

from django.urls import path
from . import views

app_name = "cms"

urlpatterns = [
    path("", views.home, name="home"),
    path("blog/", views.blog_list, name="blog_list"),
    path("blog/<slug:slug>/", views.blog_detail, name="blog_detail"),
    path("faqs/", views.faq_view, name="faq"),
    path("contact/", views.contact, name="contact"),
    path("pages/<slug:slug>/", views.static_page, name="static_page_prefixed"),
    path("<slug:slug>/", views.static_page, name="static_page"),
]
