from django.urls import path
from . import views

urlpatterns = [
    # User Authentication URLs
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.user_register, name='register'),

    # Student Management URLs
    path('students/add/', views.add_student, name='add_student'),
    path('students/', views.list_students, name='list_students'),
    path('students/edit/<int:student_id>/', views.edit_student, name='edit_student'),
    path('students/delete/<int:student_id>/', views.delete_student, name='delete_student'),
    path('student/<int:student_id>/', views.view_student, name='view_student'),

    # Hostel Management URLs
    path('hostels/add/', views.add_hostel, name='add_hostel'),
    path('hostels/', views.list_hostels, name='list_hostels'),
    
    path('hostels/edit/<int:hostel_id>/', views.edit_hostel, name='edit_hostel'),
    path('hostels/delete/<int:hostel_id>/', views.delete_hostel, name='delete_hostel'),
    path('assign_hostel/', views.assign_hostel, name='assign_hostel'),  # Adjust the view name as needed

    # Room Management URLs
    path('rooms/', views.list_rooms, name='list_rooms'),
    path('rooms/add/', views.add_room, name='add_room'),
    path('rooms/edit/<int:room_id>/', views.edit_room, name='edit_room'),
    path('rooms/delete/<int:room_id>/', views.delete_room, name='delete_room'),

    # Student Dashboard and Profile
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/profile/', views.std_profile, name='std_profile'),

    # Admin Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Notice Board URLs (Admin and Student)
    path('admin/notices/', views.list_of_notices, name='list_of_notices'),
    path('admin/notice/add/', views.add_notice, name='add_notice'),
    path('admin/notice/<int:notice_id>/', views.view_notice, name='view_notice'),
    path('admin/notice/<int:notice_id>/edit/', views.edit_notice, name='edit_notice'),
    path('admin/notice/<int:notice_id>/delete/', views.delete_notice, name='delete_notice'),
    path('notices/', views.student_notices, name='student_notices'),
    path('notice/<int:notice_id>/', views.student_view_notice, name='student_view_notice'),

    # Complaints Management
    path('submit_complaint/', views.submit_complaint, name='submit_complaint'),
    path('complaints/', views.list_complaints, name='list_complaints'),
    path('complaint/<int:complaint_id>/', views.view_complaint, name='view_complaint'),

     path('fee-management/', views.fee_management, name='fee_management'),
    path('payment-request/create/', views.create_payment_request, name='create_payment_request'),
    path('payment-request/history/', views.payment_request_history, name='payment_request_history'),
    path('payment-request/<int:request_id>/', views.view_payment_request, name='view_payment_request'),
    
    # Admin payment routes
    path('admin/payment-requests/', views.admin_payment_requests, name='admin_payment_requests'),
    path('admin/payment-request/<int:request_id>/process/', views.process_payment_request, name='process_payment_request'),
    
    # Payment management
    path('add-payment/', views.add_payment, name='add_payment'),
    path('account-book/', views.account_book, name='account_book'),
    path('account-book/<int:student_id>/', views.account_book, name='account_book_with_id'),

    # Visitor Management URLs
    path('request_visitor/', views.request_visitor, name='request_visitor'),
    path('visitor_requests/', views.visitor_requests, name='visitor_requests'),
    path('update-visitor-request/<int:id>/', views.update_visitor_request, name='update_visitor_request'),
    path('student/request_history/', views.std_request_history, name='std_request_history'),
    path('admin/manage_visitor_requests/', views.admin_manage_visitor_requests, name='admin_manage_visitor_requests'),

    # Mess Management URLs
    path('apply-mess/', views.apply_for_mess, name='apply_for_mess'),
    path('mess-menu/', views.view_mess_menu, name='mess_menu'),
    path('mess-membership-status/', views.mess_membership_status, name='mess_membership_status'),
    # Other URL patterns
    path('mess-request/', views.mess_request, name='mess_request'),
    path('mess/attendance/', views.mess_attendance, name='mess_attendance'),

    path('mess/bill/', views.mess_bill, name='mess_bill'),
    path('mess-status/', views.mess_status, name='mess_status'),
    path('admin/mess-management/', views.admin_mess_management, name='admin_mess_management'),
    path('add-mess-menu/', views.add_mess_menu, name='add_mess_menu'),
    path('view-mess-menu/', views.view_mess_menu, name='view_mess_menu'),
    path('add-multiple-menu-items/', views.add_multiple_menu_items, name='add_multiple_menu_items'),
    path('mess-attendance/', views.manage_attendance, name='manage_attendance'),
    
    path('enroll-fingerprint/', views.enroll_fingerprint, name='enroll_fingerprint'),
    path('mark-attendance/', views.mark_attendance, name='mark_attendance'),
    
    path('mess/admin/inactive/', views.inactive_memberships, name='inactive_memberships'),
    path('mess/admin/rejected/', views.rejected_applications, name='rejected_applications'),
   
    
    path('breakfast-attendance/', views.breakfast_attendance, name='breakfast_attendance'),
    path('lunch-attendance/', views.lunch_attendance, name='lunch_attendance'),
    path('tea-break-attendance/', views.tea_break_attendance, name='tea_break_attendance'),
    path('dinner-attendance/', views.dinner_attendance, name='dinner_attendance'),
    # Admin Showcase Notice URLs
   
    # Student Showcase Notice URLs
    # Add these URL patterns to your hostel/urls.py file

    path('admin/showcase-notices/', views.admin_showcase_notices, name='admin_showcase_notices'),
    path('search/students/', views.search_students, name='search_students'),  # Search Students for Admin
    path('admin/showcase-notices/<int:notice_id>/', views.view_showcase_notice, name='view_showcase_notice'),
    path('admin/showcase-notices/<int:notice_id>/edit/', views.edit_showcase_notice, name='edit_showcase_notice'),
    path('admin/showcase-notices/<int:notice_id>/delete/', views.delete_showcase_notice, name='delete_showcase_notice'),
    path('admin/showcase-notices/create/', views.create_showcase_notice, name='create_showcase_notice'),

    path('student/showcase-notices/', views.student_showcase_notices, name='student_showcase_notices'),
    path('student/showcase-notices/<int:notice_id>/', views.view_student_showcase_notice, name='view_student_showcase_notice'),

    
]
