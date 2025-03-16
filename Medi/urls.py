from django.urls import path
from Medi.views import *
from django.conf.urls.static import static

urlpatterns = [
    path('login/', login, name='login'),
    path('doc_login/', doc_login, name='doc_login'),
    path('signup/', signup, name='signup'),
    path('doc_signup/', doc_signup, name='doc_signup'),
    path('', home, name='home'),
    path('profile/',profile,name="profile"),
    path('doctor/',doctor,name="doctor"),
    path('availability/',availability,name="availability"),
    path('report/', report, name='report'),
    path('analyze/', medical_report_analysis, name='analyze_report'),
    path('locator/', locator, name='locator'),
    path('logout/', logout, name='logout'),
    path('doc_logout/', doc_logout, name='doc_logout'),
    path('appointment_page/', appointment_page, name='appointment_page'),
    path('book_appointment/', book_appointment, name='book_appointment'),
    path('availability/<int:doctor_id>/', doctor_availability, name='doctor_availability'),
    path("get-token/", generate_video_token, name="get_video_token"),
    # path('get-token/', generate_twilio_token, name='get-token'),
    path("video/", video, name="video"),
    path("doc_appointments/", doc_appointments, name="doc_appointments"),
    path("pat_appointments/", pat_appointments, name="pat_appointments"),
    path('confirm/',confirm,name='confirm'),
    path('cancel-appointment/',cancel_appointment),
    path('SubmitReview/',SubmitReview.as_view(),name='SubmitReview'),
    path('chatbot/', chatbot_page, name='chatbot'),
    path('chatbot_response/', chatbot_response, name='chatbot_response'),
    # path("report/", upload_report, name="upload_report"),
    # path('create/', create_prescription, name='create_prescription'),
    # path('download/<int:prescription_id>/', download_prescription, name='download_prescription'),
    # path('api/medications/', get_medications, name='get_medications'),

    path('get_medications/', get_medications, name='get_medications'),
    path('create_prescription/', create_prescription, name='create_prescription'),
    path('download_prescription/', download_prescription, name='download_prescription'),
]

    
