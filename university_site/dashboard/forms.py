from django import forms
from .models import StudentRequest, Enrollment, Assignment, AssignmentSubmission


class StudentRequestForm(forms.ModelForm):
    class Meta:
        model = StudentRequest
        fields = ['request_type', 'title', 'description', 'file']
        widgets = {
            'request_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'عنوان درخواست'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'توضیحات'}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class EnrollmentGradeForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ['mid_term_grade', 'final_grade', 'attendance_score', 'status']
        widgets = {
            'mid_term_grade': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '20'}),
            'final_grade': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '20'}),
            'attendance_score': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '20'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['course', 'title', 'description', 'assignment_type', 'due_date', 'max_score', 'file']
        widgets = {
            'course': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'assignment_type': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'max_score': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['due_date'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S']



class AssignmentSubmissionForm(forms.ModelForm):
    class Meta:
        model = AssignmentSubmission
        fields = ['file']
        widgets = {
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class SubmissionGradeForm(forms.ModelForm):
    class Meta:
        model = AssignmentSubmission
        fields = ['grade', 'feedback', 'status']
        widgets = {
            'grade': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'feedback': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class StaffRequestResponseForm(forms.ModelForm):
    class Meta:
        model = StudentRequest
        fields = ['status', 'response']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'response': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'پاسخ به دانشجو'}),
        }
