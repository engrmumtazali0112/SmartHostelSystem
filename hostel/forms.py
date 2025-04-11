from django import forms
from .models import MessMembership, MessAttendance
from django import forms
from .models import PaymentRequest

from django import forms
from .models import ShowcaseNotice, Student

# Add this to your hostel/forms.py file
from django import forms
from .models import ShowcaseNotice

# ==========================
# ShowCashes Notices Form
# ==========================

# forms.py
from django import forms
from .models import ShowcaseNotice, Student
from django_select2.forms import ModelSelect2MultipleWidget
# forms.py

from django import forms
from .models import ShowcaseNotice

# forms.py

from django import forms
from .models import ShowcaseNotice
from django.contrib.auth.models import User

class ShowcaseNoticeForm(forms.ModelForm):
    class Meta:
        model = ShowcaseNotice
        fields = ['title', 'description', 'notice_type', 'fine_amount', 'due_date', 'students']
        widgets = {
            'students': forms.SelectMultiple(attrs={'class': 'select2', 'style': 'width: 100%;'}),
        }
  
# ==========================
# Mess Membership Form
# ==========================

class MessMembershipForm(forms.ModelForm):
    class Meta:
        model = MessMembership
        fields = ['start_date', 'end_date']  # Fields that will be included in the form

    # Customize the widget to use date input for better UI
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

# ==========================
# Mess Attendance Form
# ==========================

class MessAttendanceForm(forms.ModelForm):
    class Meta:
        model = MessAttendance
        fields = ['is_present']  # Only the attendance status is needed for the form

# ==========================
# Payment Request Form
# ==========================

class PaymentRequestForm(forms.ModelForm):
    class Meta:
        model = PaymentRequest
        fields = [
            'amount', 
            'bank_name', 
            'transaction_id', 
            'transaction_date', 
            'payment_mode', 
            'proof_document'
        ]
        # Custom widget to use 'datetime-local' input for transaction date
        widgets = {
            'transaction_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    # Custom validation to ensure the transaction ID is unique
    def clean_transaction_id(self):
        transaction_id = self.cleaned_data['transaction_id']
        # Check if the transaction ID already exists in the database
        if PaymentRequest.objects.filter(transaction_id=transaction_id).exists():
            raise forms.ValidationError("This transaction ID has already been used.")
        return transaction_id
