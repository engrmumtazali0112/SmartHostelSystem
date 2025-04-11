from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import RegexValidator

import datetime

# ==========================
# Hostel Model
# ==========================

from django.core.exceptions import ValidationError

class Hostel(models.Model):
    Hostel_ID = models.AutoField(primary_key=True)
    Hostel_Name = models.CharField(max_length=255, unique=True)
    No_Of_Rooms = models.IntegerField(default=0)
    No_Of_Students = models.IntegerField(default=0)
    Single_Seater_Rooms = models.IntegerField(default=0)
    Two_Seater_Rooms = models.IntegerField(default=0)
    Three_Seater_Rooms = models.IntegerField(default=0)
    Six_Seater_Rooms = models.IntegerField(default=0)

    def total_rooms(self):
        return self.Single_Seater_Rooms + self.Two_Seater_Rooms + self.Three_Seater_Rooms + self.Six_Seater_Rooms

    def save(self, *args, **kwargs):
        """
        Override save method to ensure that the number of students in the hostel is at least 300.
        """
        if self.No_Of_Students < 300:
            raise ValidationError("Number of students must be at least 300.")
        if self.No_Of_Rooms != self.total_rooms():
            raise ValidationError("The total number of rooms must match the sum of individual room types.")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.Hostel_Name

# ==========================
# Room Model
# ==========================

class Room(models.Model):
    Room_ID = models.AutoField(primary_key=True)
    Room_Type = models.CharField(max_length=255)
    Capacity = models.IntegerField()
    Location = models.CharField(max_length=255)
    Room_No = models.CharField(max_length=50, unique=True)
    Floor_No = models.IntegerField()
    Students_Alloted = models.IntegerField(default=0)
    Hostel_ID = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="rooms")

    def save(self, *args, **kwargs):
        """
        Override save method to automatically set the room capacity based on its type.
        """
        capacity_map = {"Single Seater": 1, "Two Seater": 2, "Three Seater": 3, "Six Seater": 6}
        self.Capacity = capacity_map.get(self.Room_Type, self.Capacity)
        super().save(*args, **kwargs)

    def remaining_capacity(self):
        """
        Calculate the remaining capacity of the room based on the number of students allocated.
        """
        return self.Capacity - self.Students_Alloted

    def allocate_student(self):
        """
        Allocate one student to the room if there's remaining capacity.
        """
        if self.remaining_capacity() > 0:
            self.Students_Alloted += 1
            self.save()

    def remove_student(self):
        """
        Remove one student from the room and update the allocated student count.
        """
        if self.Students_Alloted > 0:
            self.Students_Alloted -= 1
            self.save()  # Ensure the room is saved after updating the count

    @property
    def is_available(self):
        """
        Return if the room is available based on remaining capacity.
        """
        return self.remaining_capacity() > 0

    def __str__(self):
        return f"{self.Room_No} ({self.Room_Type})"

# ==========================
# Student Model
# ==========================


class Student(models.Model):
    Room_ID = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, related_name="students")  # Added related_name="students"
    Hostel_ID = models.ForeignKey(Hostel, on_delete=models.SET_NULL, null=True)

    PAYMENT_STATUS_CHOICES = [
        ('NOT_PAID', 'Not Paid'),
        ('PARTIALLY_PAID', 'Partially Paid'),
        ('FULLY_PAID', 'Fully Paid'),
    ]

    Student_ID = models.AutoField(primary_key=True)
    Registration_Number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    profile_picture = models.ImageField(upload_to='student_profiles/', null=True, blank=True)

    F_Name = models.CharField(max_length=50)
    L_Name = models.CharField(max_length=50)
    Contact_Info = models.CharField(max_length=100)
    Address = models.TextField()
    Department = models.CharField(max_length=100)
    FatherName = models.CharField(max_length=50)
    fee_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='NOT_PAID')

    total_paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def update_fee_status(self):
        """
        Update the fee status of the student based on the total paid amount.
        """
        if self.total_paid_amount == 0:
            self.fee_status = 'NOT_PAID'
        elif self.total_paid_amount < self.total_fee_amount:
            self.fee_status = 'PARTIALLY_PAID'
        else:
            self.fee_status = 'FULLY_PAID'
        self.save()

    def calculate_remaining_fee(self):
        """
        Calculate the remaining fee to be paid.
        """
        return max(0, self.total_fee_amount - self.total_paid_amount)

    def remove_from_room(self):
        """
        Remove student from the room and update the room's allocated student count.
        """
        if self.Room_ID:
            room = self.Room_ID
            room.remove_student()
            self.Room_ID = None
            self.save()  # Save the student's data after removal from room

    @property
    def total_fee_amount(self):
        """
        Return the fee amount based on the room type.
        Ensure the student has a room before accessing Room_Type.
        """
        if self.Room_ID is None:
            return 0  # Return a default value or raise an error if no room is assigned
        room_fees = {
            'Single Seater': 120000,
            'Two Seater': 96000,
            'Three Seater': 80000,
            'Six Seater': 64000
        }
        return room_fees.get(self.Room_ID.Room_Type, 100000)

# ==========================
# Payment Model
# ==========================

class Payment(models.Model):
    pdf_file = models.FileField(upload_to='payments_pdfs/', null=True, blank=True)
    PAYMENT_STATUS_CHOICES = [
        ('PAID', 'Paid'),
        ('UNPAID', 'Unpaid'),
        ('PENDING', 'Pending')
    ]

    PAYMENT_MODE_CHOICES = [
        ('CASH', 'Cash'),
        ('ONLINE', 'Online'),
        ('BANK', 'Bank')
    ]

    Payment_ID = models.AutoField(primary_key=True)
    Student_ID = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='payments')
    Fee_Type = models.CharField(max_length=255)
    Payment_Date = models.DateTimeField(auto_now_add=True)
    Due_Date = models.DateTimeField(null=True, blank=True)
    Amount_Paid = models.DecimalField(max_digits=10, decimal_places=2)
    Receipt_Number = models.CharField(max_length=255)
    Fee_Status = models.CharField(max_length=50, choices=PAYMENT_STATUS_CHOICES, default='UNPAID')
    Voucher_No = models.CharField(max_length=255, default='VOU-', null=True, blank=True)
    Payment_Mode = models.CharField(max_length=50, choices=PAYMENT_MODE_CHOICES, default='CASH')
    Installment_Number = models.IntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        """
        Generate Voucher number for the payment if not already provided and update the student's fee status.
        """
        if not self.Voucher_No or self.Voucher_No == 'VOU-':
            self.Voucher_No = f'VOU-{timezone.now().strftime("%Y%m%d")}-{self.Payment_ID}'
        
        super().save(*args, **kwargs)

        student = self.Student_ID
        student.total_paid_amount = Payment.objects.filter(Student_ID=student).aggregate(
            total=models.Sum('Amount_Paid')
        )['total'] or 0
        student.update_fee_status()

# ==========================
# Admin Model
# ==========================

class Admin(models.Model):
    Admin_ID = models.AutoField(primary_key=True)
    Name = models.CharField(max_length=255)
    Password = models.CharField(max_length=128)
    Email = models.EmailField()
    Contact_Information = models.CharField(max_length=255)
    Admin_Role = models.CharField(max_length=100)
    Created_At = models.DateTimeField(auto_now_add=True)
    Updated_At = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.Name

# ==========================
# NoticeBoard Model
# ==========================

class NoticeBoard(models.Model):
    Notice_ID = models.AutoField(primary_key=True)
    Title = models.CharField(max_length=255)
    Content = models.TextField()
    Created_At = models.DateTimeField(auto_now_add=True)
    Expiry_Date = models.DateTimeField(null=True, blank=True)
    Admin_ID = models.ForeignKey(Admin, on_delete=models.CASCADE)
    Is_Active = models.BooleanField(default=True)

    def __str__(self):
        return self.Title


# ==========================
# ShowcaseNotice Model
# ==========================

# models.py update
# models.py

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class ShowcaseNotice(models.Model):
    NOTICE_TYPES = (
        ('noise', 'Noise Complaint'),
        ('fine', 'Fine'),
        ('damage', 'Property Damage'),
        ('conduct', 'Misconduct'),
        ('other', 'Other'),
    )
    
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField()
    notice_type = models.CharField(max_length=20, choices=NOTICE_TYPES)
    created_date = models.DateTimeField(default=timezone.now)
    fine_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    resolved = models.BooleanField(default=False)
    registration_number = models.CharField(max_length=100, unique=True, null=True, blank=True)
    students = models.ManyToManyField('Student', through='StudentShowcaseNotice', related_name='showcase_notices')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_showcase_notices')
    
    def save(self, *args, **kwargs):
        if not self.title:
            self.title = f"{self.get_notice_type_display()} - {timezone.now().strftime('%Y-%m-%d')}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title

# models.py
class StudentShowcaseNotice(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    notice = models.ForeignKey(ShowcaseNotice, on_delete=models.CASCADE)
    read = models.BooleanField(default=False)
    read_date = models.DateTimeField(null=True, blank=True)
    paid = models.BooleanField(default=False)  # Added Paid status
  
    def mark_as_read(self):
        self.read = True
        self.read_date = timezone.now()
        self.save()

    def mark_as_paid(self):
        self.paid = True
        self.save()

    class Meta:
        unique_together = ('student', 'notice')
    
        
# ==========================
# Visitor Model
# ==========================
class Visitor(models.Model):
    name = models.CharField(max_length=255)
    contact_info = models.CharField(max_length=255)
    visit_date = models.DateTimeField(default=timezone.now)
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='visitors')
    Visitor_ID_Proof = models.CharField(max_length=50, help_text="ID card number or other identification")
    purpose_of_visit = models.CharField(max_length=255)

    def __str__(self):
        return self.name


# ==========================
# Visitor Request Model
# ==========================

class VisitorRequest(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='visitor_requests')
    visitor = models.ForeignKey('Visitor', on_delete=models.CASCADE, related_name='requests')
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')], default='PENDING')
    is_read = models.BooleanField(default=False)
    time_in = models.DateTimeField(null=True, blank=True)
    time_out = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Request for {self.visitor.name} by {self.student.F_Name} {self.student.L_Name}"

# ==========================
# PaymentRequest Model
# ==========================

class PaymentRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected')
    ]

    PAYMENT_MODE_CHOICES = [
        ('ONLINE', 'Online Banking'),
        ('UPI', 'UPI'),
        ('BANK_TRANSFER', 'Bank Transfer')
    ]

    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='payment_requests')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    bank_name = models.CharField(max_length=100)
    transaction_id = models.CharField(max_length=100, unique=True)
    transaction_date = models.DateTimeField()
    payment_mode = models.CharField(max_length=50, choices=PAYMENT_MODE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    proof_document = models.FileField(upload_to='payment_proofs/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(null=True, blank=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Payment Request for {self.student.F_Name} {self.student.L_Name} - {self.transaction_id}"

    def approve_request(self):
        """
        This method is used to approve a payment request, create a Payment record,
        and update the status of the request to 'APPROVED'.
        """
        current_year = timezone.now().year
        semesters = [f'Fall-{current_year + i}' for i in range(4)] + \
                    [f'Spring-{current_year + i + 1}' for i in range(4)]
        
        existing_payments = self.student.payments.all()
        paid_semesters = existing_payments.values_list('Fee_Type', flat=True)
        
        # Find the first unpaid installment
        next_installment = None
        for semester in semesters:
            if semester not in paid_semesters:
                next_installment = semester
                break

        if next_installment:
            install_number = existing_payments.filter(Fee_Status='PAID').count() + 1
            voucher_no = f"VOU-{self.student.Registration_Number}-{install_number}"
            
            # Create a payment record
            payment = Payment.objects.create(
                Student_ID=self.student,
                Amount_Paid=self.amount,
                Payment_Mode=self.payment_mode,
                Fee_Status='PAID',
                Receipt_Number=self.transaction_id,
                Fee_Type=next_installment,
                Voucher_No=voucher_no,
                Installment_Number=install_number
            )
            
            self.status = 'APPROVED'
            self.save()
            return payment
        else:
            raise ValueError("All installments have been paid for this student.")



# ==========================
# Profile Model (For User Profile)
# ==========================

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    contact_info = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.user.username

# ==========================
# Complaint Model (For Complaints)
# ==========================

class Complaint(models.Model):
    Complaint_ID = models.AutoField(primary_key=True)
    Student_ID = models.ForeignKey('Student', on_delete=models.CASCADE)
    Admin_ID = models.ForeignKey('Admin', on_delete=models.CASCADE)
    Complaint_Description = models.TextField()
    Complaint_Type = models.CharField(max_length=255)
    Created_At = models.DateTimeField(auto_now_add=True)
    Updated_At = models.DateTimeField(auto_now=True)
    is_read = models.BooleanField(default=False)  # Track if complaint is read
    
    def __str__(self):
        return f"Complaint {self.Complaint_ID}"

# ==========================
# AdminRole Model (For Admin roles and permissions)
# ==========================

class AdminRole(models.Model):
    ROLE_CHOICES = [
        ('superuser', 'Superuser - Full System Access'),
        ('staff', 'Staff - Limited Administrative Access'),
        ('manager', 'Manager - Intermediate Administrative Access')
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    
    # Contact Information
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$', 
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    
    # Additional fields specific to admin
    department = models.CharField(max_length=100, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    
    # Permissions tracking
    can_manage_users = models.BooleanField(default=False)
    can_manage_system = models.BooleanField(default=False)
    can_view_reports = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

    def get_permissions(self):
        """
        Return a dictionary of permissions based on admin role
        """
        permissions = {
            'superuser': {
                'can_manage_users': True,
                'can_manage_system': True,
                'can_view_reports': True,
                'access_level': 3
            },
            'staff': {
                'can_manage_users': False,
                'can_manage_system': False,
                'can_view_reports': True,
                'access_level': 2
            },
            'manager': {
                'can_manage_users': True,
                'can_manage_system': False,
                'can_view_reports': True,
                'access_level': 1
            }
        }
        return permissions.get(self.role, {})

# ==========================
# Mess Membership Model
# ==========================

from django.db import models

# models.py

from django.db import models

# Define the Fingerprint model before MessMembership
class Fingerprint(models.Model):
    student = models.OneToOneField('Student', on_delete=models.CASCADE)
    fingerprint_template = models.BinaryField()  # Store the fingerprint data as binary data
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Fingerprint for {self.student.F_Name} {self.student.L_Name}"

class MessMembership(models.Model):
    student = models.OneToOneField('Student', on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    department = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=False)
    approved = models.BooleanField(default=False)
    fingerprint = models.OneToOneField(Fingerprint, on_delete=models.SET_NULL, null=True, blank=True)  # Refer to Fingerprint here
    date_applied = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default="Pending", choices=[
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected")
    ])  

    def __str__(self):
        return f"{self.student.F_Name} {self.student.L_Name} Mess Membership"

# ==========================
# Mess Menu Model
# ==========================

class MessMenu(models.Model):
    # Meal time choices
    BREAKFAST = 'BF'
    LUNCH = 'LN'
    EVENING_TEA = 'ET'
    DINNER = 'DN'
    
    MEAL_CHOICES = [
        (BREAKFAST, 'Breakfast'),
        (LUNCH, 'Lunch'),
        (EVENING_TEA, 'Evening Tea/Squash'),
        (DINNER, 'Dinner'),
    ]
    
    # Days of the week for easier filtering
    MONDAY = 'MON'
    TUESDAY = 'TUE'
    WEDNESDAY = 'WED'
    THURSDAY = 'THU'
    FRIDAY = 'FRI'
    SATURDAY = 'SAT'
    SUNDAY = 'SUN'
    
    DAY_CHOICES = [
        (MONDAY, 'Monday'),
        (TUESDAY, 'Tuesday'),
        (WEDNESDAY, 'Wednesday'),
        (THURSDAY, 'Thursday'),
        (FRIDAY, 'Friday'),
        (SATURDAY, 'Saturday'),
        (SUNDAY, 'Sunday'),
    ]
    
    # Fields in the model
    date = models.DateField()
    day = models.CharField(max_length=3, choices=DAY_CHOICES, blank=True)
    meal_time = models.CharField(max_length=2, choices=MEAL_CHOICES)
    dish_name = models.TextField()  # TextField to accommodate multiple dishes
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    # Fields for easy organization
    week_number = models.IntegerField(blank=True, null=True)
    month = models.CharField(max_length=20, blank=True)
    year = models.IntegerField(blank=True, null=True)
    
    def save(self, *args, **kwargs):
        # Auto-populate the 'day' field based on the 'date' field
        if self.date and not self.day:
            self.day = self.date.strftime('%a').upper()[:3]
        
        # Auto-populate month and year if not provided
        if self.date and (not self.month or not self.year):
            self.month = self.date.strftime('%B')
            self.year = self.date.year
            self.week_number = self.date.isocalendar()[1]
            
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.get_meal_time_display()} on {self.date.strftime('%A')}: {self.dish_name[:30]}..."
    
    class Meta:
        # Order by date and meal time
        ordering = ['date', 'meal_time']
        # Add indexes to optimize queries for date and meal time
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['meal_time']),
            models.Index(fields=['month', 'year']),
        ]


# ==========================
# Mess Attendance Model
# ==========================
# Updated models.py with payment tracking
# Updated models.py with payment request system
from django.db import models
from django.utils import timezone
from django.urls import reverse

class MessAttendance(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    meal_time = models.CharField(max_length=2, choices=MessMenu.MEAL_CHOICES)
    is_present = models.BooleanField()
    price_charged = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    def __str__(self):
        return f"{self.student.F_Name} {self.student.L_Name} - {self.date} - {self.get_meal_time_display()} - {'Present' if self.is_present else 'Absent'}"
        
    def save(self, *args, **kwargs):
        if self.is_present:
            # Fetch the meal price for the given date and meal time
            menu_item = MessMenu.objects.filter(date=self.date, meal_time=self.meal_time).first()
            if menu_item:
                self.price_charged = menu_item.price
        super().save(*args, **kwargs)
        
        # After saving, check if student has completed 10 days of attendance
        self.check_attendance_milestone()
    
    def check_attendance_milestone(self):
        """Check if student has completed 10 days of attendance and create payment request if needed"""
        # Count the number of unique days with attendance in the last 30 days
        today = timezone.now().date()
        thirty_days_ago = today - timezone.timedelta(days=30)
        
        # Get distinct dates where the student was present for at least one meal
        attendance_days = MessAttendance.objects.filter(
            student=self.student,
            date__gte=thirty_days_ago,
            date__lte=today,
            is_present=True
        ).values('date').distinct()
        
        # Count the number of unique days
        days_count = attendance_days.count()
        
        # If exactly 10 days completed, create payment request
        if days_count == 10:
            # Check if payment request already exists for this milestone
            existing_request = MessPaymentRequest.objects.filter(
                student=self.student,
                status='PENDING',
                milestone_days=10
            ).exists()
            
            # Get unpaid bills
            unpaid_bills = MessBill.objects.filter(
                student=self.student,
                paid_status=False
            )
            
            # Calculate total due amount
            total_due = sum(bill.remaining_due() for bill in unpaid_bills)
            
            # Only create request if none exists and there are unpaid bills
            if not existing_request and unpaid_bills.exists() and total_due > 0:
                # Create payment request
                payment_request = MessPaymentRequest.objects.create(
                    student=self.student,
                    request_date=timezone.now(),
                    amount=total_due,
                    status='PENDING',
                    milestone_days=10,
                    request_note=f"Payment request after {days_count} days attendance. Registration: {self.student.reg_no}"
                )
                
                # Associate bills with the payment request
                for bill in unpaid_bills:
                    payment_request.bills.add(bill)


class MessPaymentRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected')
    ]
    
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    request_date = models.DateTimeField(default=timezone.now)
    bills = models.ManyToManyField('MessBill', related_name='payment_requests')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    processed_date = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_payments')
    request_note = models.CharField(max_length=255, blank=True, null=True)
    admin_note = models.CharField(max_length=255, blank=True, null=True)
    milestone_days = models.IntegerField(default=10)  # Number of days attendance achieved
    
    def __str__(self):
        return f"Payment Request for {self.student.F_Name} {self.student.L_Name} on {self.request_date}"
    
    def approve_payment(self, admin_user, note=None):
        """Approve the payment request and mark bills as paid"""
        self.status = 'APPROVED'
        self.processed_date = timezone.now()
        self.processed_by = admin_user
        if note:
            self.admin_note = note
        self.save()
        
        # Mark bills as paid and create payment record
        for bill in self.bills.all():
            bill.paid_status = True
            bill.paid_amount = bill.amount_due
            bill.payment_date = timezone.now()
            bill.save()
            
            # Create payment record
            MessPayment.objects.create(
                student=self.student,
                bill=bill,
                payment_date=timezone.now(),
                amount=bill.amount_due,
                payment_method='ADMIN',
                payment_note=f"Payment approved by admin after {self.milestone_days} days attendance"
            )
    
    def reject_payment(self, admin_user, note=None):
        """Reject the payment request"""
        self.status = 'REJECTED'
        self.processed_date = timezone.now()
        self.processed_by = admin_user
        if note:
            self.admin_note = note
        self.save()


class MessPayment(models.Model):
    PAYMENT_METHODS = [
        ('CASH', 'Cash'),
        ('BANK', 'Bank Transfer'),
        ('ADMIN', 'Admin Approved'),
        ('OTHER', 'Other')
    ]
    
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    bill = models.ForeignKey('MessBill', on_delete=models.CASCADE, related_name='payments')
    payment_date = models.DateTimeField(default=timezone.now)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, default='CASH')
    payment_note = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return f"Payment of {self.amount} for {self.student.F_Name} {self.student.L_Name} on {self.payment_date}"





# ==========================
# Mess Bill Model
# ==========================

class MessBill(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    bill_date = models.DateField(default=timezone.now)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_status = models.BooleanField(default=False)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Bill for {self.student.F_Name} {self.student.L_Name} - {self.bill_date}"
    
    def remaining_due(self):
        return self.amount_due - self.paid_amount
    
    def save(self, *args, **kwargs):
        # Calculate the bill amount based on attendance
        if not self.id:  # If it's a new bill
            attendance_today = MessAttendance.objects.filter(student=self.student, date=self.bill_date)
            self.amount_due = sum(attendance.price_charged for attendance in attendance_today if attendance.is_present)
        
        # If bill is being marked as paid and payment_date isn't set, set it now
        if self.paid_status and not self.payment_date:
            self.payment_date = timezone.now()
            
        super().save(*args, **kwargs)

# ==========================
# Face Detection Record Model
# ==========================

class FaceDetectionRecord(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    image_url = models.URLField(null=True, blank=True)  # URL for the face detection image
    detected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Face detection record for {self.student} on {self.detected_at}"


class MessRequest(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    request_date = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)  # Tracks if the request has been read
    description = models.TextField()  # Description or details of the mess request
    
    def __str__(self):
        return f"Mess Request by {self.student.full_name} on {self.request_date}"