from django.contrib import admin

from core.admin_jalali import JalaliAdminMixin

from .models import Book, Article, LibraryMembership


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'year', 'language', 'copies_available', 'is_available']
    list_filter = ['language', 'is_available', 'year']
    list_editable = ['copies_available', 'is_available']
    search_fields = ['title', 'author', 'isbn']


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'authors', 'section', 'journal', 'year']
    list_filter = ['section', 'year']
    search_fields = ['title', 'authors']


@admin.register(LibraryMembership)
class LibraryMembershipAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = ['full_name', 'student_id', 'email', 'status', 'created_jalali']
    list_filter = ['status']
    list_editable = ['status']
    search_fields = ['full_name', 'student_id']
