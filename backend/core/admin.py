from django.contrib import admin
from .models import Student, Attendance, Embedding

# ================= INLINE POUR EMBEDDINGS =================
class EmbeddingInline(admin.TabularInline):  # ou StackedInline si tu veux un affichage vertical
    model = Embedding
    extra = 0  # pas de ligne vide supplémentaire
    fields = ('enrollment_photo_path', 'created_date')
    readonly_fields = ('created_date',)

# ================= INLINE POUR ATTENDANCES =================
class AttendanceInline(admin.TabularInline):
    model = Attendance
    extra = 0
    fields = ('timestamp', 'confidence', 'matched_embedding')
    readonly_fields = ('timestamp',)

# ================= STUDENT =================
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'name', 'email', 'enrollment_date', 'active')
    search_fields = ('name', 'email')
    list_filter = ('active', 'enrollment_date')
    ordering = ('name',)
    inlines = [EmbeddingInline, AttendanceInline]  # affichage direct des embeddings et présences

# ================= ATTENDANCE =================
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('attendance_id', 'student', 'timestamp', 'confidence')
    search_fields = ('student__name',)
    list_filter = ('timestamp',)
    ordering = ('-timestamp',)

# ================= EMBEDDING =================
@admin.register(Embedding)
class EmbeddingAdmin(admin.ModelAdmin):
    list_display = ('embedding_id', 'student', 'enrollment_photo_path', 'created_date')
    search_fields = ('student__name',)
    list_filter = ('created_date',)
    ordering = ('-created_date',)
