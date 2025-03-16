from django.db import models
from django.core.validators import RegexValidator
import datetime



class Specialization(models.Model):
    name=models.CharField(max_length=100)

class Doctor(models.Model):
    name = models.CharField(max_length=100, name="name")
    specialization = models.ForeignKey(Specialization,on_delete=models.CASCADE)
    experience = models.IntegerField(name="experience",default=0)
    rating = models.DecimalField(null=True,blank=True,decimal_places=2,max_digits=3)
    pswd=models.CharField(max_length=128)
    fees=models.IntegerField(default=100)
    profile_picture=models.ImageField(upload_to="doctor_profiles/", blank=True, null=True)
    mobile=models.CharField(
        max_length=15, 
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', message="Enter a valid mobile number.")]
    )
    email = models.EmailField(name="email")
    address = models.TextField(name="address")
    

class Patient(models.Model):
    name=models.CharField(max_length=50)
    email=models.EmailField(unique=True)
    mobile=models.CharField(
        max_length=15, 
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', message="Enter a valid mobile number.")]
    )
    dob = models.DateField(null=True)
    pswd=models.CharField(max_length=128)
    address = models.TextField(name="address",null=True)


class Availability(models.Model):
    SLOT_CHOICES=[
        ('Morning', 'Morning'),
        ('Evening', 'Evening'),
        ('Both', 'Both'),
    ]
    doctor=models.ForeignKey(Doctor, on_delete=models.CASCADE)  
    day_of_week=models.CharField(
        max_length=10, 
        default="",
        choices=[
            ('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'),
            ('Thursday', 'Thursday'), ('Friday', 'Friday'), ('Saturday', 'Saturday'),
            ('Sunday', 'Sunday')
        ]
    )

    slot_type=models.CharField(max_length=10, choices=SLOT_CHOICES, default='Both')
    morning_start = models.TimeField(null=True, blank=True)
    morning_end = models.TimeField(null=True, blank=True)
    evening_start = models.TimeField(null=True, blank=True)
    evening_end = models.TimeField(null=True, blank=True)

    def __str__(self):
        details = f"{self.doctor.username} - {self.day_of_week}: "
        if self.slot_type in ['Morning', 'Both']:
            details += f"Morning ({self.morning_start_time} - {self.morning_end_time}) "
        if self.slot_type in ['Evening', 'Both']:
            details += f"Evening ({self.evening_start_time} - {self.evening_end_time})"

        return details


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    doc = models.ForeignKey(Doctor,on_delete=models.DO_NOTHING)
    patient = models.ForeignKey(Patient,on_delete=models.DO_NOTHING)
    appointment_date = models.DateField()
    appointment_time = models.TimeField(default=datetime.time(9, 0))
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

class Review(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="reviews")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    rating = models.DecimalField(max_digits=3, decimal_places=1)
    review_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True) # Stores only once when created
    class Meta:
        unique_together = ('doctor', 'patient')
    def __str__(self):
        return f"{self.patient.username} - {self.doctor.name} ({self.rating})"



class Prescription(models.Model):
    patient = models.ForeignKey(Patient, related_name="prescriptions", on_delete=models.CASCADE)  # Patient ID
    doctor = models.ForeignKey(Doctor, related_name="doctor_prescriptions", on_delete=models.CASCADE)  # Doctor ID
    diagnosis = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    appointment = models.OneToOneField(Appointment,on_delete=models.CASCADE)
    test = models.TextField(null=True)
    remark = models.TextField(null=True)

    def __str__(self):
        return f"Prescription {self.id} by Dr. {self.doctor.username} for {self.patient.username}"

class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, related_name="medications", on_delete=models.CASCADE)
    medicine_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.medicine_name} - {self.dosage}"
