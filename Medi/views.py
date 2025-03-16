import json
from django.http import JsonResponse
from django.shortcuts import render, redirect,get_object_or_404,HttpResponse
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from Medi.models import Doctor,Patient,Appointment,Availability,Specialization,Review
from datetime import datetime
from django.contrib.auth.decorators import login_required
from collections import defaultdict
from datetime import datetime, date, timedelta
from django.core.files.storage import default_storage
import os
from twilio.rest import Client
from django.conf import settings
import time
import PyPDF2
import google.generativeai as genai
from django.core.files.storage import FileSystemStorage
from dotenv import load_dotenv
from google.api_core import exceptions
from PIL import Image
from django.views.decorators.csrf import csrf_exempt
from deep_translator import GoogleTranslator 
import twilio.jwt.access_token as AccessToken
import twilio.jwt.access_token.grants as Grants
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from reportlab.lib.utils import ImageReader




def login(req):
    if req.session.get('user_id'):
        return redirect('home')

    if req.method == 'POST':
        email = req.POST.get('email')
        password = req.POST.get('password')

        try:
            user = Patient.objects.get(email=email)
            if check_password(password, user.pswd):
                req.session['user_id'] = user.id
                # req.session.set_expiry(3600)  # Session expires in 1 hour
                return redirect('home')
            else:
                messages.error(req, 'Incorrect password. Please try again.')
        except Patient.DoesNotExist:
            messages.error(req, 'This email is not registered with us.')

        return redirect('login')

    return render(req, 'login.html')


def doc_login(req):
    if req.session.get('doc_id'):
        return redirect('doctor')
    
    if req.method == 'POST':
        email = req.POST['email']
        password = req.POST['password']
        try:
            doc = Doctor.objects.get(email=email)
            if check_password(password, doc.pswd):
                req.session['doc_id'] = doc.id
                # req.session.set_expiry(3600)  # Session expires in 1 hour
                return redirect('doctor')
            else:
                messages.error(req, 'Incorrect password. Please try again.')
        except Doctor.DoesNotExist:
            messages.error(req, 'This email is not registered with us.')

    return render(req, 'doc_login.html')


def signup(req):
    if req.session.get('user_id'):
        return redirect('home')

    if req.method == 'POST':
        email = req.POST.get('email')
        if Patient.objects.filter(email=email).exists():
            messages.error(req, 'This email is already registered with us.')
            return redirect('signup')


        name = req.POST.get('name')
        password = make_password(req.POST.get('password'))
        mobile = req.POST.get('mobile')
        user = Patient.objects.create(name=name, email=email, pswd=password, mobile=mobile)
        req.session['user_id'] = user.id
        return redirect('home')

    return render(req, 'signup.html')


def doc_signup(req):
    if req.session.get('doc_id'):
        return redirect('doctor')
    specializations = Specialization.objects.all()
    if req.method == 'POST':
        name = req.POST['name']
        email = req.POST['email']
        password = req.POST['password']
        confirm_password = req.POST['confirm_password']
        specialization_id = req.POST['specialization']
        contact_number = req.POST['contact_number']

        if password != confirm_password:
            messages.error(req, "Passwords do not match!")
            return redirect('doc_signup')
        password = make_password(password)
        if Doctor.objects.filter(name=email).exists():
            messages.error(req, "Email is already registered!")
            return redirect('doc_signup')
        
        specialization = Specialization.objects.get(id=specialization_id)
        user = Doctor.objects.create(name=name, email=email, pswd=password, specialization=specialization,mobile=contact_number)
        user.save()
        req.session['doc_id'] = user.id
        messages.success(req, "Account created successfully!")
        return redirect('doctor')

    return render(req, 'doc_signup.html',{'specializations': specializations})


def home(req):
    user_id = req.session.get('user_id')
    try:
        if user_id:
            user = Patient.objects.get(id=user_id)
            return render(req, 'home.html', {'email': user.email, 'name': user.name})
        else:
            return render(req, 'home.html')
    except Patient.DoesNotExist:
        del req.session['user_id']
        return redirect('login')


def doctor(req):
    user_id = req.session.get('doc_id')
    if user_id:
        try:
            user = Doctor.objects.get(id=user_id)
            appointments=Appointment.objects.filter(doc=user,status="confirmed")
            today=date.today()
            sessions=0
            for a in appointments:
                if a.appointment_date==today:
                    sessions+=1
            return render(req, 'doctor.html', {'doc': user,'sessions':sessions})
        except Doctor.DoesNotExist:
            del req.session['doc_id']
            return redirect('doc_login')
    else:
        return redirect('doc_login')


def logout(req):
    if req.session.get('user_id'):
        del req.session['user_id']
    return redirect('home')

def doc_logout(req):
    if req.session.get('doc_id'):
        del req.session['doc_id']
    return redirect('doc_login')


def report(req):
    if req.session.get('user_id'):
            
        return render(req,'report.html')
    return redirect('login')






load_dotenv()

# Configure the Gemini AI model
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("Gemini API key not found. Please set the GEMINI_API_KEY environment variable.")

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

def analyze_medical_report(content, content_type):
    prompt = "Analyze this medical report concisely. Provide key findings, diagnoses, and diet recommendations in tabular form:"
    
    for attempt in range(MAX_RETRIES):
        try:
            if content_type == "image":
                response = model.generate_content([prompt, content])
            else:  # text
                response = model.generate_content(f"{prompt}\n\n{content}")
            
            return response.text
        except exceptions.GoogleAPIError as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                return fallback_analysis(content, content_type)

def fallback_analysis(content, content_type):
    if content_type == "image":
        return "Unable to analyze the image due to API issues. Please try again later."
    else:  # text
        word_count = len(content.split())
        return f"""
        Fallback Analysis:
        - Document Type: Text-based medical report
        - Word Count: {word_count} words
        - Recommendation: Please consult a medical professional.
        """

def extract_text_from_pdf(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def medical_report_analysis(req):
    if req.method == "POST" and req.FILES.get('file'):
        uploaded_file = req.FILES['file']
        fs = FileSystemStorage()
        file_path = fs.save(uploaded_file.name, uploaded_file)
        file_url = fs.url(file_path)
        analysis = "No analysis available."
        print(analysis)
        if uploaded_file.name.endswith('.pdf'):
            with open(fs.path(file_path), 'rb') as pdf_file:
                pdf_text = extract_text_from_pdf(pdf_file)
                analysis = analyze_medical_report(pdf_text, "text")
        elif uploaded_file.name.lower().endswith(('png', 'jpg', 'jpeg')):
            image = Image.open(fs.path(file_path))
            analysis = analyze_medical_report(image, "image")
        print(analysis)
        # Remove the uploaded file after processing
        os.remove(fs.path(file_path))

        return render(req, "report.html", {
            'file_url': file_url,
            'analysis': analysis
        })

    return render(req, "report.html")






def locator(req):
    if req.session.get('user_id'):
        return render(req,'locator.html')
    return redirect('login')


def profile(req):
    if req.session.get("doc_id"):
        doc_id = req.session.get("doc_id")
        doc = get_object_or_404(Doctor, id=doc_id)

        if req.method == "POST":
            n = req.POST.get("name")
            s = req.POST.get("specialization")
            e = req.POST.get("experience")
            num = req.POST.get("phone")
            mail = req.POST.get("email")
            add = req.POST.get("address")
            fees = req.POST.get("fees")
            sp = get_object_or_404(Specialization, id=s)

            if "profilePicture" in req.FILES:
                uploaded_pic = req.FILES["profilePicture"]

                # Delete the old profile picture if it exists
                if doc.profile_picture:
                    if default_storage.exists(doc.profile_picture.path):
                        default_storage.delete(doc.profile_picture.path)

                # Save the new profile picture
                file_path = default_storage.save(f"doctor_profiles/doc_{doc.id}.jpg", uploaded_pic)
                doc.profile_picture = file_path

            # Update doctor details
            doc.name = n
            doc.specialization = sp
            doc.experience = e
            doc.mobile = num
            doc.email = mail
            doc.address = add
            doc.fees = fees
            doc.save()

            return redirect("doctor")

        specializations = Specialization.objects.all()
        return render(req, "profile.html", {"doc": doc, "specializations": specializations, "sp": doc.specialization.id if doc else None})

    return redirect("doc_login")



def availability(req):
    doc_id = req.session.get('doc_id')
    doctor=Doctor.objects.get(id=doc_id)
    availability=Availability.objects.filter(doctor=doctor).order_by('day_of_week')
    grouped_availability = defaultdict(list)
    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for slot in availability:
        grouped_availability[slot.day_of_week].append(slot)

    sorted_availability = sorted(grouped_availability.items(), key=lambda x: days_order.index(x[0]))
    if req.method == 'POST':
        if req.session.get('doc_id'):
            doc_id = req.session.get('doc_id')
        else:
            messages.error(req, "You must be logged in to set availability.")
            return redirect('doctor')
        doctor=Doctor.objects.get(id=doc_id)
        day_of_week = req.POST.get('day_of_week')
        slot_type = req.POST.get('slot_type')

        defaults = {}

        if slot_type == 'Morning':
            defaults['morning_start'] = req.POST.get('morning_start')
            defaults['morning_end'] = req.POST.get('morning_end')
            defaults['evening_start'] = None
            defaults['evening_end'] = None
        elif slot_type == 'Evening':
            defaults['morning_start'] = None
            defaults['morning_end'] = None
            defaults['evening_start'] = req.POST.get('evening_start')
            defaults['evening_end'] = req.POST.get('evening_end')
        elif slot_type == 'Both':
            defaults['morning_start'] = req.POST.get('morning_start')
            defaults['morning_end'] = req.POST.get('morning_end')
            defaults['evening_start'] = req.POST.get('evening_start')
            defaults['evening_end'] = req.POST.get('evening_end')

        defaults['slot_type']=slot_type
        availability, created = Availability.objects.update_or_create(
            doctor=doctor,
            day_of_week=day_of_week,
            defaults=defaults
        )
        

        messages.success(req, "Availability successfully saved!")
        return redirect('availability')

    return render(req, 'availability.html',{'availability_slots':sorted_availability})


def pat_appointments(req):
    if req.session.get('user_id'):
        today = date.today()
        current_time = datetime.now().strftime("%I:%M %p")
        pat_id=req.session.get('user_id')
        patient=Patient.objects.get(id=pat_id)
        my_appointments=Appointment.objects.filter(patient=patient)
        appointments_dict = {
        "pending": [],
        "confirmed": [],
        "completed": [],
        "cancelled": []
        }

        for appointment in my_appointments:
            appointments_dict[appointment.status].append({
            "id":appointment.id,
            "date": appointment.appointment_date.strftime("%Y-%m-%d"),
            "time": appointment.appointment_time.strftime("%I:%M %p"),
            "doctor": f"Dr. {appointment.doc.name}",
            "status": appointment.status
        })
        # print(appointments_dict)
        return render(req, 'pat_appointment.html', {'appointments': json.dumps(appointments_dict),'today':today,'current_time':current_time,'doc_id':appointment.doc.id,'pat_id':appointment.patient.id})
    return redirect('login')




@csrf_exempt  # Temporarily disable CSRF (not recommended for production)
def cancel_appointment(req):
    if req.method == "POST":
        try:
            data = json.loads(req.body.decode("utf-8"))  # Ensure decoding
            appointment_id = data.get("appointment_id")  # Extract appointment ID
            if not appointment_id:
                return JsonResponse({"error": "Appointment ID is required"}, status=400)

            try:
                appointment = Appointment.objects.get(id=appointment_id)
                appointment.status = "cancelled"
                appointment.save()
                
                return JsonResponse({"success": True, "message": "Appointment cancelled successfully!","updated_appointment": {
                        "id": appointment.id,
                        "date": appointment.appointment_date.strftime("%Y-%m-%d"),
                        "time":appointment.appointment_time.strftime("%I:%M %p"),
                        "doctor": f"Dr. {appointment.doc.name}",
                        "status": appointment.status
                    }})
            except Appointment.DoesNotExist:
                return JsonResponse({"error": "Appointment not found"}, status=404)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid req method"}, status=405)



translator = GoogleTranslator(source="auto", target="hi")  # ✅ Auto-detects input language, translates to Hindi


def chatbot_page(request):
    return render(request, "chat.html")
# Initialize Gemini AI
genai.configure(api_key=settings.GEMINI_API_KEY)

@csrf_exempt
def chatbot_response(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_input = data.get("message", "").strip().lower()  # Convert input to lowercase
            user_language = data.get("language", "en").lower()  # Default to English
            # Convert full language names to language codes
            language_map = {
                "english": "en",
                "hindi": "hi",
                "french": "fr",
                "spanish": "es",
                "german": "de",
                "telugu": "te",
                "tamil": "ta",
                "bengali": "bn"
            }
            user_language = language_map.get(user_language, user_language)

            if not user_input:
                return JsonResponse({"error": "Message cannot be empty"}, status=400)

            # Define common greetings
            greetings = ["hi", "hello", "hey", "namaste", "hola", "bonjour", "hii"]
            if user_input in greetings:
                response_text = "Hello! How can I assist you today?"  # Default greeting response

                # Translate greeting response if needed
                if user_language != "en":
                    translator = GoogleTranslator(source="en", target=user_language)
                    response_text = translator.translate(response_text)

                return JsonResponse({"response": response_text, "language": user_language})

            # Restrict bot to only health-related queries
            health_keywords = [
                "health", "diet", "exercise", "body", "multivitamins", "disease",
                "food", "nutrition", "medicine", "workout", "lifestyle", "fitness",
                "symptoms", "doctor", "hospital", "wellness", "treatment"
            ]
            if not any(keyword in user_input for keyword in health_keywords):
                restricted_response = "I'm specialize in providing information related to health, wellness, and the human body.Let me know if you need any assistance regarding that."
                
                # Translate restriction message if needed
                if user_language != "en":
                    translator = GoogleTranslator(source="en", target=user_language)
                    restricted_response = translator.translate(restricted_response)

                return JsonResponse({"response": restricted_response, "language": user_language})

            # Convert Hinglish to Hindi for better AI understanding
            translator = GoogleTranslator(source="auto", target="hi")
            hindi_text = translator.translate(user_input)

            # Get response from Gemini AI
            model = genai.GenerativeModel("gemini-1.5-pro-latest")
            response = model.generate_content(
                f"Provide a structured response in bullet points for: {hindi_text}"
            )
            bot_response = response.text

            # Ensure response is formatted in bullet points
            bot_response = "• " + bot_response.replace("\n", "\n• ")
            # Translate response if needed
            if user_language != "hi":
                translator = GoogleTranslator(source="hi", target=user_language)
                bot_response = translator.translate(bot_response)
            return JsonResponse({"response": bot_response, "language": user_language})

        except Exception as e:
            print("Error:", str(e))
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Only POST requests are allowed."}, status=405)



def appointment_page(req):
    if(req.session.get('user_id')):
        doctors = Doctor.objects.all()
        
        today = date.today()
        upcoming_days = [
            {
                "date": (today + timedelta(days=i)).strftime('%Y-%m-%d'),
                "day": (today + timedelta(days=i)).strftime('%A')
            }
            for i in range(3)
        ]  # Generate next three days with both date and day name
        specializations=Specialization.objects.all()
        doctor_availability = get_doctor_availability(upcoming_days)
        # print(doctor_availability)
        return render(req, 'book_appointment.html', {
            'doctors': doctors,
            'specializations':specializations,
            'upcoming_days': upcoming_days,
            'doctor_availability': json.dumps(doctor_availability)
        })
    else:
        return redirect('login')

def get_doctor_availability(dates):
    """Fetch availability of doctors for given dates."""
    doctor_availability = {}

    for doctor in Doctor.objects.all():
        doctor_availability[doctor.id] = {}

        for day_info in dates:
            day_of_week = day_info["day"]  # Get weekday name
            date_str = day_info["date"]
            is_today = date_str == date.today().strftime('%Y-%m-%d')

            availability_slots = Availability.objects.filter(doctor=doctor, day_of_week=day_of_week)

            morning_slots = []
            evening_slots = []

            for slot in availability_slots:
                if slot.slot_type in ["Morning", "Both"]:
                    morning_slots.extend(generate_time_slots(slot.morning_start, slot.morning_end, is_today))
                if slot.slot_type in ["Evening", "Both"]:
                    evening_slots.extend(generate_time_slots(slot.evening_start, slot.evening_end, is_today))

            doctor_availability[doctor.id][date_str] = {
                "morning_slots": morning_slots,
                "evening_slots": evening_slots
            }

    return doctor_availability

def generate_time_slots(start_time, end_time, is_today):
    """Generate 15-minute interval slots between start_time and end_time, skipping past slots for today."""
    slots = []
    if start_time and end_time:
        current_time = datetime.combine(date.today(), start_time)
        end_datetime = datetime.combine(date.today(), end_time)
        now = datetime.now()

        while current_time < end_datetime:
            if not (is_today and current_time < now):  # Skip past slots for today
                slots.append(current_time.time().strftime('%I:%M %p'))
            current_time += timedelta(minutes=15)
    return slots


# Twilio credentials from settings.py
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TwILIO_PHONE_NUMBER")  # Your Twilio number

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)



def book_appointment(req):
    if req.method == "POST":
        doc_id = req.POST.get("doc_id", "")
        slot_time = req.POST.get("slot_time", "")
        slot_date = req.POST.get("selectedDate", "")
        print(f"Doctor ID: {doc_id}, Slot Time: {slot_time}, Slot Date: {slot_date}")
        print(req.session.get('user_id'))
        pat=Patient.objects.get(id=req.session.get('user_id'))
        doc=Doctor.objects.get(id=doc_id)
        print(doc.mobile)
        slot_time_24hr = datetime.strptime(slot_time, '%I:%M %p').strftime('%H:%M')
        appointments=Appointment.objects.filter(doc=doc,appointment_date=slot_date,appointment_time=slot_time_24hr)
        print(doc.mobile)
        if(len(appointments)==2):
            # messages.error(req, "Slot already booked.")
            return JsonResponse({'status': 'success', 'message': 'Appointment already booked!'})
        
        appointment=Appointment(patient=pat,doc=doc,appointment_date=slot_date,appointment_time=slot_time_24hr)
        appointment.save()
        print(doc.mobile)
        doctor_message = f"New Appointment req!\nDate: {slot_date}\Time: {slot_time}\nPatient: {pat.name}."
        # send_sms(doc.mobile, doctor_message)
        return JsonResponse({'status': 'success', 'message': 'Appointment booked successfully!'})


def doc_appointments(req):
    doc_id=req.session.get('doc_id')
    today = date.today()
    current_time = datetime.now().strftime("%I:%M %p")
    doc=Doctor.objects.get(id=doc_id)
    appointments=Appointment.objects.filter(doc=doc)
    appointments_dict = {
        "pending": [],
        "confirmed": [],
        "completed": [],
        "cancelled": []
        }

    for appointment in appointments:
        appointments_dict[appointment.status].append({
        "id":appointment.id,
        "date": appointment.appointment_date.strftime("%Y-%m-%d"),
        "time": appointment.appointment_time.strftime("%I:%M %p"),
        "patient": f"{appointment.patient.name}",
        "status": appointment.status
        })
    print(appointment.patient.id)
    return render(req, 'doc_appointments.html', {'appointments': json.dumps(appointments_dict),'today':today,'current_time':current_time,'doc_id':doc_id,'pat_id':appointment.patient.id})





# Function to send SMS
def send_sms(to, message):
    client.messages.create(
        body=message,
        from_=TWILIO_PHONE_NUMBER,
        to=to
    )

def confirm(req):
    if(req.session.get('doc_id')):
        id = req.GET.get('id')
        ap=Appointment.objects.get(id=id)
        ap.status='confirmed'
        ap.save()
        patient_message = f"Your appointment is confirmed!\nDon't worry, wait till your chance. ✅"
        print(ap.patient.mobile)
        # send_sms(ap.patient.mobile, patient_message)

        # return JsonResponse({'message': 'Appointment confirmed, patient has been notified.'})
        return redirect('doc_appointments')



def doctor_availability(req, doctor_id):
    doctor = Doctor.objects.get(id=doctor_id)
    availability = Availability.objects.filter(doctor=doctor).order_by('day_of_week')

    grouped_availability = defaultdict(list)
    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for slot in availability:
        grouped_availability[slot.day_of_week].append(slot)

    sorted_availability = sorted(grouped_availability.items(), key=lambda x: days_order.index(x[0]))
    datee=[]
    today=date.today()
    next=today+timedelta(days=1)
    next2=today+timedelta(days=2)
    datee.append(today,next,next2)
    return render(req, "doctor_availability.html", {"doctor": doctor, "availability": sorted_availability, 'datee':datee})


def video(req):
    did = req.GET.get('did')
    pid = req.GET.get('pid')
    role = req.GET.get('role')
    id = req.GET.get('id')
    return render(req,'video.html',{"did":did,"pid":pid,"role":role,"id":id})




load_dotenv()  # Load environment variables from .env file

# Get Twilio credentials
TWILIO_ACCOUNT_SID_V = os.getenv("TWILIO_ACCOUNT_SID_V")
TWILIO_API_KEY_SID_V = os.getenv("TWILIO_API_KEY_SID_V")
TWILIO_API_KEY_SECRET_V = os.getenv("TWILIO_API_KEY_SECRET_V")

def generate_video_token(req):
    """Generate a Twilio Video Access Token"""
    identity = req.GET.get("identity", "guest")  # Unique user identifier

    # Create an Access Token
    token = AccessToken.AccessToken(
        TWILIO_ACCOUNT_SID_V,
        TWILIO_API_KEY_SID_V,
        TWILIO_API_KEY_SECRET_V,
        identity=identity
    )

    # Grant access to Twilio Video
    video_grant = Grants.VideoGrant()
    token.add_grant(video_grant)

    return JsonResponse({"token": token.to_jwt()})



# import json
# from django.http import JsonResponse
# from twilio.jwt.access_token import AccessToken
# from twilio.jwt.access_token.grants import VideoGrant
# from django.conf import settings

# def generate_twilio_token(req):
#     identity = req.GET.get("identity", "guest_user")  # Get identity from the req

#     account_sid = settings.TWILIO_ACCOUNT_SID
#     api_key_sid = settings.TWILIO_API_KEY_SID
#     api_key_secret = settings.TWILIO_API_KEY_SECRET

#     token = AccessToken(account_sid, api_key_sid, api_key_secret, identity=identity)
#     video_grant = VideoGrant()
#     token.add_grant(video_grant)


# from .models import Prescription, PrescriptionItem
# from io import BytesIO
# from reportlab.pdfgen import canvas
# import requests

# # Fetch medications from OpenFDA API
# def get_medications(req):
#     api_url = "https://api.fda.gov/drug/label.json?limit=100"
#     try:
#         response = requests.get(api_url)
#         data = response.json()
#         medications = [entry["openfda"]["brand_name"][0] for entry in data["results"] if "openfda" in entry and "brand_name" in entry["openfda"]]
#         return JsonResponse({"medications": medications})
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)

# # Save prescription
# def create_prescription(req):
#     if req.method == "POST":
#         patient_id = req.POST.get("patient_id")
#         doctor_id = req.user.id  # Assuming doctor is logged in
#         diagnosis = req.POST.get("diagnosis")
#         medicines = req.POST.getlist("medicines[]")  
#         dosages = req.POST.getlist("dosages[]")

#         patient = get_object_or_404(Patient, id=patient_id)
#         doctor = get_object_or_404(Doctor, id=doctor_id)

#         prescription = Prescription.objects.create(
#             patient=patient,
#             doctor=doctor,
#             diagnosis=diagnosis,
#         )

#         for med, dose in zip(medicines, dosages):
#             PrescriptionItem.objects.create(prescription=prescription, medicine_name=med, dosage=dose)

#         return JsonResponse({"success": True, "prescription_id": prescription.id})

#     return render(req, "create_prescription.html")

# # Generate PDF
# def download_prescription(req, prescription_id):
#     prescription = get_object_or_404(Prescription, id=prescription_id)
#     medications = prescription.medications.all()

#     response = HttpResponse(content_type='application/pdf')
#     response['Content-Disposition'] = f'attachment; filename="prescription_{prescription.id}.pdf"'

#     buffer = BytesIO()
#     p = canvas.Canvas(buffer)

#     p.setFont("Helvetica", 16)
#     p.drawString(100, 800, "Prescription")

#     p.setFont("Helvetica", 12)
#     p.drawString(100, 770, f"Patient ID: {prescription.patient.id} ({prescription.patient.username})")
#     p.drawString(100, 750, f"Doctor ID: {prescription.doctor.id} (Dr. {prescription.doctor.username})")
#     p.drawString(100, 730, f"Date: {prescription.date.strftime('%Y-%m-%d %H:%M')}")

#     p.setFont("Helvetica-Bold", 12)
#     p.drawString(100, 700, "Diagnosis:")
#     p.setFont("Helvetica", 12)
#     p.drawString(100, 680, prescription.diagnosis)

#     p.setFont("Helvetica-Bold", 12)
#     p.drawString(100, 650, "Medications:")

#     y_position = 630
#     p.setFont("Helvetica", 12)
#     for med in medications:
#         p.drawString(100, y_position, f"{med.medicine_name} - {med.dosage}")
#         y_position -= 20

#     p.showPage()
#     p.save()

#     buffer.seek(0)
#     response.write(buffer.read())
#     return response


from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from .models import Prescription, PrescriptionItem, Patient, Doctor
from io import BytesIO
from reportlab.pdfgen import canvas
import requests

# Fetch medications from OpenFDA API
def get_medications(req):
    api_url = "https://api.fda.gov/drug/label.json?limit=100"
    try:
        response = requests.get(api_url)
        data = response.json()
        medications = [
            entry["openfda"]["brand_name"][0]
            for entry in data["results"]
            if "openfda" in entry and "brand_name" in entry["openfda"]
        ]
        return JsonResponse({"medications": medications})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# Save prescription
def create_prescription(request):
    if request.method == "POST":
        patient_id = request.POST.get("patient_id")
        id = request.POST.get("id")
        ap=Appointment.objects.get(id=id)
        ap.status="completed"
        ap.save()
        diagnosis = request.POST.get("diagnosis")
        test = request.POST.get("test")
        remark = request.POST.get("remark")

        medicines = request.POST.getlist("medicines[]")  
        print(patient_id," ",diagnosis," ",medicines)
        dosages = request.POST.getlist("dosages[]")
        print(dosages)
        patient = get_object_or_404(Patient, id=patient_id)
        doctor = get_object_or_404(Doctor, id=request.session.get('doc_id'))  # Assuming doctor is logged in
        prescription = Prescription.objects.create(
            patient=patient,
            doctor=doctor,
            diagnosis=diagnosis,
            appointment=ap,
            test=test,
            remark=remark
        )
        for med, dose in zip(medicines, dosages):
            PrescriptionItem.objects.create(prescription=prescription, medicine_name=med, dosage=dose)

        return JsonResponse({"success": True, "prescription_id": prescription.id})

    return render(request, "create_prescription.html")

# Generate PDF
def download_prescription(request):
    id = request.GET.get('id')
    prescription = Prescription.objects.get(appointment=id)
    medications = prescription.medications.all()
    recommended_tests = prescription.test  # Assuming this is a text field or ManyToMany
    additional_remarks = prescription.remark  # Assuming this is a text field

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="prescription_{prescription.id}.pdf"'

    buffer = BytesIO()
    p = canvas.Canvas(buffer)

    # Load MediReach logo
    # logo_path = os.path.join(settings.STATICFILES_DIRS[0], "img", "mediReach (1).png")  # Update path
    # if os.path.exists(logo_path):
    logo = ImageReader("Medi/static/img/medi.jpg")
    p.drawImage(logo, 50, 780, width=100, height=50, preserveAspectRatio=True)

    # Title
    p.setFont("Helvetica-Bold", 20)
    p.drawString(180, 800, "MediReach Prescription")

    # Patient & Doctor Details
    p.setFont("Helvetica", 12)
    p.drawString(100, 760, f"Date: {prescription.date.strftime('%Y-%m-%d %H:%M')}")
    p.drawString(100, 740, f"Patient: {prescription.patient.name} (ID: {prescription.patient.id})")
    p.drawString(100, 720, f"Doctor: Dr. {prescription.doctor.name} (ID: {prescription.doctor.id})")
    p.drawString(100, 700, f"Doctor Email: {prescription.doctor.email}")

    # Diagnosis
    p.setFont("Helvetica-Bold", 12)
    p.drawString(100, 670, "Diagnosis:")
    p.setFont("Helvetica", 12)
    p.drawString(100, 650, prescription.diagnosis)

    # Medications Section
    p.setFont("Helvetica-Bold", 12)
    p.drawString(100, 620, "Medications & Dosage:")

    y_position = 600
    p.setFont("Helvetica", 12)
    for med in medications:
        p.drawString(100, y_position, f"{med.medicine_name} - {med.dosage}")
        y_position -= 20

    # Recommended Tests
    if recommended_tests:
        p.setFont("Helvetica-Bold", 12)
        p.drawString(100, y_position - 20, "Recommended Tests:")
        p.setFont("Helvetica", 12)
        p.drawString(100, y_position - 40, recommended_tests)
        y_position -= 60

    # Additional Remarks
    if additional_remarks:
        p.setFont("Helvetica-Bold", 12)
        p.drawString(100, y_position - 20, "Additional Remarks:")
        p.setFont("Helvetica", 12)
        p.drawString(100, y_position - 40, additional_remarks)

    p.showPage()
    p.save()

    buffer.seek(0)
    response.write(buffer.read())
    buffer.close()
    return response






class SubmitReview(APIView):
    def post(self, req):
        doctor = get_object_or_404(Doctor, id=req.data.get("did"))
        rating = req.data.get("rating")
        review_text = req.data.get("review_text", "")
        user_id = req.session.get('user_id')  # Fetch user_id from session
        if not user_id:
            return Response({"error": "User is not authenticated"}, status=400)

        patient = Patient.objects.get(id=user_id)  # Use id explicitly
        if not rating:
            return Response({"error": "Rating is required"}, status=status.HTTP_400_BAD_req)
        review, created = Review.objects.update_or_create(
            doctor=doctor,
            patient=patient,
            defaults={"rating": rating, "review_text": review_text}
        )
        return Response({"message": "Review submitted successfully!"})
