# Django standard imports
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta, date
from decimal import Decimal
from django.urls import reverse
from django.contrib.admin.views.decorators import staff_member_required

# Models
from .models import MessMenu, MessAttendance, MessBill, MessPayment, MessPaymentRequest, MessMembership, ShowcaseNotice, Student, Admin, VisitorRequest, Profile, Visitor, Room, Hostel, PaymentRequest, Fingerprint, MessRequest

# Forms
from .forms import ShowcaseNoticeForm, PaymentRequestForm, MessMembershipForm, PaymentRequest

# Image processing
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile

from .forms import *
from .forms import PaymentRequestForm, MessMembershipForm
from django.db import IntegrityError
from .models import Complaint, Payment

# ===========================
# Custom User Creation Form
# ===========================

class CustomUserCreationForm(forms.Form):
    name = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}))
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}))


# ===========================
# User Login Function
# ===========================

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        login_type = request.POST.get('login_type', 'user')

        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Check if user is attempting to access admin panel
            if login_type == 'admin':
                try:
                    admin = Admin.objects.get(Name=username)
                    login(request, user)
                    return redirect('dashboard')
                except Admin.DoesNotExist:
                    messages.error(request, "Access Denied. Please login as a student instead.")
                    return render(request, 'user_auth/login.html')
            else:
                # Check if user is a student trying to access student panel
                try:
                    student = Student.objects.get(user=user)
                    login(request, user)
                    return redirect('student_dashboard')
                except Student.DoesNotExist:
                    messages.error(request, "Access Denied. Please login as an admin instead.")
                    return render(request, 'user_auth/login.html')
        else:
            messages.error(request, "Invalid username or password.")
    
    return render(request, 'user_auth/login.html')
# ===========================
# User Registration Function
# ===========================

def user_register(request): 
    if request.method == 'POST': 
        form = CustomUserCreationForm(request.POST) 
        if form.is_valid(): 
            name = form.cleaned_data['name']
            email = form.cleaned_data['email'] 
            username = form.cleaned_data['username'] 
            password = form.cleaned_data['password'] 
            confirm_password = form.cleaned_data['confirm_password'] 
            registration_type = request.POST.get('registration_type', 'user') 

            # Password confirmation check 
            if password != confirm_password: 
                messages.error(request, "Passwords do not match.") 
                return render(request, 'user_auth/register.html', {'form': form}) 

            try: 
                # Create the user object 
                user = User.objects.create_user(username=username, email=email, password=password) 
                user.first_name = name.split()[0]  # Extract first name
                if len(name.split()) > 1:
                    user.last_name = name.split()[1]  # Extract last name if available
                user.save() 

                # Based on registration type, create appropriate profile 
                if registration_type == 'admin': 
                    Admin.objects.create( 
                        Name=name, 
                        Email=email, 
                        Password=password,  # Note: In production, use more secure password storage 
                        Admin_Role='Staff' 
                    ) 
                else: 
                    # Create student with the correct field names
                    names = name.split()
                    first_name = names[0]
                    last_name = names[1] if len(names) > 1 else ""
                    
                    student = Student.objects.create( 
                        user=user, 
                        F_Name=first_name,
                        L_Name=last_name,
                        Contact_Info="",  # Provide default values or make these fields optional
                        Address="",
                        # Add other required fields with default values
                    )

                    # Here, assign a default Room if none exists
                    # Assuming you have a Room model with a method to get a default or available room
                    default_room = Room.objects.first()  # or use any other logic to assign a room
                    student.Room_ID = default_room  # Set the default room
                    student.save()  # Save the student with the assigned room

                messages.success(request, "Registration successful. You can now log in.") 
                return redirect('login') 

            except IntegrityError: 
                messages.error(request, "Username already exists. Please choose a different one.")
            except Exception as e:
                messages.error(request, f"Registration failed: {str(e)}")
    else: 
        form = CustomUserCreationForm() 
    
    return render(request, 'user_auth/register.html', {'form': form})

# ===========================
# User Logout Function
# ===========================

def user_logout(request):
    logout(request)
    return redirect('login')

# ===========================
# Dashboard View for Admin
# ===========================
@login_required
def dashboard(request):
    # Get unread counts 
    unread_complaints = Complaint.objects.filter(is_read=False).count()
    
    # Change this line to count PENDING requests that are also unread
    pending_visitor_requests = VisitorRequest.objects.filter(status='PENDING', is_read=False).count()
    pending_payment_requests = PaymentRequest.objects.filter(status='PENDING', is_read=False).count()
    
    # Add unread mess requests
    unread_mess_requests = MessRequest.objects.filter(is_read=False).count()  # Assuming `is_read` tracks whether a request is read
    
    # Rest of your dashboard function remains the same
    total_students = Student.objects.count()
    students_with_paid_payment = Payment.objects.filter(Fee_Status='PAID').values('Student_ID').distinct().count()
    
    # Room statistics
    rooms = Room.objects.all()
    available_rooms = sum(1 for room in rooms if room.is_available)
    
    # Complaint statistics
    total_complaints = Complaint.objects.count()
    recent_complaints = Complaint.objects.order_by('-Created_At')[:5]
    
    # Active notices query
    current_date = timezone.now()
    active_notices_query = NoticeBoard.objects.filter(
        Is_Active=True
    ).filter(
        Q(Expiry_Date__isnull=True) | Q(Expiry_Date__gte=current_date)
    )
    
    # Get the count of active notices
    active_notices_count = active_notices_query.count()
    
    # Get the actual notices for display (limited to 5)
    active_notices = active_notices_query.order_by('-Created_At')[:5]
    
    context = {
        'total_students': total_students,
        'students_with_paid_payment': students_with_paid_payment,
        'available_rooms': available_rooms,
        'total_complaints': total_complaints,
        'unread_complaints': unread_complaints,
        'complaints': recent_complaints,
        'notices': active_notices,
        'active_notices': active_notices_count,
        'pending_visitor_requests': pending_visitor_requests,
        'pending_payment_requests': pending_payment_requests,
        'unread_mess_requests': unread_mess_requests,  # Add this line for Mess Requests
    }
    
    return render(request, 'dashboard.html', context)


# ===========================
# Student Profile View Function
# ===========================

@login_required
def std_profile(request):
    # Get the logged-in student's profile information
    student = Student.objects.get(user=request.user)
    
    # Check if the student has a hostel assigned
    if student.Hostel_ID is None:
        messages.error(request, "This student is not assigned to any hostel.")
        return redirect('assign_hostel')  # Replace 'assign_hostel' with the actual URL name for assigning a hostel
    
    # Prepare context data for rendering the profile page
    context = {
        'student': student,
        'personal_info': {
            'Father\'s Name': student.FatherName,
            'Email': student.user.email,
            'Contact': student.Contact_Info,
            'Address': student.Address,
            'Department': student.Department
        },
        'hostel_info': {
            'Hostel Name': student.Hostel_ID.Hostel_Name if student.Hostel_ID else "Not Assigned",
            'Room Number': student.Room_ID.Room_No if student.Room_ID else "Not Assigned",
            'Room Type': student.Room_ID.Room_Type if student.Room_ID else "Not Assigned",
            'Floor Number': student.Room_ID.Floor_No if student.Room_ID else "Not Assigned"
        },
        'fee_status_info': [
            ('Fee Status', student.fee_status, 'green' if student.fee_status == 'Paid' else 'red'),
            ('Total Fee', f'₹{student.total_fee_amount}', 'gray'),  # Use the property method for total fee
            ('Paid Amount', f'₹{student.total_paid_amount}', 'gray'),
            ('Remaining Fee', f'₹{student.calculate_remaining_fee()}', 'red')
        ],
        'notices': NoticeBoard.objects.filter(Is_Active=True).order_by('-Created_At')[:5]  # Latest active notices
    }
    
    # Render the student profile page
    return render(request, 'user_auth/std_profile.html', context)

# views.py
from django.shortcuts import render

def assign_hostel(request):
    # Logic to assign hostel or show a form for the student to select a hostel
    return render(request, 'assign_hostel.html')

# ===========================
# Student Dashboard View Function
# ===========================

@login_required
def student_dashboard(request):
    # Ensure the logged-in user is a student
    if not hasattr(request.user, 'student'):
        messages.error(request, "Access denied. Student account required.")
        return redirect('login')
    
    student = request.user.student
    
    # Get recent notices for the student
    recent_notices = NoticeBoard.objects.filter(
        Is_Active=True
    ).order_by('-Created_At')[:5]
    
    # Fetch the student's associated Showcase Notices
    student_showcase_notices = StudentShowcaseNotice.objects.filter(student=student).order_by('-notice__created_date')
    
    # Count the unread showcase notices for the student
    unread_showcase_notices_count = StudentShowcaseNotice.objects.filter(student=student, read=False).count()
    
    # Get room and hostel details
    room = student.Room_ID
    hostel = student.Hostel_ID
    
    # Calculate fee status
    total_fee = student.total_fee_amount
    paid_amount = student.total_paid_amount
    remaining_fee = student.calculate_remaining_fee()
    fee_percentage = (paid_amount / total_fee * 100) if total_fee > 0 else 0
    
    # Prepare context data for the dashboard
    context = {
        'student': student,
        'recent_notices': recent_notices,
        'student_showcase_notices': student_showcase_notices,  # Add this to display Showcase Notices
        'unread_showcase_notices_count': unread_showcase_notices_count,  # Pass the unread count
        'room': room,
        'hostel': hostel,
        'fee_status': {
            'total': total_fee,
            'paid': paid_amount,
            'remaining': remaining_fee,
            'percentage': round(fee_percentage, 2)
        }
    }
    
    # Render the student dashboard page
    return render(request, 'student_dashboard.html', context)

# ===========================
# List All Hostels
# ===========================

def list_hostels(request):
    # Fetch all hostel objects from the database
    hostels = Hostel.objects.all()
    # Render the list of hostels in the 'list_hostels.html' template
    return render(request, 'hostel_management/list_hostels.html', {'hostels': hostels})


# ===========================
# Add a Hostel and its Rooms
# ===========================

def add_hostel(request):
    if request.method == "POST":
        # Retrieve data from the POST request
        hostel_name = request.POST.get("hostel_name")
        no_of_rooms = int(request.POST.get("no_of_rooms"))
        no_of_students = int(request.POST.get("no_of_students"))
        single_seater = int(request.POST.get("single_seater"))
        two_seater = int(request.POST.get("two_seater"))
        three_seater = int(request.POST.get("three_seater"))
        six_seater = int(request.POST.get("six_seater"))

        # Validate if the hostel name is unique
        if Hostel.objects.filter(Hostel_Name=hostel_name).exists():
            messages.error(request, "Hostel name already exists!")
            return redirect("add_hostel")

        # Create a new hostel instance
        hostel = Hostel.objects.create(
            Hostel_Name=hostel_name,
            No_Of_Rooms=no_of_rooms,
            No_Of_Students=no_of_students,
            Single_Seater_Rooms=single_seater,
            Two_Seater_Rooms=two_seater,
            Three_Seater_Rooms=three_seater,
            Six_Seater_Rooms=six_seater,
        )
        hostel.save()

        # Create rooms for the hostel based on room types and assign sequential room numbers starting from 101
        room_types = [
            ("Single Seater", single_seater, 1),
            ("Two Seater", two_seater, 2),
            ("Three Seater", three_seater, 3),
            ("Six Seater", six_seater, 6)
        ]

        room_counter = 101  # Start room numbers from 101

        # Loop through each room type and create corresponding rooms
        for room_type, count, capacity in room_types:
            for _ in range(count):
                # Assign room number sequentially starting from 101
                room_no = f"{room_counter}"
                room_counter += 1  # Increment room counter for next room
                
                # Ensure the room number is unique
                while Room.objects.filter(Room_No=room_no).exists():
                    room_no = f"{room_counter}"
                    room_counter += 1

                # Create the room and associate it with the hostel
                Room.objects.create(
                    Room_Type=room_type,
                    Capacity=capacity,
                    Location=hostel.Hostel_Name,
                    Room_No=room_no,
                    Floor_No=(room_counter // 10) + 1,  # Calculate floor based on room number
                    Hostel_ID=hostel,
                )

        # Display success message and redirect to the list of hostels
        messages.success(request, "Hostel and rooms created successfully!")
        return redirect("list_hostels")

    # Render the hostel creation form if the request method is GET
    return render(request, 'hostel_management/add_hostel.html')


# ===========================
# Edit Hostel Information
# ===========================

def edit_hostel(request, hostel_id):
    # Retrieve the hostel object or return 404 if not found
    hostel = get_object_or_404(Hostel, Hostel_ID=hostel_id)
    if request.method == 'POST':
        # Update hostel fields based on the POST data
        hostel.Hostel_Name = request.POST.get('hostel_name')
        hostel.No_Of_Rooms = request.POST.get('no_of_rooms')
        hostel.No_Of_Students = request.POST.get('no_of_students')
        hostel.Single_Seater_Rooms = request.POST.get('single_seater')
        hostel.Two_Seater_Rooms = request.POST.get('two_seater')
        hostel.Three_Seater_Rooms = request.POST.get('three_seater')
        hostel.Six_Seater_Rooms = request.POST.get('six_seater')
        
        # Save the updated hostel information
        hostel.save()
        messages.success(request, "Hostel updated successfully!")
        return redirect('list_hostels')

    # Render the edit hostel form with the current hostel data
    return render(request, 'hostel_management/edit_hostel.html', {'hostel': hostel})


# ===========================
# Delete Hostel
# ===========================

def delete_hostel(request, hostel_id):
    # Retrieve the hostel object or return 404 if not found
    hostel = get_object_or_404(Hostel, Hostel_ID=hostel_id)
    
    # Delete the hostel record from the database
    hostel.delete()
    messages.success(request, "Hostel deleted successfully!")
    return redirect('list_hostels')




# ===========================
# Add Room Function
# ===========================

def add_room(request):
    if request.method == 'POST':
        # Retrieve room data from the POST request
        hostel_id = request.POST.get('hostel_id')
        room_type = request.POST.get('room_type')
        room_no = request.POST.get('room_no')
        floor_no = request.POST.get('floor_no')
        location = request.POST.get('location')
        students_alloted = request.POST.get('students_alloted', '0')
        
        # Debugging: Print received form data
        print("Received form data:")
        print(f"Hostel ID: {hostel_id}, Room Type: {room_type}, Room No: {room_no}, Floor No: {floor_no}, Location: {location}, Students Alloted: {students_alloted}")

        # Validate form fields
        if not hostel_id or not room_type or not room_no or not floor_no or not location:
            messages.error(request, "All fields are required.")
            return redirect('add_room')  # Redirect back to the form with error message

        try:
            hostel_id = int(hostel_id)
            floor_no = int(floor_no)
            students_alloted = int(students_alloted)
        except ValueError:
            messages.error(request, "Invalid input. Please enter valid integers for floor number and students allocated.")
            return redirect('add_room')

        # Fetch the selected hostel
        try:
            hostel = Hostel.objects.get(pk=hostel_id)
        except Hostel.DoesNotExist:
            messages.error(request, f"Hostel with ID {hostel_id} does not exist.")
            return redirect('add_room')

        # Validate room type and capacity
        capacity = {"Single Seater": 1, "Two Seater": 2, "Three Seater": 3, "Six Seater": 6}.get(room_type)
        if not capacity:
            messages.error(request, "Invalid room type selected.")
            return redirect('add_room')

        # Ensure that the room does not exceed its capacity
        if students_alloted > capacity:
            messages.error(request, f"Allocated students ({students_alloted}) cannot exceed room capacity ({capacity}).")
            return redirect('add_room')

        # Check if the room number already exists
        existing_room = Room.objects.filter(Room_No=room_no, Hostel_ID=hostel).first()
        if existing_room:
            messages.error(request, f"Room number {room_no} already exists in this hostel.")
            return redirect('add_room')

        # Add the new room
        try:
            room = Room.objects.create(
                Room_No=room_no,
                Room_Type=room_type,
                Capacity=capacity,
                Location=location,
                Floor_No=floor_no,
                Students_Alloted=students_alloted,
                Hostel_ID=hostel,
            )
            
            # Debugging: Check if the room was successfully created
            print(f"Room {room_no} created successfully in hostel {hostel.Hostel_Name}.")

            # Update the room count in the hostel
            hostel.No_Of_Rooms += 1
            hostel.save()

            messages.success(request, f"Room {room_no} added successfully!")
            return redirect('list_rooms')
        except Exception as e:
            messages.error(request, f"Error creating room: {str(e)}")
            print(f"Error creating room: {str(e)}")
            return redirect('add_room')

    # For GET request, load hostels for selection
    hostels = Hostel.objects.all()
    return render(request, 'room_management/add_room.html', {'hostels': hostels})

# ===========================
# List Rooms Function
# ===========================

def list_rooms(request):
    # Get all rooms with their related students
    rooms = Room.objects.all().prefetch_related('students')
    
    # Get search query from GET parameters
    search_query = request.GET.get('search', '')
    
    if search_query:
        rooms = rooms.filter(
            Q(Room_No__icontains=search_query) |
            Q(Room_Type__icontains=search_query) |
            Q(Location__icontains=search_query)
        )
    
    # Calculate room statistics
    for room in rooms:
        # Update remaining capacity for each room
        room.remaining_capacity = room.Capacity - room.Students_Alloted
        room.allocated_students = room.students.all().values(
            'Student_ID',
            'F_Name',
            'L_Name',
            'Department',
            'fee_status'
        )

    context = {
        'rooms': rooms,
        'search_query': search_query,
    }
    
    return render(request, 'room_management/list_rooms.html', context)


# ===========================
# Edit Room Function
# ===========================

def edit_room(request, room_id):
    # Fetch the room object or return 404 if not found
    room = get_object_or_404(Room, Room_ID=room_id)
    # Get the original hostel for comparison
    original_hostel = room.Hostel_ID
    
    if request.method == 'POST':
        # Retrieve updated values from the form
        room_no = request.POST.get('room_no')
        room_type = request.POST.get('room_type')
        floor_no = request.POST.get('floor_no')
        location = request.POST.get('location')
        students_alloted = request.POST.get('students_alloted', '0')
        
        # Convert numeric fields to integers
        try:
            floor_no = int(floor_no)
            students_alloted = int(students_alloted)
        except ValueError:
            messages.error(request, "Invalid input. Please enter valid integers for floor number and students allocated.")
            return redirect('edit_room', room_id=room_id)
        
        # Map room types to their capacities
        capacity_map = {
            "Single": 1, 
            "Double": 2, 
            "Triple": 3, 
            "Quad": 4
        }
        
        capacity = capacity_map.get(room_type)
        if not capacity:
            messages.error(request, "Invalid room type selected.")
            return redirect('edit_room', room_id=room_id)
            
        # Ensure students allocated doesn't exceed room capacity
        if students_alloted > capacity:
            messages.error(request, f"Allocated students ({students_alloted}) cannot exceed room capacity ({capacity}).")
            return redirect('edit_room', room_id=room_id)
        
        # Update the room details
        room.Room_No = room_no
        room.Room_Type = room_type
        room.Capacity = capacity
        room.Floor_No = floor_no
        room.Location = location
        room.Students_Alloted = students_alloted
        
        # Save the updated room details
        room.save()
        
        messages.success(request, "Room updated successfully!")
        return redirect('list_rooms')

    # For GET request, load hostels for selection
    hostels = Hostel.objects.all()
    
    # Prepare the room data for the template
    context = {
        'room': room,
        'hostels': hostels
    }
    
    return render(request, 'room_management/edit_room.html', context)


# ===========================
# Delete Room Function
# ===========================

def delete_room(request, room_id):
    room = get_object_or_404(Room, Room_ID=room_id)

    if request.method == 'POST':
        # Delete the room if confirmed
        room.delete()
        messages.success(request, "Room deleted successfully!")
        return redirect('list_rooms')

    return render(request, 'delete_room_confirmation.html', {'room': room})


# ===========================
# Image Compression Function
# ===========================

def compress_image(image):
    """
    This function takes an image, compresses it to a maximum size of 200x200 pixels,
    and returns the compressed image as an InMemoryUploadedFile object for further use.

    :param image: The image file to be compressed
    :return: An InMemoryUploadedFile object containing the compressed image
    """
    
    # Open the image using PIL (Python Imaging Library)
    img = Image.open(image)
    
    # Convert the image to RGB (necessary for saving as JPEG)
    img = img.convert('RGB')
    
    # Resize the image to a maximum of 200x200 pixels, keeping aspect ratio
    img.thumbnail((200, 200))
    
    # Save the compressed image to a BytesIO object (in-memory buffer)
    output = BytesIO()
    img.save(output, format='JPEG')  # Save image in JPEG format
    output.seek(0)  # Move the cursor to the beginning of the in-memory file
    
    # Return the compressed image as an InMemoryUploadedFile
    return InMemoryUploadedFile(output, 'ImageField', image.name, 'image/jpeg', output.getbuffer().nbytes, None)

# ===========================
# Add Student Function
# ===========================

@login_required
def add_student(request):
    if request.method == "POST":
        # Capture form data for new student
        email = request.POST.get("email")
        room_id = request.POST.get("room_id")
        hostel_id = request.POST.get("hostel_id")
        registration_number = request.POST.get("registration_number")  # Capture the registration number from form

        # Check if the username or email already exists
        if User.objects.filter(username=email).exists():
            messages.error(request, "A user with this email already exists.")
            return redirect("add_student")

        try:
            # Fetch room and hostel details
            room = Room.objects.get(pk=room_id)
            hostel = Hostel.objects.get(pk=hostel_id)
        except (Room.DoesNotExist, Hostel.DoesNotExist):
            messages.error(request, "Invalid room or hostel selection.")
            return redirect("add_student")

        # Check if room has remaining capacity
        if room.remaining_capacity() <= 0:
            messages.error(request, "The selected room is full.")
            return redirect("add_student")

        # Create the user
        user = User.objects.create_user(
            username=email,
            email=email,
            password=request.POST.get("password"),
            first_name=request.POST.get("first_name"),
            last_name=request.POST.get("last_name"),
        )
        user.save()

        # Process profile picture upload
        profile_picture = request.FILES.get("profile_picture")

        # Create the student record
        student = Student.objects.create(
            user=user,
            F_Name=request.POST.get("first_name"),
            L_Name=request.POST.get("last_name"),
            Contact_Info=request.POST.get("contact_info"),
            Address=request.POST.get("address"),
            Department=request.POST.get("department"),
            FatherName=request.POST.get("father_name"),
            fee_status="Unpaid",  # Default fee status
            Room_ID=room,
            Hostel_ID=hostel,
            Registration_Number=registration_number,  # Save the registration number
            profile_picture=profile_picture  # Save profile picture
        )

        # Increment Students_Alloted in the Room
        room.Students_Alloted += 1
        room.save()

        # Update remaining capacity after adding the student
        messages.success(request, "Student added successfully!")
        return redirect("list_students")

    # For GET request, load hostels and rooms for selection
    hostels = Hostel.objects.all()
    rooms = Room.objects.all()
    return render(request, 'student_management/add_student.html', {'hostels': hostels, 'rooms': rooms})


# ===========================
# View Student Function
# ===========================

@login_required
def view_student(request, student_id):
    # Get the student object based on student_id
    student = get_object_or_404(Student, Student_ID=student_id)

    return render(request, 'student_management/view_student.html', {'student': student})


# ===========================
# List All Students Function
# ===========================

@login_required
def list_students(request):
    # Get the search query from GET parameters
    search_query = request.GET.get('search', '')
    
    # Room type fees mapping
    room_fees = {
        'Single Seater': 120000,
        'Two Seater': 100000,
        'Three Seater': 68000,
        'Six Seater': 52000
    }
    
    students = Student.objects.all()
    
    # Calculate total fee for each student based on room type
    for student in students:
        if student.Room_ID:
            student.total_fee = room_fees.get(student.Room_ID.Room_Type, 5000)
        else:
            student.total_fee = 0
    
    if search_query:
        students = students.filter(
            Q(F_Name__icontains=search_query) |
            Q(L_Name__icontains=search_query) |
            Q(Registration_Number__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    return render(request, 'student_management/list_students.html', {
        'students': students,
        'search_query': search_query
    })


# ===========================
# Edit Student Function
# ===========================

@login_required
def edit_student(request, student_id):
    student = get_object_or_404(Student, Student_ID=student_id)

    if request.method == 'POST':
        # Get the previous room before changes
        previous_room = student.Room_ID

        # Update student details from form data
        student.F_Name = request.POST.get('first_name')
        student.L_Name = request.POST.get('last_name')
        student.user.email = request.POST.get('email')  # Update user email
        student.Contact_Info = request.POST.get('contact_info')
        student.Address = request.POST.get('address')
        student.Department = request.POST.get('department')
        student.FatherName = request.POST.get('father_name')
        student.fee_status = request.POST.get('fee_status')

        # Fetch room and hostel details from the form
        room_id = request.POST.get('room_id')
        hostel_id = request.POST.get('hostel_id')

        try:
            # Update room and hostel
            student.Room_ID = get_object_or_404(Room, Room_ID=room_id)
            student.Hostel_ID = get_object_or_404(Hostel, Hostel_ID=hostel_id)
        except (Room.DoesNotExist, Hostel.DoesNotExist):
            messages.error(request, "Invalid Room or Hostel ID selected!")
            return redirect('edit_student', student_id=student_id)

        # Update room allocations if the room changes
        if previous_room != student.Room_ID:
            # Decrease the capacity of the previous room (remove the student)
            previous_room.Students_Alloted -= 1
            previous_room.save()

            # Increase the capacity of the new room (add the student)
            student.Room_ID.Students_Alloted += 1
            student.Room_ID.save()

        # Save the user and student details
        student.user.save()  # Save the user model
        student.save()  # Save the student model

        messages.success(request, 'Student updated successfully!')
        return redirect('list_students')

    # Render the edit student form with current student data
    hostels = Hostel.objects.all()
    rooms = Room.objects.all()

    return render(request, 'student_management/edit_student.html', {'student': student, 'hostels': hostels, 'rooms': rooms})


# ===========================
# Delete Student Function
# ===========================

def delete_student(request, student_id):
    # Get the student object or return 404 if not found
    student = get_object_or_404(Student, pk=student_id)
    room = student.Room_ID  # Get the assigned room

    if request.method == "POST":
        # Delete the student from the database
        student.delete()  
        
        # Update the room allocation count
        if room:
            # Ensure the room doesn't go below 0 students
            room.Students_Alloted = max(room.Students_Alloted - 1, 0)  
            
            # Save the room after updating the student count
            room.save()

            # Recalculate and save remaining capacity
            room.remaining_capacity = room.Capacity - room.Students_Alloted
            room.save()

        # Display success message and redirect to the student list
        messages.success(request, "Student deleted successfully, and room availability updated!")
        return redirect("list_students")  # Redirect to student list

    # Render confirmation template
    return render(request, "confirm_delete.html", {"student": student})


# ===========================
# Add Notice View Function (Admin only)
# ===========================

@login_required
def add_notice(request):
    # Ensure that only admins can add notices
    if not request.user.is_staff:
        return redirect('student_dashboard')  # Redirect non-admin users to their dashboard
    
    # Check if the user has a profile; if not, create one
    if not hasattr(request.user, 'profile'):
        Profile.objects.create(user=request.user)
    
    # Fetch the admin associated with the logged-in user
    try:
        admin = Admin.objects.get(Email=request.user.email)
    except Admin.DoesNotExist:
        # If the admin doesn't exist, create one
        admin = Admin.objects.create(
            Name=request.user.username,
            Admin_Role='Superuser',
            Email=request.user.email,
            Contact_Information=request.user.profile.contact_info if hasattr(request.user.profile, 'contact_info') else request.user.email
        )
    
    # Handle POST request to create a new notice
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        expiry_date_str = request.POST.get('expiry_date')
        
        # Handle expiry date properly
        expiry_date = None
        if expiry_date_str and expiry_date_str.strip():
            try:
                expiry_date = timezone.make_aware(datetime.strptime(expiry_date_str, '%Y-%m-%d'))
            except ValueError:
                messages.error(request, 'Invalid date format. Please use YYYY-MM-DD format.')
                return render(request, 'add_notice.html')
        
        # Create and save the new notice
        notice = NoticeBoard.objects.create(
            Title=title,
            Content=content,
            Expiry_Date=expiry_date,
            Admin_ID=admin,  # Automatically link the notice to the admin
            Is_Active=True
        )
        
        # Display success message
        messages.success(request, 'Notice created successfully!')
        
        # Redirect to dashboard to see the notice right away
        return redirect('dashboard')  # Changed from 'list_of_notices'
    
    # Render the notice creation page
    return render(request, 'notice_complaint_management/add_notice.html')


# ===========================
# List All Notices Function (Admin only)
# ===========================

@login_required
def list_of_notices(request):
    # Ensure only admins can access the list of notices
    if not request.user.is_staff:
        return redirect('student_notices')  # Redirect students to their notice page
        
    # Fetch all notices from the database, ordered by the most recent
    notices = NoticeBoard.objects.all().order_by('-Created_At')
    
    # Render the list of notices
    return render(request, 'notice_complaint_management/list_of_noticeboard.html', {'notices': notices})


# ===========================
# View Specific Notice Function (Admin only)
# ===========================

@login_required
def view_notice(request, notice_id):
    # Ensure only admins can view the notice (students are redirected to their version)
    if not request.user.is_staff:
        return redirect('student_view_notice', notice_id=notice_id)
        
    try:
        # Fetch the notice using the ID
        notice = NoticeBoard.objects.get(Notice_ID=notice_id)
        return render(request, 'notice_complaint_management/view_notice.html', {'notice': notice})
    except NoticeBoard.DoesNotExist:
        # Handle the case where the notice doesn't exist
        messages.error(request, 'Notice not found!')
        return redirect('notice_complaint_management/list_of_notices')


# ===========================
# Edit Notice Function (Admin only)
# ===========================

@login_required
def edit_notice(request, notice_id):
    # Ensure only admins can edit the notice
    if not request.user.is_staff:
        return redirect('student_dashboard')  # Redirect non-admin users to their dashboard
    
    try:
        # Fetch the notice to be edited
        notice = NoticeBoard.objects.get(Notice_ID=notice_id)
        
        if request.method == 'POST':
            # Update notice fields from the form data
            notice.Title = request.POST.get('title')
            notice.Content = request.POST.get('content')
            notice.Expiry_Date = request.POST.get('expiry_date') or None
            notice.Is_Active = 'is_active' in request.POST
            notice.save()
            
            messages.success(request, 'Notice updated successfully!')
            return redirect('view_notice', notice_id=notice_id)
            
        # Render the edit form with current notice data
        return render(request, 'notice_complaint_management/edit_notice.html', {'notice': notice})
    except NoticeBoard.DoesNotExist:
        # Handle case where the notice does not exist
        messages.error(request, 'Notice not found!')
        return redirect('list_of_notices')


# ===========================
# Delete Notice Function (Admin only)
# ===========================

@login_required
def delete_notice(request, notice_id):
    # Ensure only admins can delete the notice
    if not request.user.is_staff:
        return redirect('student_dashboard')  # Redirect non-admin users to their dashboard

    try:
        # Fetch the notice to be deleted
        notice = NoticeBoard.objects.get(Notice_ID=notice_id)
    except NoticeBoard.DoesNotExist:
        # Handle case where the notice does not exist
        messages.error(request, 'Notice not found!')
        return redirect('list_of_notices')

    # Handle GET request to show the delete confirmation page
    if request.method == 'GET':
        return render(request, 'delete_notice_confirmation.html', {'notice': notice})

    # Handle POST request to delete the notice
    if request.method == 'POST':
        notice.delete()
        messages.success(request, 'Notice deleted successfully!')
        return redirect('list_of_notices')

# ===========================
# Student Notice Views
# ===========================

@login_required
def student_notices(request):
    # Fetch all active notices from the database
    notices = NoticeBoard.objects.filter(Is_Active=True).order_by('-Created_At')
    
    # Render the notice board for students
    return render(request, 'notice_complaint_management/student_notices.html', {'notices': notices})

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import NoticeBoard

@login_required
def student_view_notice(request, notice_id):
    try:
        # Attempt to retrieve the notice by its ID and ensure it is active
        notice = get_object_or_404(NoticeBoard, Notice_ID=notice_id, Is_Active=True)
        
        # Render the notice details for the student
        return render(request, 'notice_complaint_management/view_notice_student.html', {'notice': notice})
    
    except NoticeBoard.DoesNotExist:
        # If the notice doesn't exist or isn't active, show an error and redirect
        messages.error(request, 'Notice not found or has been deactivated.')
        return redirect('student_notices')


# ===========================
# Submit Complaint View
# ===========================

@login_required
def submit_complaint(request):
    # Ensure the user is a student
    if not hasattr(request.user, 'student'):
        messages.error(request, "You must be a student to submit a complaint.")
        return redirect('student_dashboard')  # Redirect to student dashboard
    
    student = request.user.student  # Get the student object related to the user

    if request.method == "POST":
        # Capture complaint details from the form
        complaint_description = request.POST.get('complaint_description')
        complaint_type = request.POST.get('complaint_type')

        # Fetch the first admin (in a real app, choose an appropriate admin)
        admin = Admin.objects.first()

        # Create and save the complaint
        Complaint.objects.create(
            Student_ID=student,
            Admin_ID=admin,
            Complaint_Description=complaint_description,
            Complaint_Type=complaint_type,
        )

        # Notify the student about successful complaint submission
        messages.success(request, "Your complaint has been submitted successfully.")
        return redirect('student_dashboard')  # Redirect to student dashboard

    # Render the complaint submission form
    return render(request, 'notice_complaint_management/submit_complaint.html')

# ===========================
# View Complaint Details
# ===========================

@login_required
def view_complaint(request, complaint_id):
    # Fetch the specific complaint by its ID
    complaint = get_object_or_404(Complaint, Complaint_ID=complaint_id)

    # Render the complaint details page
    return render(request, 'notice_complaint_management/view_complaint.html', {'complaint': complaint})

# ===========================
# List Complaints View
# ===========================

@login_required
def list_complaints(request):
    # Fetch all complaints ordered by creation date (latest first)
    complaints = Complaint.objects.all().order_by('-Created_At')

    # Mark all complaints as read when the user views them
    Complaint.objects.filter(is_read=False).update(is_read=True)
    
    # Reset the unread complaints count in the session
    request.session['unread_complaints'] = 0

    # Render the list of complaints
    return render(request, 'notice_complaint_management/list_complaints.html', {'complaints': complaints})

# ===========================
# All Student Fee Management
# ===========================

def fee_management(request):
    # Fetch all students along with their payments, room, and hostel info
    students = Student.objects.all().prefetch_related('payments', 'Room_ID', 'Hostel_ID')
    
    # Implement search functionality based on multiple fields
    search_query = request.GET.get('search', '')
    if search_query:
        students = students.filter(
            Q(F_Name__icontains=search_query) | 
            Q(L_Name__icontains=search_query) | 
            Q(user__email__icontains=search_query) | 
            Q(Department__icontains=search_query)
        )
    
    # Calculate fee status for each student
    for student in students:
        if hasattr(student, 'calculate_remaining_fee'):
            remaining = student.calculate_remaining_fee()
            # Check if the student has paid all fees or still has outstanding fees
            student.fee_status = 'Paid' if remaining <= 0 else 'Unpaid'
        else:
            student.fee_status = 'Unknown'
    
    # Return the fee management view with students and search query
      # When redirecting from this page to add_payment, ensure the URL is correct
    return render(request, 'payment_management/fee_management.html', {
        'students': students, 
        'search_query': search_query
    })


# ===========================
# Add Payment Information
# ===========================

@login_required
def add_payment(request):
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to add payments.")
        return redirect('dashboard')

    if request.method == "POST":
        student_id = request.POST.get("student_id")
        amount_paid = request.POST.get("amount_paid")
        fee_type = request.POST.get("fee_type")
        receipt_number = request.POST.get("receipt_number")
        payment_mode = request.POST.get("payment_mode")

        try:
            # Fetch the student by ID
            student = Student.objects.get(pk=student_id)
            
            # Get the current year's semesters
            current_year = timezone.now().year
            semesters = []
            for i in range(4):
                semesters.extend([f'Fall-{current_year + i}', f'Spring-{current_year + i + 1}'])

            # Find the next unpaid installment
            existing_payments = student.payments.all()
            paid_semesters = existing_payments.filter(Fee_Status='PAID').values_list('Fee_Type', flat=True)
            next_installment = None
            for semester in semesters:
                if semester not in paid_semesters:
                    next_installment = semester
                    break

            if next_installment:
                # Determine installment number and generate voucher number
                install_number = len(paid_semesters) + 1
                voucher_no = f"VOU-{student.Registration_Number}-{install_number}"

                # Create and save the payment record
                payment = Payment.objects.create(
                    Student_ID=student,
                    Fee_Type=next_installment,
                    Amount_Paid=amount_paid,
                    Receipt_Number=receipt_number,
                    Fee_Status="PAID",
                    Voucher_No=voucher_no,
                    Payment_Mode=payment_mode,
                    Installment_Number=install_number
                )

                messages.success(request, f"Payment of Rs{amount_paid} successfully added for {student.F_Name} {student.L_Name}")
                return redirect('fee_management')
            else:
                messages.error(request, "All installments have been paid for this student.")

        except Student.DoesNotExist:
            messages.error(request, "Student not found.")

    students = Student.objects.all()
    return render(request, 'payment_management/add_payment.html', {
        'students': students,
        'payment_modes': Payment.PAYMENT_MODE_CHOICES
    })


# ===========================
# Remove Payment Information
# ===========================

@login_required
def remove_payment(request, payment_id):
    payment = get_object_or_404(Payment, Payment_ID=payment_id)
    student = payment.Student_ID

    # Remove the payment record
    payment.delete()

    # Update student's fee status after payment removal
    if student.payments.filter(Fee_Status='PAID').count() == 0:
        student.fee_status = 'NOT_PAID'
    else:
        student.fee_status = 'PARTIALLY_PAID'
    student.save()

    messages.success(request, "Payment removed successfully, and fee status updated.")
    return redirect('payment_management/account_book')


# ===========================
# Account Book for Student
# ===========================

@login_required
def account_book(request, student_id=None):
    # If no student ID is provided and the user is a student, show their own account book
    if student_id is None:
        if hasattr(request.user, 'student'):
            student = request.user.student
        else:
            messages.error(request, "Please select a student to view their account book.")
            return redirect('fee_management')
    else:
        student = get_object_or_404(Student, Student_ID=student_id)
    
    # Get all payments for the student, ordered by payment date
    payments = student.payments.all().order_by('Payment_Date')
    
    # Calculate fee details based on room type
    room_fees = {
        'Single Seater': 120000,
        'Two Seater': 100000,
        'Three Seater': 68000,
        'Six Seater': 52000
    }
    
    total_fee = room_fees.get(student.Room_ID.Room_Type, 5000)
    per_installment = total_fee // 8
    
    # Calculate total paid and remaining fees
    paid_payments = payments.filter(Fee_Status='PAID')
    paid_installments = paid_payments.count()
    remaining_fee = total_fee - (paid_installments * per_installment)
    
    # Generate the expected payments for each semester
    semesters = []
    start_year = timezone.now().year
    for i in range(4):
        semesters.extend([f'Fall-{start_year + i}', f'Spring-{start_year + i + 1}'])
    
    expected_payments = []
    paid_semesters = paid_payments.values_list('Fee_Type', flat=True)
    
    for i, semester in enumerate(semesters[:8], 1):
        payment = payments.filter(Fee_Type=semester).first()
        expected_payments.append({
            'challan_no': f'{student.Registration_Number}-{i}',
            'semester': semester,
            'amount': per_installment,
            'status': 'PAID' if payment and payment.Fee_Status == 'PAID' else 'UNPAID',
            'voucher_no': payment.Voucher_No if payment and payment.Fee_Status == 'PAID' else '',
            'payment_date': payment.Payment_Date.strftime('%Y-%m-%d') if payment and payment.Fee_Status == 'PAID' and payment.Payment_Date else '',
            'payment_mode': payment.Payment_Mode if payment and payment.Fee_Status == 'PAID' else '-'
        })
    
    context = {
        'student': student,
        'total_fee': total_fee,
        'per_installment': per_installment,
        'paid_installments': f"{paid_installments}/8",
        'remaining_fee': remaining_fee,
        'payments': expected_payments
    }
    
    return render(request, 'payment_management/account_book.html', context)

# ===========================
# Payment Request Views
# ===========================

@login_required
def view_payment_request(request, request_id):
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to view payment request details.")
        return redirect('dashboard')
    
    payment_request = get_object_or_404(PaymentRequest, id=request_id)
    return render(request, 'payment_management/view_payment_request.html', {'payment_request': payment_request})

@login_required
def create_payment_request(request):
    if request.method == 'POST':
        form = PaymentRequestForm(request.POST, request.FILES)
        try:
            student = request.user.student
            if form.is_valid():
                payment_request = form.save(commit=False)
                payment_request.student = student
                payment_request.save()
                messages.success(request, "Payment request submitted successfully. Waiting for admin approval.")
                return redirect('payment_request_history')
            else:
                messages.error(request, "Please correct the errors in the form.")
        except Student.DoesNotExist:
            messages.error(request, "Student profile not found.")
    else:
        form = PaymentRequestForm()

    return render(request, 'payment_management/create_payment_request.html', {'form': form})

@login_required
def payment_request_history(request):
    try:
        student = request.user.student
        payment_requests = PaymentRequest.objects.filter(student=student).order_by('-created_at')
        return render(request, 'payment_management/payment_request_history.html', {'payment_requests': payment_requests})
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect('dashboard')

@login_required
def admin_payment_requests(request):
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to view this page.")
        return redirect('dashboard')
    
    payment_requests = PaymentRequest.objects.filter(status='PENDING').order_by('created_at')
    return render(request, 'payment_management/admin_payment_requests.html', {'payment_requests': payment_requests})

@login_required
def process_payment_request(request, request_id):
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to process payment requests.")
        return redirect('dashboard')
    
    payment_request = get_object_or_404(PaymentRequest, id=request_id)
    
    if request.method == "POST":
        action = request.POST.get('action')
        
        if action == 'approve':
            # Process the approval
            payment_request.status = 'APPROVED'
            payment_request.save()
            
            # Create a new payment record
            Payment.objects.create(
                Student_ID=payment_request.student,
                Fee_Type='Hostel Fee',
                Amount_Paid=payment_request.amount,
                Receipt_Number=payment_request.transaction_id,
                Fee_Status='PAID',
                Payment_Mode=payment_request.payment_mode
            )
            
            messages.success(request, f"Payment request from {payment_request.student.F_Name} {payment_request.student.L_Name} has been approved.")
        
        elif action == 'reject':
            payment_request.status = 'REJECTED'
            payment_request.save()
            messages.warning(request, f"Payment request from {payment_request.student.F_Name} {payment_request.student.L_Name} has been rejected.")
        
        # Use the correct redirect URL
        return redirect('admin_payment_requests')
    
    # If not a POST request, redirect to view the request details
    return redirect('view_payment_request', request_id=request_id)
 




# ===========================
# Visitor Management
# ===========================

@login_required
def request_visitor(request):
    if request.method == 'POST':
        visitor_name = request.POST['visitor_name']
        contact_info = request.POST['contact_info']
        visitor_id_proof = request.POST['cnic']  # Use Visitor_ID_Proof field
        purpose_of_visit = request.POST['purpose_of_visit']
        time_in = request.POST['time_in']
        time_out = request.POST['time_out']

        # Ensure that the visitor is linked to the logged-in student
        visitor = Visitor.objects.create(
            name=visitor_name,
            contact_info=contact_info,
            Visitor_ID_Proof=visitor_id_proof,
            purpose_of_visit=purpose_of_visit,
            student=request.user.student  # Link the visitor to the logged-in student
        )

        # Create the visitor request
        VisitorRequest.objects.create(
            student=request.user.student,
            visitor=visitor,
            time_in=time_in,
            time_out=time_out,
            status="Pending"  # Default status is Pending
        )

        messages.success(request, "Visitor request submitted successfully.")
        return redirect('std_request_history')

    return render(request, 'visitor_management/request_visitor.html')


def update_visitor_request(request, id):
    visitor_request = get_object_or_404(VisitorRequest, id=id)

    if request.method == 'POST':
        status = request.POST.get('status')

        if status not in ['PENDING', 'APPROVED', 'REJECTED']:
            messages.error(request, "Invalid status selected.")
            return redirect('visitor_requests')

        visitor_request.status = status
        visitor_request.save()

        messages.success(request, "Visitor request updated successfully.")
        return redirect('visitor_requests')

    return render(request, 'visitor_management/update_visitor_request.html', {'visitor_request': visitor_request})


# Admin manages visitor requests
@login_required
def admin_manage_visitor_requests(request):
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to view this page.")
        return redirect('home')

    # Get all unread visitor requests first (before marking them as read)
    visitor_requests = VisitorRequest.objects.all()

    if request.method == 'POST':
        request_id = request.POST.get('request_id')
        status = request.POST.get('status')

        try:
            visitor_request = VisitorRequest.objects.get(id=request_id)
            visitor_request.status = status
            visitor_request.save()

            messages.success(request, "Visitor request updated successfully.")
        except VisitorRequest.DoesNotExist:
            messages.error(request, "Visitor request not found.")
    
    # Only mark them as read AFTER processing the request
    VisitorRequest.objects.filter(is_read=False).update(is_read=True)

    return render(request, 'visitor_management/admin_manage_visitor_requests.html', {'visitor_requests': visitor_requests})
  


@login_required
def visitor_requests(request):
    # Get all visitor requests for the logged-in student
    visitor_requests = VisitorRequest.objects.filter(student=request.user.student)
    return render(request, 'visitor_management/visitor_requests.html', {'visitor_requests': visitor_requests})


@login_required
def std_request_history(request):
    # Fetch all visitor requests for the logged-in student
    student = request.user.student
    requests = VisitorRequest.objects.filter(student=student)
    return render(request, 'visitor_management/all_std_request_history.html', {'requests': requests})


# ===========================
# Disciplinary Management
# ===========================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from .models import ShowcaseNotice, StudentShowcaseNotice  # Corrected import
from hostel.models import Student
from .forms import ShowcaseNoticeForm  # Assuming you have a form for ShowcaseNotice

# views.py
# Add these functions to your hostel/views.py file

# Helper function to count unread notices - add this to your existing context processors
def unread_notices_count(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'student'):
            student_unread_showcase_notices = StudentShowcaseNotice.objects.filter(
                student=request.user.student,
                read=False
            ).count()
            return {'student_unread_showcase_notices': student_unread_showcase_notices}
        elif request.user.is_staff:
            unread_showcase_notices = ShowcaseNotice.objects.filter(
                studentshowcasenotice__read=False
            ).distinct().count()
            return {'unread_showcase_notices': unread_showcase_notices}
    return {}

# Admin Views for Showcase Notices
@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_showcase_notices(request):
    notices = ShowcaseNotice.objects.all().order_by('-created_date')
    
    context = {
        'notices': notices,
    }
    return render(request, 'student_showcaseNotice/admin_showcase_notices.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def create_showcase_notice(request):
    if request.method == 'POST':
        form = ShowcaseNoticeForm(request.POST)
        if form.is_valid():
            notice = form.save(commit=False)
            notice.created_by = request.user
            notice.save()
            
            # Add selected students to the notice
            selected_students = form.cleaned_data['students']
            for student in selected_students:
                StudentShowcaseNotice.objects.create(student=student, notice=notice)
            
            messages.success(request, 'Disciplinary notice created successfully.')
            return redirect('admin_showcase_notices')  # Use the URL name, not the path
    else:
        form = ShowcaseNoticeForm()
    
    context = {
        'form': form,
    }
    return render(request, 'student_showcaseNotice/create_showcase_notice.html', context)
@login_required
@user_passes_test(lambda u: u.is_staff)
def view_showcase_notice(request, notice_id):
    notice = get_object_or_404(ShowcaseNotice, id=notice_id)
    student_notices = StudentShowcaseNotice.objects.filter(notice=notice)
    
    context = {
        'notice': notice,
        'student_notices': student_notices,
    }
    return render(request, 'student_showcaseNotice/view_showcase_notice.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def edit_showcase_notice(request, notice_id):
    # Fetch the notice using its ID
    notice = get_object_or_404(ShowcaseNotice, id=notice_id)
    
    if request.method == 'POST':
        # Create the form instance with POST data
        form = ShowcaseNoticeForm(request.POST, instance=notice)
        if form.is_valid():
            # Save the notice
            notice = form.save()
            
            # Get the list of students currently associated with the notice
            # Get the list of students currently associated with the notice
            current_students = set(StudentShowcaseNotice.objects.filter(notice=notice).values_list('student_id', flat=True))

            # Get the list of students selected in the form
            selected_students = set(student.pk for student in form.cleaned_data['students'])

            # Add new students
            for student in form.cleaned_data['students']:
                if student.pk not in current_students:
                    StudentShowcaseNotice.objects.create(student=student, notice=notice)
            # Remove students that were unselected
            StudentShowcaseNotice.objects.filter(notice=notice).exclude(student__in=form.cleaned_data['students']).delete()
            
            messages.success(request, 'Disciplinary notice updated successfully.')
            return redirect('admin_showcase_notices')  # Redirect to the notices list
            
    else:
        form = ShowcaseNoticeForm(instance=notice)
        form.initial['students'] = notice.students.all()  # Pre-populate the students field
    
    context = {
        'form': form,
        'notice': notice,
    }
    return render(request, 'student_showcaseNotice/edit_showcase_notice.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def delete_showcase_notice(request, notice_id):
    notice = get_object_or_404(ShowcaseNotice, id=notice_id)
    
    if request.method == 'POST':
        notice.delete()
        messages.success(request, 'Disciplinary notice deleted successfully.')
        return redirect('admin_showcase_notices')
    
    context = {
        'notice': notice,
    }
    return render(request, 'student_showcaseNotice/delete_showcase_notice.html', context)

# Student Views for Showcase Notices
@login_required
def student_showcase_notices(request):
    student = request.user.student
    student_notices = StudentShowcaseNotice.objects.filter(student=student).order_by('-notice__created_date')
    
    context = {
        'student_notices': student_notices,
    }
    return render(request, 'student_showcaseNotice/student_showcase_notices.html', context)

@login_required
def view_student_showcase_notice(request, notice_id):
    student = request.user.student
    student_notice = get_object_or_404(StudentShowcaseNotice, notice_id=notice_id, student=student)
    
    # Mark notice as read if not already
    if not student_notice.read:
        student_notice.mark_as_read()
    
    context = {
        'student_notice': student_notice,
    }
    return render(request, 'student_showcaseNotice/view_student_showcase_notice.html', context)

# ===========================
# View Mess Membership Status
# ===========================

@login_required
def mess_status(request):
    try:
        # Get the mess membership status for the logged-in student
        mess_membership = MessMembership.objects.get(student=request.user.student)
        
        # Check if the mess membership is approved or still pending
        if mess_membership.approved:
            status_message = "Your application has been approved!"
            status_class = "success"
        elif mess_membership.status == "Rejected":
            status_message = "Your application has been rejected."
            status_class = "danger"
        else:
            status_message = "Your application is still pending. Please wait for admin approval."
            status_class = "warning"

        # Pass the status message and mess membership data to the template
        return render(request, 'mess_management/mess_status.html', {
            'status_message': status_message,
            'status_class': status_class,
            'membership': mess_membership
        })

    except MessMembership.DoesNotExist:
        # If the student has not applied for mess, inform them and redirect to the apply page
        messages.warning(request, "You have not applied for mess yet. Please apply first.")
        return redirect('mess_membership_status')  # Redirect to the membership status page


# ===========================
# Mess Membership and Attendance Management
# ===========================


@login_required
def apply_for_mess(request):
    
    # Check if student already has an application
    try:
        existing_membership = MessMembership.objects.get(student=request.user.student)
        messages.info(request, "You already have a mess membership application.")
        return redirect('mess_membership_status')
    except MessMembership.DoesNotExist:
        pass
    
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')  # Retrieve the end_date from the form
        
        department = request.POST.get('department')
        
        # Validate dates
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            if start_date >= end_date:
                messages.error(request, "End date must be after start date.")
                return render(request, 'mess_management/mess_apply.html')
                
            if start_date < date.today():
                messages.error(request, "Start date cannot be in the past.")
                return render(request, 'mess_management/mess_apply.html')
        except ValueError:
            messages.error(request, "Invalid date format.")
            return render(request, 'mess_management/mess_apply.html')
        
        # Create a new membership application
        try:
            membership = MessMembership(
                student=request.user.student,
                start_date=start_date,
                end_date=end_date,
                department=department,
                is_active=False,
                approved=False,
                status="Pending"
            )
            membership.save()
            messages.success(request, "Mess membership application submitted successfully. Please wait for approval.")
            return redirect('mess_status')
        except Exception as e:
            messages.error(request, f"Error submitting application: {str(e)}")
    
    return render(request, 'mess_management/mess_apply.html')

@login_required
def mess_membership_status(request):
    try:
        membership = MessMembership.objects.get(student=request.user.student)
        
        # Set status class for styling
        if membership.approved:
            status_class = "success"
        elif membership.status == "Rejected":
            status_class = "danger"
        else:
            status_class = "warning"
            
        # Set status message
        if membership.approved and membership.is_active:
            status_message = "Your application has been approved and membership is active!"
        elif membership.approved and not membership.is_active:
            status_message = "Your application has been approved but membership is currently inactive."
        elif membership.status == "Rejected":
            status_message = "Your application has been rejected."
        else:
            status_message = "Your application is still pending approval."
            
        return render(request, 'mess_management/mess_membership_status.html', {
            'membership': membership,
            'status_message': status_message,
            'status_class': status_class
        })
    except MessMembership.DoesNotExist:
        return render(request, 'mess_management/mess_membership_status.html', {
            'membership': None,
            'status_message': "You don't have an active mess membership application.",
            'status_class': "info"
        })
    except Exception as e:
        messages.error(request, f"Error retrieving mess membership status: {str(e)}")
        return redirect('mess_status')  # Replace with an existing view name

@staff_member_required
def admin_mess_management(request):
    # Fetch different categories of memberships
    active_memberships = MessMembership.objects.filter(approved=True, is_active=True).order_by('-date_applied')
    inactive_memberships = MessMembership.objects.filter(approved=True, is_active=False).order_by('-date_applied')
    rejected_memberships = MessMembership.objects.filter(status="Rejected").order_by('-date_applied')
    pending_requests = MessMembership.objects.filter(approved=False, status="Pending").order_by('-date_applied')
    
    # Handle activation of inactive memberships
    if request.method == 'POST':
        request_id = request.POST.get('request_id')
        action = request.POST.get('action')
        
        try:
            mess_request = MessMembership.objects.get(id=request_id)
            
            if action == 'activate':
                mess_request.is_active = True
                mess_request.save()
                messages.success(request, f"Membership for {mess_request.student} activated successfully!")
                
            elif action == 'deactivate':
                mess_request.is_active = False
                mess_request.save()
                messages.success(request, f"Membership for {mess_request.student} deactivated successfully!")
                
        except MessMembership.DoesNotExist:
            messages.error(request, "Membership not found!")
            
        return redirect('admin_mess_management')
    
    context = {
        'active_memberships': active_memberships,
        'inactive_memberships': inactive_memberships,
        'rejected_memberships': rejected_memberships,
        'pending_requests': pending_requests,
        'active_tab': 'active'  # Default active tab
    }
    
    return render(request, 'mess_management/admin_mess_management.html', context)

@staff_member_required
def inactive_memberships(request):
    # Fetch inactive mess memberships (students who have mess membership but not active)
    inactive_memberships = MessMembership.objects.filter(
        approved=True, 
        is_active=False
    ).order_by('-date_applied')

    # Fetch students who are in a hostel but do not have a mess membership (haven't joined the mess)
    students_not_in_mess = Student.objects.filter(
        Room_ID__isnull=False  # Ensure the student is assigned to a room (i.e., in a hostel)
    ).exclude(
        messmembership__isnull=False  # Ensure they have no mess membership
    )
    
    # Combine both querysets by preparing two different lists for rendering in the context
    context = {
        'inactive_memberships': inactive_memberships,
        'students_not_in_mess': students_not_in_mess,
        'active_tab': 'inactive'  # Mark this tab as active
    }

    # Handle activation of inactive memberships
    if request.method == 'POST':
        request_id = request.POST.get('request_id')
        action = request.POST.get('action')

        try:
            mess_request = MessMembership.objects.get(id=request_id)

            if action == 'activate':
                mess_request.is_active = True
                mess_request.save()
                messages.success(request, f"Membership for {mess_request.student} activated successfully!")

        except MessMembership.DoesNotExist:
            messages.error(request, "Membership not found!")

        return redirect('inactive_memberships')

    return render(request, 'mess_management/inactive_memberships.html', context)

@staff_member_required
def rejected_applications(request):
    # Fetch rejected applications
    rejected_memberships = MessMembership.objects.filter(status="Rejected").order_by('-date_applied')
    
    context = {
        'rejected_memberships': rejected_memberships,
        'active_tab': 'rejected'  # Mark this tab as active
    }
    
    return render(request, 'mess_management/rejected_applications.html', context)


@staff_member_required
def mess_request(request):
    # Fetch pending requests
    pending_requests = MessMembership.objects.filter(approved=False, status="Pending").order_by('-date_applied')
    
    if request.method == 'POST':
        request_id = request.POST.get('request_id')
        action = request.POST.get('action')
        
        try:
            mess_request = MessMembership.objects.get(id=request_id)
            
            if action == 'approve':
                mess_request.approved = True
                mess_request.is_active = True
                mess_request.status = "Approved"
                mess_request.save()
                messages.success(request, f"Membership for {mess_request.student} approved successfully!")
            
            elif action == 'reject':
                mess_request.status = "Rejected"
                mess_request.save()
                messages.success(request, f"Membership request for {mess_request.student} rejected successfully!")
            
            elif action == 'deactivate':
                mess_request.is_active = False
                mess_request.save()
                messages.success(request, f"Membership for {mess_request.student} deactivated successfully!")
            
            elif action == 'activate':
                mess_request.is_active = True
                mess_request.save()
                messages.success(request, f"Membership for {mess_request.student} activated successfully!")
        
        except MessMembership.DoesNotExist:
            messages.error(request, "Request not found!")
        
        return redirect('mess_request')
    
    context = {
        'pending_requests': pending_requests,
        'active_tab': 'pending'  # Mark this tab as active
    }
    
    return render(request, 'mess_management/mess_request.html', context)

@staff_member_required
def manage_attendance(request):
    # Filter by date if provided
    date_filter = request.GET.get('date')
    if date_filter:
        # Handle filtering of records by date
        breakfast_records = MessAttendance.objects.filter(meal_time='BF', date=date_filter).order_by('-date')
        lunch_records = MessAttendance.objects.filter(meal_time='LN', date=date_filter).order_by('-date')
        tea_break_records = MessAttendance.objects.filter(meal_time='ET', date=date_filter).order_by('-date')
        dinner_records = MessAttendance.objects.filter(meal_time='DN', date=date_filter).order_by('-date')

        # Set records to None if no records exist for the given date
        if not breakfast_records.exists():
            breakfast_records = None
        if not lunch_records.exists():
            lunch_records = None
        if not tea_break_records.exists():
            tea_break_records = None
        if not dinner_records.exists():
            dinner_records = None
    else:
        # Fetch all attendance records for each meal
        breakfast_records = MessAttendance.objects.filter(meal_time='BF').order_by('-date')
        lunch_records = MessAttendance.objects.filter(meal_time='LN').order_by('-date')
        tea_break_records = MessAttendance.objects.filter(meal_time='ET').order_by('-date')
        dinner_records = MessAttendance.objects.filter(meal_time='DN').order_by('-date')

    context = {
        'breakfast_records': breakfast_records,
        'lunch_records': lunch_records,
        'tea_break_records': tea_break_records,
        'dinner_records': dinner_records
    }
    
    return render(request, 'mess_management/manage_attendance.html', context)

from .models import Fingerprint, MessMembership


@login_required
def mark_attendance(request):
    if request.method == 'POST':
        try:
            # Using our mock implementation
            fingerprint_device = digitalpersona.Device()
            fingerprint_data = fingerprint_device.capture()

            # For development purposes, always find a match
            # In real implementation, you'd compare actual fingerprints
            fingerprint = Fingerprint.objects.filter(student=request.user.student).first()
            
            # If no fingerprint exists for testing, create one with our mock data
            if not fingerprint:
                fingerprint = Fingerprint.objects.create(
                    student=request.user.student,
                    fingerprint_template=b"mock_fingerprint_data_123456789"  # Same as our mock capture
                )

            # Force match for development (remove this condition in production)
            fingerprint_match = True  # For development only
            # Real comparison would be: fingerprint.fingerprint_template == fingerprint_data

            if fingerprint and fingerprint_match:
                meal_code = request.POST.get('meal_code')
                membership = MessMembership.objects.filter(student=request.user.student, approved=True).first()
                
                if membership and membership.is_active:
                    MessAttendance.objects.create(
                        student=request.user.student,
                        date=timezone.now().date(),
                        meal_time=meal_code,
                        is_present=True,
                        price_charged=0  # Set the price as needed
                    )
                    return JsonResponse({'success': True, 'message': 'Attendance marked successfully!'})
                else:
                    return JsonResponse({'success': False, 'message': 'You are not an active member of the mess.'})
            else:
                return JsonResponse({'success': False, 'message': 'Fingerprint verification failed.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})

    return render(request, 'mess_management/mark_attendance.html')

@staff_member_required
def breakfast_attendance(request):
    # Fetch attendance records for Breakfast only
    breakfast_records = MessAttendance.objects.filter(meal_time='BF').order_by('-date')

    context = {
        'breakfast_records': breakfast_records
    }

    return render(request, 'mess_management/breakfast_attendance.html', context)


@staff_member_required
def lunch_attendance(request):
    # Fetch attendance records for Lunch only
    lunch_records = MessAttendance.objects.filter(meal_time='LN').order_by('-date')

    context = {
        'lunch_records': lunch_records
    }

    return render(request, 'mess_management/lunch_attendance.html', context)


@staff_member_required
def tea_break_attendance(request):
    # Fetch attendance records for Tea Break only
    tea_break_records = MessAttendance.objects.filter(meal_time='ET').order_by('-date')

    context = {
        'tea_break_records': tea_break_records
    }

    return render(request, 'mess_management/tea_break_attendance.html', context)


@staff_member_required
def dinner_attendance(request):
    # Fetch attendance records for Dinner only
    dinner_records = MessAttendance.objects.filter(meal_time='DN').order_by('-date')

    context = {
        'dinner_records': dinner_records
    }

    return render(request, 'mess_management/dinner_attendance.html', context)


# ===========================
# Mess Menu Management (Admin)
# ===========================

@staff_member_required
def add_mess_menu(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        meal_time = request.POST.get('meal_time')
        dish_name = request.POST.get('dish_name')
        price_str = request.POST.get('price', '0')

        # Convert price to Decimal (using '0' as a fallback)
        try:
            price = Decimal(price_str.strip() or '0')
        except Exception:
            price = Decimal('0')

        # Parse the date string into a date object
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError as e:
            messages.error(request, f"Invalid date format: {e}")
            return redirect('add_mess_menu')

        # Create and save the menu item (model save() will auto-calculate day, week_number, month, year)
        menu_item = MessMenu(
            date=date_obj,
            meal_time=meal_time,
            dish_name=dish_name,
            price=price
        )
        menu_item.save()
        messages.success(request, "Menu item added successfully!")
        return redirect('view_mess_menu')

    context = {
        'meal_choices': MessMenu.MEAL_CHOICES,
        'day_choices': MessMenu.DAY_CHOICES,
    }
    return render(request, 'mess_management/add_mess_menu.html', context)


@staff_member_required
def add_multiple_menu_items(request):
    if request.method == 'POST':
        try:
            start_date_str = request.POST.get('start_date')
            end_date_str = request.POST.get('end_date')
            days = request.POST.getlist('days')
            meal_time = request.POST.get('meal_time')
            dish_name = request.POST.get('dish_name')
            price_str = request.POST.get('price', '0')
            
            # Convert price to Decimal
            price = Decimal(price_str.strip() or '0')

            # Parse the start and end dates
            start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()

            # Validate date range
            if start_date_obj > end_date_obj:
                messages.error(request, "Start date must be before or equal to end date.")
                return redirect('add_multiple_menu_items')

            # Loop over the date range and add items for selected days
            current_date = start_date_obj
            while current_date <= end_date_obj:
                # Calculate day code (e.g., 'MON', 'TUE', etc.)
                day_code = current_date.strftime('%a').upper()[:3]
                if day_code in days:
                    menu_item = MessMenu(
                        date=current_date,
                        meal_time=meal_time,
                        dish_name=dish_name,
                        price=price
                    )
                    menu_item.save()
                current_date += timedelta(days=1)

            messages.success(request, "Multiple menu items added successfully!")
            return redirect('view_mess_menu')
        except ValueError as e:
            messages.error(request, f"Invalid date format: {e}")
            return redirect('add_multiple_menu_items')

    context = {
        'meal_choices': MessMenu.MEAL_CHOICES,
        'day_choices': MessMenu.DAY_CHOICES,
    }
    return render(request, 'mess_management/add_mess_menu.html', context)


@login_required
def view_mess_menu(request):
    today = timezone.now().date()
    selected_week = request.GET.get('week')
    selected_month = request.GET.get('month')
    selected_year = request.GET.get('year', str(today.year))

    # Handle selected month or week or default to this week
    if selected_month and selected_year:
        year = int(selected_year)
        month_num = datetime.strptime(selected_month, '%B').month
        start_date = date(year, month_num, 1)
        end_date = date(year + 1, 1, 1) - timedelta(days=1) if month_num == 12 else date(year, month_num + 1, 1) - timedelta(days=1)
        title = f"Mess Menu for {selected_month} {selected_year}"
    elif selected_week:
        year, week = map(int, selected_week.split('-W'))
        start_date = datetime.strptime(f'{year}-W{week}-1', '%Y-W%W-%w').date()
        end_date = start_date + timedelta(days=6)
        title = f"Mess Menu for Week {week}, {year}"
    else:
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
        title = "This Week's Mess Menu"

    # Fetch menu items for the selected date range
    menu_items = MessMenu.objects.filter(date__gte=start_date, date__lte=end_date)

    days_of_week = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
    meal_times = ['BF', 'LN', 'ET', 'DN']  # Updated to remove 'MB'

    # Populate the menu for each day and meal time
    structured_menu = {day: {meal: None for meal in meal_times} for day in days_of_week}
    for item in menu_items:
        if item.day in structured_menu and item.meal_time in structured_menu[item.day]:
            structured_menu[item.day][item.meal_time] = item

    current_year = today.year
    available_weeks = [(f"{current_year}-W{week}", f"Week {week}, {current_year}") for week in range(1, 53)]
    available_months = [(month_name, month_name) for month_name in ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']]

    context = {
        'title': title,
        'structured_menu': structured_menu,
        'days_of_week': days_of_week,
        'meal_times': meal_times,
        'meal_names': dict(MessMenu.MEAL_CHOICES),
        'day_names': dict(MessMenu.DAY_CHOICES),
        'available_weeks': available_weeks,
        'available_months': available_months,
        'current_week': f"{today.year}-W{today.isocalendar()[1]}",
        'current_month': today.strftime('%B'),
        'current_year': today.year,
        'years': range(current_year-1, current_year+2),
    }
    
    return render(request, 'mess_management/view_mess_menu.html', context)



@login_required
def mess_attendance(request):
    today = timezone.now().date()
    student = request.user.student
    
    # Get all meal times
    meal_times = [
        {'code': 'BF', 'name': 'Breakfast'},
        {'code': 'LN', 'name': 'Lunch'},
        {'code': 'ET', 'name': 'Evening Tea'},
        {'code': 'DN', 'name': 'Dinner'}
    ]
    all_meal_codes = {meal['code'] for meal in meal_times}
    
    # Check which meal times have already been marked today
    marked_meals = set(MessAttendance.objects.filter(
        student=student,
        date=today
    ).values_list('meal_time', flat=True))
    
    # Process form submission
    if request.method == 'POST':
        for meal_code in all_meal_codes:
            checkbox_name = f'is_present_{meal_code}'
            
            # Only process if this meal hasn't been marked yet
            if meal_code not in marked_meals and checkbox_name in request.POST:
                # Get current meal price from menu (using filter() instead of get())
                menu_item = MessMenu.objects.filter(meal_time=meal_code, date=today).first()  # Use .first() to get the first result
                
                if not menu_item:
                    # Default price if no menu item exists
                    price = 0
                else:
                    price = menu_item.price
                
                # Create attendance record
                MessAttendance.objects.create(
                    student=student,
                    date=today,
                    meal_time=meal_code,
                    is_present=True,
                    price_charged=price
                )
                
        # Redirect to the same page to refresh the data
        return redirect('mess_attendance')
    
    # Calculate remaining meals to be marked
    remaining_meals = all_meal_codes - marked_meals
    
    # Get attendance for the last 30 days
    start_date = today - timezone.timedelta(days=30)
    
    # Get all attendance records in the date range
    attendance_records = MessAttendance.objects.filter(
        student=student,
        date__gte=start_date,
        date__lte=today
    ).order_by('-date')
    
    # Organize attendance by date for display
    attendance_by_date = {}
    
    for record in attendance_records:
        if record.date not in attendance_by_date:
            attendance_by_date[record.date] = {
                'date': record.date,
                'meals': {}
            }
        
        attendance_by_date[record.date]['meals'][record.meal_time] = {
            'is_present': record.is_present,
            'price': record.price_charged
        }
    
    # Convert to list and sort by date
    attendance_history = list(attendance_by_date.values())
    attendance_history.sort(key=lambda x: x['date'], reverse=True)
    
    context = {
        'attendance_history': attendance_history,
        'meal_times': meal_times,
        'marked_meals': marked_meals,
        'remaining_meals': remaining_meals
    }
    
    return render(request, 'mess_management/mess_attendance.html', context)

def generate_daily_bill(student, date):
    """
    Generate or update a daily bill based on attendance for a specific date
    """
    # Get all attendance records for this student on this date where they were present
    attendance_records = MessAttendance.objects.filter(
        student=student,
        date=date,
        is_present=True
    )
    
    # Calculate total amount due
    total_amount = sum(record.price_charged for record in attendance_records)
    
    # Create or update the bill
    bill, created = MessBill.objects.get_or_create(
        student=student,
        bill_date=date,
        defaults={'amount_due': total_amount}
    )
    
    # If bill already existed, update the amount
    if not created:
        bill.amount_due = total_amount
        bill.save()
    
    return bill


def is_admin(user):
    return user.is_staff or user.is_superuser

@login_required
def mess_bill(request):
    student = request.user.student
    bills = MessBill.objects.filter(student=student).order_by('-bill_date')
    
    # Calculate total amount due across all unpaid bills
    total_due = sum(bill.remaining_due() for bill in bills if not bill.paid_status)
    
    # Get attendance details for the current month for a breakdown
    today = timezone.now().date()
    first_day = today.replace(day=1)
    
    attendance_records = MessAttendance.objects.filter(
        student=student,
        date__gte=first_day,
        date__lte=today,
        is_present=True  # Only include meals where student was present
    ).order_by('-date')
    
    # Organize attendance by date
    attendance_by_date = {}
    monthly_total = 0
    
    for record in attendance_records:
        if record.date not in attendance_by_date:
            attendance_by_date[record.date] = {
                'date': record.date,
                'meals': {},
                'daily_total': 0
            }
        
        attendance_by_date[record.date]['meals'][record.meal_time] = {
            'is_present': record.is_present,
            'price': record.price_charged
        }
        
        # Update daily total
        attendance_by_date[record.date]['daily_total'] += record.price_charged
        
        # Update monthly total
        monthly_total += record.price_charged
    
    # Convert to list and sort by date
    attendance_by_date = list(attendance_by_date.values())
    attendance_by_date.sort(key=lambda x: x['date'], reverse=True)
    
    # Get attendance milestone information
    thirty_days_ago = today - timezone.timedelta(days=30)
    attendance_days = MessAttendance.objects.filter(
        student=student,
        date__gte=thirty_days_ago,
        date__lte=today,
        is_present=True
    ).values('date').distinct()
    
    days_count = attendance_days.count()
    days_until_payment = max(0, 10 - days_count)
    
    # Get payment history
    payments = MessPayment.objects.filter(student=student).order_by('-payment_date')
    
    # Get payment requests
    payment_requests = MessPaymentRequest.objects.filter(student=student).order_by('-request_date')
    
    # Check if there is a pending payment request
    has_pending_request = payment_requests.filter(status='PENDING').exists()
    
    context = {
        'bills': bills,
        'total_due': total_due,
        'attendance_by_date': attendance_by_date,
        'monthly_total': monthly_total,
        'attendance_days': days_count,
        'days_until_payment': days_until_payment,
        'payments': payments,
        'payment_requests': payment_requests,
        'has_pending_request': has_pending_request,

        'registration_number': student.Registration_Number
  # Use the correct attribute
    }
    
    return render(request, 'mess_management/mess_bill.html', context)


@login_required
def mess_account_book(request):
    """View for displaying detailed mess account book"""
    student = request.user.student
    
    # Get date range for filtering
    today = timezone.now().date()
    start_date = today.replace(day=1)  # First day of current month
    
    # Allow changing the month/year view
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))
    
    if 1 <= month <= 12 and 2000 <= year <= 2100:
        start_date = timezone.datetime(year, month, 1).date()
        # Find the last day of the selected month
        if month == 12:
            end_date = timezone.datetime(year + 1, 1, 1).date() - timezone.timedelta(days=1)
        else:
            end_date = timezone.datetime(year, month + 1, 1).date() - timezone.timedelta(days=1)
    else:
        # If invalid parameters, default to current month
        month = today.month
        year = today.year
        end_date = today
    
    # Get all attendance for the selected month
    all_attendance = MessAttendance.objects.filter(
        student=student,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date', 'meal_time')
    
    # Summary statistics
    total_meals = all_attendance.filter(is_present=True).count()
    total_cost = all_attendance.filter(is_present=True).aggregate(Sum('price_charged'))['price_charged__sum'] or 0
    
    # Group by date for the calendar view
    attendance_by_date = {}
    
    for record in all_attendance:
        if record.date not in attendance_by_date:
            attendance_by_date[record.date] = {
                'date': record.date,
                'meals': {},
                'daily_total': 0,
                'present_count': 0
            }
        
        attendance_by_date[record.date]['meals'][record.meal_time] = {
            'is_present': record.is_present,
            'price': record.price_charged
        }
        
        if record.is_present:
            attendance_by_date[record.date]['daily_total'] += record.price_charged
            attendance_by_date[record.date]['present_count'] += 1
    
    # Generate calendar data (all days in month)
    calendar_data = []
    current_date = start_date
    
    while current_date <= end_date:
        if current_date in attendance_by_date:
            day_data = attendance_by_date[current_date]
        else:
            day_data = {
                'date': current_date,
                'meals': {},
                'daily_total': 0,
                'present_count': 0
            }
        calendar_data.append(day_data)
        current_date += timezone.timedelta(days=1)
    
    # Get paid/unpaid bills for this month
    bills = MessBill.objects.filter(
        student=student,
        bill_date__gte=start_date,
        bill_date__lte=end_date
    ).order_by('bill_date')
    
    # Payment statistics
    paid_amount = bills.filter(paid_status=True).aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0
    pending_amount = bills.filter(paid_status=False).aggregate(Sum('amount_due'))['amount_due__sum'] or 0
    
    context = {
        'calendar_data': calendar_data,
        'total_meals': total_meals,
        'total_cost': total_cost,
        'bills': bills,
        'paid_amount': paid_amount,
        'pending_amount': pending_amount,
        'student': student,
        'current_month': month,
        'current_year': year,
        'months': [
            {'num': 1, 'name': 'January'},
            {'num': 2, 'name': 'February'},
            {'num': 3, 'name': 'March'},
            {'num': 4, 'name': 'April'},
            {'num': 5, 'name': 'May'},
            {'num': 6, 'name': 'June'},
            {'num': 7, 'name': 'July'},
            {'num': 8, 'name': 'August'},
            {'num': 9, 'name': 'September'},
            {'num': 10, 'name': 'October'},
            {'num': 11, 'name': 'November'},
            {'num': 12, 'name': 'December'},
        ]
    }
    
    return render(request, 'mess_management/mess_account_book.html', context)




@login_required
@user_passes_test(lambda u: u.is_staff)

def search_students(request):
    query = request.GET.get('q', '')
    students = []

    if query and len(query) >= 2:
        # Search by name (first name or last name) or registration number
        students = Student.objects.filter(
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) | 
            Q(registration_number__icontains=query)
        )[:20]  # Limit to 20 results for performance
        
        students = [
            {
                'id': student.id,
                'full_name': f"{student.first_name} {student.last_name}",
                'registration_number': student.registration_number
            }
            for student in students
        ]
    
    return JsonResponse({'students': students})

    query = request.GET.get('q', '')
    students = []
    
    if query and len(query) >= 2:
        # Search by name (first name or last name) or registration number
        students = Student.objects.filter(
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) | 
            Q(registration_number__icontains=query)
        )[:20]  # Limit to 20 results for performance
        
        students = [
            {
                'id': student.id,
                'full_name': f"{student.first_name} {student.last_name}",
                'registration_number': student.registration_number
            }
            for student in students
        ]
    
    return JsonResponse({'students': students})

    """
    Handle AJAX requests to search for students by name or registration number.
    Used by the Select2 widget in the create_showcase_notice form.
    """
    query = request.GET.get('q', '')
    students = []
    
    if query and len(query) >= 2:
        # Search by name (first name or last name) or registration number
        students = Student.objects.filter(
            models.Q(first_name__icontains=query) | 
            models.Q(last_name__icontains=query) | 
            models.Q(registration_number__icontains=query)
        )[:20]  # Limit to 20 results for performance
        
        # Format the results for Select2
        students = [
            {
                'id': student.id,
                'full_name': f"{student.first_name} {student.last_name}",
                'registration_number': student.registration_number
            }
            for student in students
        ]
    
    return JsonResponse({'students': students})


@login_required
def enroll_fingerprint(request):
    if request.method == 'POST':
        try:
            # Use the mock digitalpersona module
            fingerprint_device = digitalpersona.Device()
            fingerprint_data = fingerprint_device.capture()
            
            # Create or update fingerprint record
            fingerprint, created = Fingerprint.objects.update_or_create(
                student=request.user.student,
                defaults={'fingerprint_template': fingerprint_data}
            )
            
            # Link fingerprint to the student's mess membership (if any)
            membership = MessMembership.objects.filter(student=request.user.student).first()
            if membership:
                membership.fingerprint = fingerprint
                membership.save()
                messages.success(request, "Fingerprint successfully enrolled!")
            else:
                messages.error(request, "You must apply for a mess membership first.")
            
            return redirect('mess_membership_status')
        except Exception as e:
            messages.error(request, f"Error enrolling fingerprint: {str(e)}")
    
    return render(request, 'mess_management/enroll_fingerprint.html')
    if request.method == 'POST':
        try:
            # Use the mock digitalpersona module
            fingerprint_device = digitalpersona.Device()
            fingerprint_data = fingerprint_device.capture()
            
            if fingerprint_data:
                # Store the fingerprint data in the database
                fingerprint = Fingerprint.objects.create(
                    student=request.user.student,
                    fingerprint_template=fingerprint_data
                )
                
                # Link fingerprint to the student's mess membership (if any)
                membership = MessMembership.objects.filter(student=request.user.student).first()
                if membership:
                    membership.fingerprint = fingerprint
                    membership.save()
                    messages.success(request, "Fingerprint successfully enrolled!")
                else:
                    messages.error(request, "You must apply for a mess membership first.")
                
                return redirect('mess_membership_status')
            else:
                messages.error(request, "Fingerprint capture failed. Please try again.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
    
    return render(request, 'mess_management/enroll_fingerprint.html')