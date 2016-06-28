'''
Manages how data will be stored and interacted with
Author: Gleb Promokhov
'''

from __future__ import unicode_literals

from datetime import timedelta, datetime
from django.db import models
from django.forms import CharField, Form, PasswordInput, ModelForm, DateInput, DateTimeInput, ValidationError, ModelChoiceField, DateField, FileField
from django.forms.widgets import CheckboxSelectMultiple
from django.http import Http404
from django.contrib.auth.models import User
from .customData import BLOOD_TYPES, EYE_COLORS
from datetime import date
import datetime as dt
import re
import json

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~HOSPITAL
class Hospital(models.Model):
	'''
	Defines the model for the Hospital
	'''

	name = models.CharField(max_length=200)
	address = models.CharField(max_length=200)

	#printing a hosptial will print it's name
	def __str__(self):
		return self.name

	# list hosptial alphbettiaclly
	class Meta:
		ordering = ('name',)

class HospitalForm(ModelForm):
	'''
	Defines a form for the Hospital model
	'''

	class Meta:
		model = Hospital
		fields = '__all__'
		labels = { 'name':'Name *', 'address':'Address *',}
	
	#make sure there are no duplicate hospital names
	def clean_name(self):
		n = self.cleaned_data['name']
		if(Hospital.objects.filter(name=n)):	
			raise ValidationError("A hospital with that name already exsists!")
		return n

	#make sure there are no duplicate hospital addresses
	def clean_address(self):
		a = self.cleaned_data['address']
		if(Hospital.objects.filter(address=a)):	
			raise ValidationError("A hospital with that adress already exsists!")
		return a 

class HospitalSelectionForm(Form):
	'''
	Form to be used in the hospital selection page
	Expects a 'start' keyword, for what the inital hospital in the form will be
	Expects a 'fromset' keyword, for the options of hospitals
	'''

	def __init__(self, *args, **kwargs):
		s = kwargs.pop('start')
		f = kwargs.pop('fromset')
		super(HospitalSelectionForm, self).__init__(*args, **kwargs)
		self.fields['hospital'].initial = s
		self.fields['hospital'].queryset = f

	hospital = ModelChoiceField(queryset=Hospital.objects.all(),empty_label=None)

class HospitalTransferForm(Form):
	'''
	Form to be used in hospital transfer page
	Expects a 'start' keyword, for what the inital hospital in the form will be
	'''
	def __init__(self, *args, **kwargs):
		s = kwargs.pop('start')
		self.patient = kwargs.pop('patient')
		super(HospitalTransferForm, self).__init__(*args, **kwargs)
		self.fields['hospital'].initial = s

	hospital = ModelChoiceField(queryset=Hospital.objects.all(),empty_label=None)
	
	#make sure that the patient is only transfered to a hospital that there
	#primaryCareProvider works at too
	def clean(self):
		h = self.cleaned_data['hospital']
		p = self.patient
		if(h not in p.primaryCareProvider.hospitals.all()):
			self.add_error('hospital', "This patients doctor does not work at selected hospital!")
		return self.cleaned_data


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~HEALTHNETUSER
class HealthNetUserManager(models.Manager):
	'''
	Manager for HealthNetUsers
	Provides this addional method in HealthNetUser.objects
	'''
	#in situations where you need to get profile, but dont' know what it is, use this 
	#looks kinda stupid, but Django doesn't actually support inheritence/polymorphisim that well
	#call this function by: HealthNetUser.objects.getChild(<username>)
	def getChild(self, username):
		if (Administrator.objects.filter(username=username)):
			return Administrator.objects.get(username=username)
		elif (Patient.objects.filter(username=username)):
			return Patient.objects.get(username=username)
		elif (Doctor.objects.filter(username=username)):
			return Doctor.objects.get(username=username)
		elif (Nurse.objects.filter(username=username)):
			return Nurse.objects.get(username=username)	
		else:
			#raise Http404("Error getting profile infornmation. Raised by HealthNetUser.objects.getChild()") #is this correct? 
			return None #this is correct

class HealthNetUser(models.Model):
		'''
		Base class for all users in HealthNet
		'''

		# link this model to the Django User object
		# will user user when profile delted
		djangoUser = models.OneToOneField(User, on_delete=models.CASCADE) #required

		# which hospital(s) is this user related too
		hospitals = models.ManyToManyField(Hospital, related_name='hospitals') #required

		#which Hospital is this user curently in?
		currentHospital = models.ForeignKey(Hospital, on_delete=models.PROTECT,related_name='currentHospital')

		# how this HealthNetUser will be primarily accessed
		username = models.CharField(max_length=200) #required

		#HealthNetUser needs a custom manager to maange it's children
		objects = HealthNetUserManager()

		firstName = models.CharField(max_length=200)  # required
		middleName = models.CharField(max_length=200, blank=True)
		lastName = models.CharField(max_length=200)  # required
		age = models.IntegerField(blank=True, null=True)
		birthDate = models.DateField(null=True, blank=True)
		address = models.CharField(max_length=200, blank=True)
		email = models.EmailField(max_length=200, blank=True)
		phoneNumber = models.CharField(max_length=200, blank=True)

		#for stats date range thing
		date = models.DateField(auto_now_add=True)

		def fullName(self):
			if(self.middleName):
				return self.firstName + " " + self.middleName + " " + self.lastName
			else:
				return self.firstName + " " + self.lastName

		def getNum(self):
			if(isinstance(self, Administrator)):
				return 4
			if(isinstance(self, Doctor)):
				return 3
			if(isinstance(self, Nurse)):
				return 2
			if(isinstance(self, Patient)):
				return 1
			return 0

		# this should never be directly accessed
		def __str__(self):
				return self.fullName()

		# declare HealthNetUser object as abstract
		# a HealthNetUser object should never be instantiated
		#class Meta:
				#abstract = True #TODO: is this required? 

#used for User (django authenticate), not profiel form
class HealthNetUserForm(ModelForm):
	'''
	Form for a HealthNetUser
	'''

	class Meta:
		model = User
		widgets = { 'password': PasswordInput(),}
		fields = ('username', 'password',)
		labels = {'username': 'Username *', 'password': 'Password *'}

	#make sure there are no duplicate usernames
	#make sure there are not '@'s in the username, this breaks things
	def clean_username(self):
		u = self.cleaned_data['username']
		if('@' in u):
			raise ValidationError("Invalid charecter @")
		if(HealthNetUser.objects.getChild(u)):	
			raise ValidationError("A user with that username already exsists!")
		return u

	#make sure the phone number is in the correct format
	def clean_phoneNumber(self):
		p = self.cleaned_data['phoneNumber']
		if(p):
			if(re.match("^\d{3}-\d{3}-\d{4}$", p) == None):
				raise ValidationError("Invalid phone number")
		return p

	#make sure the birhtdate is in the correct format
	#django actually does this for us
	def clean_birthDate(self):
		b = self.cleaned_data['birthDate']
		if(b == None):
			return b


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~DOCTOR
class Doctor(HealthNetUser):
		'''
		Model for a Doctor user
		'''
	
		#get their blank form
		def getInitialForm(self, i):
				p = Doctor.objects.get(username=i)
				return DoctorForm(instance=p)

		#get their POSTed info form
		def getUpdateForm(self, request, i):
				p = Doctor.objects.get(username=i)
				return DoctorForm(request.POST, instance=p)

		class Meta:
				ordering = ('lastName',)

		def __str__(self):
				return self.fullName()

class DoctorForm(HealthNetUserForm):
	'''
	Form for doctor creation
	'''

	#sets the Hospitals to a checkbox select, instead of the weird 
	#multiple select thing
	def __init__(self, *args, **kwargs):
		super(DoctorForm, self).__init__(*args, **kwargs)
		self.fields['hospitals'].widget = CheckboxSelectMultiple()
		self.fields['hospitals'].queryset = Hospital.objects.all()
	
	class Meta:
		model = Doctor
		fields = ('__all__')
		widgets = {'birthDate': DateInput(attrs={'class': 'birthDatePicker'}),}
		exclude = ('djangoUser','username','age','currentHospital')
		labels = { 'username' : 'Username *', 'hospitals': 'Hospitals *',
			'firstName': 'First Name *', 'middleName':'Middle Name', 'lastName':'Last Name *', 
			'birthDate':'Birth Date', 'phoneNumber':'Phone Number (xxx-xxx-xxxx)', }

	#make sure the doctor is registered with at least one hospital
	def clean_hospitals(self):
		h = self.cleaned_data['hospitals']
		if(h == None):
			raise ValidationError("Please select at least one hospital")
		return h

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~NURSE
class Nurse(HealthNetUser):
		'''
		Model for a Nurse user
		'''

		# Doctors * <-> * Nurses 
		doctors = models.ManyToManyField(
		Doctor,
		related_name="nurseDoctor",
		related_query_name="nurseDoctors",
		)

		#get their blank form
		def getInitialForm(self, i):
				p = Nurse.objects.get(username=i)
				return NurseForm(instance=p)

		#get their POSTed info form
		def getUpdateForm(self, request, i):
				p = Nurse.objects.get(username=i)
				return NurseForm(request.POST, instance=p)

		class Meta:
				ordering = ('lastName',)

		def __str__(self):
				return self.fullName()

class NurseForm(HealthNetUserForm):
	'''
	Form for a Nurse user
	'''

	#makes the doctor select a list of checkboxses
	#instead of the weird multiple select thing
	def __init__(self, *args, **kwargs):
		super(NurseForm, self).__init__(*args, **kwargs)
		self.fields['doctors'].widget = CheckboxSelectMultiple()
		self.fields['doctors'].queryset = Doctor.objects.all()
	
	class Meta:
		model = Nurse
		fields = ('currentHospital','doctors','firstName', 'middleName', 'lastName', 'birthDate', 'address', 'email', 'phoneNumber',)
		widgets = {'birthDate': DateInput(attrs={'class': 'birthDatePicker'}),}
		exclude = ('djangoUser','username', 'age', 'hospitals')
		labels = { 'username' : 'Username *', 'password':'Password *', 'doctors':'Doctors *', 'currentHospital':'Hospital *',
			'firstName': 'First Name *', 'middleName':'Middle Name', 'lastName':'Last Name *', 
			'birthDate':'Birth Date', 'phoneNumber':'Phone Number (xxx-xxx-xxxx)', }

	#make sure that all of the doctors selected work at the selected hospital
	def clean(self):
		h = self.cleaned_data['currentHospital']
		docs = self.cleaned_data['doctors'].all()
		for d in docs:
			if h not in d.hospitals.all():
				self.add_error('currentHospital',"One or more of the selected doctors is not in that hospital")
		return self.cleaned_data

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ADMINISTRATOR
class Administrator(HealthNetUser):
	'''
	Model definition for an Administrator
	'''
		
	#get their blank form
	def getInitialForm(self, i):
		p = Administrator.objects.get(username=i)
		return AdministratorForm(instance=p)
	
	#get their POSTed info form
	def getUpdateForm(self, request, i):
		p = Administrator.objects.get(username=i)
		return AdministratorForm(request.POST, instance=p)

	class Meta:
		ordering = ('lastName',)

	def __str__(self):
		return self.fullName()

class AdministratorForm(HealthNetUserForm):
	'''
	Form for an Administrator
	'''

	#make the hospital selection a list of checkboxses
	#instead of the wierd multiple selection thing
	def __init__(self, *args, **kwargs):
		super(AdministratorForm, self).__init__(*args, **kwargs)
		self.fields['hospitals'].widget = CheckboxSelectMultiple()
		self.fields['hospitals'].queryset = Hospital.objects.all()

	class Meta:
		model = Administrator
		fields = ('__all__')
		widgets = {'birthDate': DateInput(attrs={'class': 'birthDatePicker'}),}
		exclude = ('djangoUser', 'username','currentHospital','age',)

		labels = { 'username' : 'Username *', 'hospitals': 'Hospitals *',  
			'firstName': 'First Name *', 'middleName':'Middle Name', 'lastName':'Last Name *', 
			'birthDate':'Birth Date', 'phoneNumber':'Phone Number (xxx-xxx-xxxx)', }

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~PATIENT
class Patient(HealthNetUser):
		'''	
		Model for a Patient User	
		'''
		healthNumber = models.CharField(max_length = 12) #required
		# EYE_COLORS from customData.py
		eyeColor = models.CharField(max_length=8, choices=EYE_COLORS, default="BROWN", blank=True)
		# BLOOD_TYPES from customData.py
		bloodType = models.CharField(max_length=3, choices=BLOOD_TYPES, default="O+", blank=True)
		height = models.IntegerField(blank=True, null=True)
		weight = models.IntegerField(blank=True, null=True)
		emergencyContact = models.TextField(max_length=600, blank=True)

		# Doctors 1 <-> * Patient
		primaryCareProvider = models.ForeignKey(
		'Doctor',
		on_delete=models.PROTECT,
		related_name="patientsDoctors",
		related_query_name="patientsDoctor",
		)

		# Nurses * <-> * Patient
		# I don't think this field is acutally every used
		nurses = models.ManyToManyField(
		Nurse,
		related_name="nurses",
		related_query_name="nurse",
		blank=True)

		#get their blank form
		def getInitialForm(self, i):
				p = Patient.objects.get(username=i)
				return PatientForm(instance=p)

		#get their form with POSTed data
		def getUpdateForm(self, request, i, h):
				p = Patient.objects.get(username=i)
				return PatientForm(request.POST, instance=p, curHealthNumber=h)

		def __str__(self):
				return self.fullName()


class PatientForm(ModelForm):
	'''
	Form for Patient user
	'''

	#get rid of blank choice in hospital and doctor selection fields
	def __init__(self, *args, **kwargs):
		self.curHealthNumber = kwargs.pop('curHealthNumber', None)
		super(PatientForm, self).__init__(*args, **kwargs)
		self.fields['primaryCareProvider'].empty_label = None
		self.fields['primaryCareProvider'].widget.choices = self.fields['primaryCareProvider'].choices
		self.fields['currentHospital'].empty_label = None
		self.fields['currentHospital'].widget.choices = self.fields['currentHospital'].choices

	class Meta:
		model = Patient
		fields = ('healthNumber', 'primaryCareProvider', 'currentHospital', 'firstName', 'middleName', 'lastName', 'age', 'birthDate', 'height', 'weight',
			'address', 'email', 'phoneNumber', 'emergencyContact', 'eyeColor', 'bloodType')
		widgets = {'birthDate': DateTimeInput(attrs={'class': 'birthDatePicker'}),}
		exclude = ('djangoUser', 'username', 'age', 'hospitals')
		labels = { 'healthNumber':'Your health insurance number, should be 12 alpha-numeric charecters, the first one is a letter *',
			'primaryCareProvider':'Doctor *', 'currentHospital':'Hospital *',
			'firstName': 'First Name *', 'middleName':'Middle Name', 'lastName':'Last Name *', 
			'birthDate':'Birth Date', 'phoneNumber':'Phone Number (xxx-xxx-xxxx)', 'emergencyContact':'Emergency Contact', 
			'eyeColor':'Eye Color', 'bloodType':'Blood Type', 'weight':"Weight (in lbs)", 'height':"Height (total in inches)"}

	#make sure the health insurance number is in the correct format
	#make suret there are no duplicate health insurance numbers
	def clean_healthNumber(self):
		h = self.cleaned_data['healthNumber']
		if(re.match("^[a-zA-Z][a-zA-Z0-9]{11}$", h) == None):
			raise ValidationError("Invalid health insurance number")
		if(h != self.curHealthNumber):
			if (Patient.objects.filter(healthNumber=h)):
				raise ValidationError("A user with that health insurance number already exsists!")
		return h

	#make sure that the chosen doctor actually works in chose hospital
	def clean(self):
		d = self.cleaned_data['primaryCareProvider']
		h = self.cleaned_data['currentHospital']
		if(d == None):
			self.add_error('primaryCareProvider', "Please select a doctor")
		if(h == None):
			self.add_error('currentHospital', "Please select a hospital")
		if(h and d):
			d = d.hospitals.all()
			if(h not in d):
				self.add_error('primaryCareProvider', "Chosen doctor does not in work chosen hospital!")
		return self.cleaned_data

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~HEALTHTEST
class HealthTest(models.Model):
	'''
	Model for a HealthTest (Test)
	'''
	title = models.CharField(max_length=200)
	date = models.DateField()
	desc = models.TextField(max_length=600)
	results = models.TextField(max_length=600)
	image = models.FileField(upload_to="testimages/", null=True, blank=True)
	released = models.BooleanField()

	# Doctor 1 <-> 1 HealthTest
	doctor = models.ForeignKey(
	'Doctor',
	on_delete=models.CASCADE,
	related_name="doctorTested",
	blank=True,
	)

	# Patient 1 <-> 1 HealthTest
	patient = models.ForeignKey(
	'Patient',
	on_delete=models.CASCADE,
	related_name="patientTested",
	)

class HealthTestFormForAdmin(ModelForm):
	'''
	HealthTest form for Admins
	'''

	#can select any doctor and any patient in their current hospital
	def setQuerysets(self, a):
		self.fields['patient'].queryset = Patient.objects.filter(currentHospital=a.currentHospital)
		self.fields['doctor'].queryset = Doctor.objects.filter(hospitals=a.currentHospital)

	class Meta:
		model = HealthTest
		fields = ('__all__')
		widgets = {
			'date': DateTimeInput(attrs={'class': 'dateInput'}),
		}
		labels = { 'title':'Title *', 'date':'Date *', 'desc':'Description *', 'patient':'Patient *', 'released':'Released', 'doctor':'Doctor *', 'results':'Results *',}

	#make sure date is in the correct format
	#django does this for us
	def clean_date(self):
		return self.cleaned_data['date']

	#provide a clean method for the image upload so it works
	def clean_image(self):
		return self.cleaned_data['image']

	#make sure the selected doctor and patient are related
	def clean(self):
		d = self.cleaned_data['doctor']
		p = self.cleaned_data['patient']
		if(p.primaryCareProvider != d):
			self.add_error('doctor', 'Chosen doctor is not the patients doctor!')
		return self.cleaned_data

class HealthTestFormForDoctor(ModelForm):
	'''
	HealthTest form for a Doctor user
	'''
		
	#they can only select their patients in their current hospital
	def setQuerysets(self, a):
		self.fields['patient'].queryset = Patient.objects.filter(primaryCareProvider=a,currentHospital=a.currentHospital)
	class Meta:
		model = HealthTest
		fields = ('__all__')
		widgets = {
			'date': DateTimeInput(attrs={'class': 'dateInput'}),
		}
		exclude = ('doctor',)
		labels = { 'title':'Title *', 'date':'Date *', 'desc':'Description *', 'patient':'Patient *', 'released':'Released', 'doctor':'Doctor *'}

	#make sure data is in the correct format
	#django does this for us
	def clean_date(self):
		return self.cleaned_data['date']

class HealthTestFormForNurse(ModelForm):
	'''
	HealthTest form for a Nurse user
	'''

	#they can only select their doctor's patients in their current hospital
	#they can only select their doctors
	def setQuerysets(self, a):
		self.fields['patient'].queryset = Patient.objects.filter(primaryCareProvider__in=a.doctors.all(), currentHospital=a.currentHospital)
		self.fields['doctor'].queryset = a.doctors.all()

	class Meta:
		model = HealthTest
		fields = ('__all__')
		widgets = {
			'date': DateTimeInput(attrs={'class': 'dateInput'}),
		}
		exclude = ('released',)
		labels = { 'title':'Title *', 'date':'Date *', 'desc':'Description *', 'patient':'Patient *', 'released':'Released', 'doctor':'Doctor *'}

	#make sure the date is in the correct format
	#django does this for us
	def clean_date(self):
		return self.cleaned_data['date']

	#make sure the selected patient and doctor are related
	#this is redundant
	def clean(self):
		d = self.cleaned_data['doctor']
		p = self.cleaned_data['patient']
		if(p.primaryCareProvider != d):
			self.add_error('doctor', 'Chosen doctor is not the patients doctor!')
		return self.cleaned_data

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~PRESCRIPTION
class Prescription(models.Model):
	'''
	Model for a Prescription object
	'''

	name = models.CharField(max_length=200)
	dosage = models.CharField(max_length=200)
	notes = models.TextField(max_length=600)

	# Doctor 1 <-> 1 Prescription
	doctor = models.ForeignKey(
		'Doctor',
		on_delete=models.CASCADE,
		related_name="doctorPrescribed",
	)

	# Patient 1 <-> Prescription
	prescribedTo = models.ForeignKey(
		'Patient',
		on_delete=models.CASCADE,
		related_name="patientPerscriptions",
		related_query_name="patientPerscription",
	)

	def __str__(self):
		return self.name

	# keep in alphabetical order
	class Meta:
		ordering = ('name',)

        
class PrescriptionForm(ModelForm):
	'''
	Form for a Prescription object, for doctors
	'''

	#can only select the doctor's patients in their current hospital
	def __init__(self, *args, **kwargs):
		d = kwargs.pop('doctor', None)
		super(PrescriptionForm, self).__init__(*args, **kwargs)
		self.fields['prescribedTo'].queryset = Patient.objects.filter(primaryCareProvider=d)

	class Meta:
		model = Prescription
		fields = ('__all__')
		exclude = ('doctor',)
		labels = { 'name':'Name *', 'dosage':'Dosage *', 'notes':'Notes', 'prescribedTo':'Prescribed To *' }

class PrescriptionFormPlus(ModelForm):
	'''
	Form for a Prescription object, for nurses and admins
	'''
	#if a nurse keyword provided, can only select nurse's doctors and their doctor's patients in currentHospital
	#if an admin keyword provided, can only select doctors and patients in their currentHospital
	def __init__(self, *args, **kwargs):
		n = kwargs.pop('nurse', None)
		a = kwargs.pop('admin', None)
		super(PrescriptionFormPlus, self).__init__(*args, **kwargs)
		if(n):
			self.fields['doctor'].queryset = n.doctors.all()
			self.fields['prescribedTo'].queryset = Patient.objects.filter(primaryCareProvider__in=n.doctors.all())
		if(a):
			self.fields['doctor'].queryset = Doctor.objects.filter(hospitals=a.currentHospital).all()
			self.fields['prescribedTo'].queryset = Patient.objects.filter(currentHospital=a.currentHospital).all()

	class Meta:
		model = Prescription
		fields = ('__all__')
		labels = { 'name':'Name *', 'dosage':'Dosage *', 'notes':'Notes', 'prescribedTo':'Prescribed To *' }

	#make sure the selected doctor and patient are related
	def clean(self):
		d = self.cleaned_data['doctor']
		p = self.cleaned_data['prescribedTo']
		if(p.primaryCareProvider != d):
			self.add_errors('doctor', 'Chosen doctor is not the patients doctor!')
		return self.cleaned_data

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~APPOINTMENT
class AppointmentManager(models.Manager):
		'''
		Manager for Appointment objects
		Provides these addional methods under Appointment.objects
		'''

		#get upcoming appointments relevant to given user
		#meaning all appointments with startTimes after datetime.now()
		def getUpcomingAppointments(self, username):
				 #admins should never have appointments TODO right?
				if (Administrator.objects.filter(username=username)):
						return None				
				#if patient, get their appointments
				elif (Patient.objects.filter(username=username)):
						p = Patient.objects.get(username=username)
						return Appointment.objects.filter(patient=p, dateAndTimeStart__gt=datetime.now()).order_by('dateAndTimeStart')

				#if doctor, get all appointments with them listed as the doctor
				elif (Doctor.objects.filter(username=username)):
						d = Doctor.objects.get(username=username)
						return Appointment.objects.filter(doctor=d, dateAndTimeStart__gt=datetime.now()).order_by('dateAndTimeStart')


				#if nurse, get all of their doctor's appointments
				elif (Nurse.objects.filter(username=username)):
						apps = []
						n = Nurse.objects.get(username=username)
						for d in n.doctors.all():
							apps += Appointment.objects.getUpcomingAppointments(d.username).order_by('dateAndTimeStart')
						return apps
				else:
						raise Http404("Error getting appointments") #is this correct? 

		#get all of a users appointments
		def getAllAppointments(self, username):
				 #admins should never have appointments TODO right?
				if (Administrator.objects.filter(username=username)):
						return None				
				#if patient, get their appointments
				elif (Patient.objects.filter(username=username)):
						p = Patient.objects.get(username=username)
						return Appointment.objects.filter(patient=p);

				#if doctor, get all appointments with them listed as the doctor
				elif (Doctor.objects.filter(username=username)):
						d = Doctor.objects.get(username=username)
						return Appointment.objects.filter(doctor=d);

				#if nurse, get all of their doctor's appointments
				elif (Nurse.objects.filter(username=username)):
						apps = []
						n = Nurse.objects.get(username=username)
						for d in n.doctors.all():
							apps += Appointment.objects.getAllAppointments(d.username)
						return apps
				else:
						raise Http404("Error getting appointments") #is this correct? 

class Appointment(models.Model):
		'''
		Model for an Appointment object
		'''
		dateAndTimeStart = models.DateTimeField(null=True)
		dateAndTimeEnd = models.DateTimeField(null=True)
		duration = models.DurationField()
		location = models.CharField(max_length=200, blank=True)
		desc = models.TextField(max_length=600)

		# Patient 1 <-> 1 Appointment
		patient = models.ForeignKey(
				'Patient',
				on_delete=models.CASCADE,
				null=True, 
				blank=True,
				default=None,
				)

		# Doctor 1 <-> 1 Appointment
		doctor = models.ForeignKey(
				'Doctor',
				on_delete=models.CASCADE,
				default=None,
				)

		objects = AppointmentManager()

		def __str__(self):
				return self.desc

#Time for the worst code I've written for this project
class AppointmentFormForAdministrator(ModelForm):
	'''
	Form for an Appointment object, for Admins
	'''
	def __init__(self, *args, **kwargs):
		self.appID = kwargs.pop('appID', None)
		super(AppointmentFormForAdministrator, self).__init__(*args, **kwargs)

	class Meta:
		model = Appointment
		fields = ('__all__')
		exclude = ('dateAndTimeEnd',)
		widgets = {
			'dateAndTimeStart': DateTimeInput(attrs={'class': 'startInput'}),
			'duration': DateTimeInput(attrs={'class': 'durationInput'}),
		}
		labels = { 'dateAndTimeStart':'When? *', 'duration':'How long? *', 'location':'Where?', 'desc':'For what? *', 
					'patient':'Patient','doctor':'Doctor *', }

	def clean(self):
		p = self.cleaned_data.get('patient', None)
		pu = None
		if(p != None):
			pu = p.username
		do = self.cleaned_data.get('doctor', None)
		du = None
		if(do != None):
			du = do.username
		s = self.cleaned_data.get('dateAndTimeStart', None)
		d = self.cleaned_data.get('duration', None)

		#check that doctor is selected, if patient selected check doctor and patient relevevance
		if(du == None):
			self.add_error('doctor', 'Please select a doctor.')
		if(du and pu):
			if(p.primaryCareProvider.username != du):
				self.add_error('patient', "Chosen doctor is not the patient's doctor")

		#check duration format (django does this for us)
		if(s == None):
			return self.cleaned_data

		#check duration format
		if(d == None):
			return self.cleaned_data
	
		#check that appointment isn't made in past
		if(s != None):
			sn = s.replace(tzinfo=None)
			if( sn < datetime.now()):
				self.add_error('dateAndTimeStart', "Can't make an appointment in the past")
	
		#check that this appointment doesn't conflict with any of the doctor's appointments
		if(du != None and s != None):
			for a in Appointment.objects.getAllAppointments(du):
				#if we are updating an appointment, we want to skip over the appointment we are updating, otherwise is error as a conflict with itself
				if a.pk != self.appID:
					if s <= a.dateAndTimeStart <= s+d:
						self.add_error('dateAndTimeStart', "That doctor already has an appointment during that time.")

		#check that this appointment doesn't conflict with any of the patient's appointments
		if(pu != None and s != None):
			for a in Appointment.objects.getAllAppointments(pu):
				#if we are updating an appointment, we want to skip over the appointment we are updating, otherwise is error as a conflict with itself
				if a.pk != self.appID:
					if s <= a.dateAndTimeStart <= s+d:
						self.add_error('dateAndTimeStart', "That patient already has an appointment during that time.")

		return self.cleaned_data

class AppointmentFormForPatient(ModelForm):
	'''
	Form for an Appointment object, for Patients
	'''

	def __init__(self, *args, **kwargs):
		self.patientUsername = kwargs.pop('patient')
		self.doctorUsername = kwargs.pop('doctor')
		self.appID = kwargs.pop('appID', None)
		super(AppointmentFormForPatient, self).__init__(*args, **kwargs)

	class Meta:
		model = Appointment
		fields = ('__all__')
		widgets = {'dateAndTimeStart': DateTimeInput(attrs={'class': 'startInput'}),}
		exclude = ('duration', 'location', 'patient', 'doctor','dateAndTimeEnd' )
		labels = { 'dateAndTimeStart':'When? *', 'duration':'How long? *', 'location':'Where?', 'desc':'For what? *', }

	def clean(self):
		pu = self.patientUsername
		du = self.doctorUsername
		s = self.cleaned_data.get('dateAndTimeStart', None)
		d = dt.timedelta(minutes=30)

		#check duration format (django does this for us)
		if(s == None):
			return self.cleaned_data

		#check duration format
		if(d == None):
			return self.cleaned_data
	
		#check that appointment isn't made in past
		if(s != None):
			sn = s.replace(tzinfo=None)
			if( sn < datetime.now()):
				self.add_error('dateAndTimeStart', "Can't make an appointment in the past")
	
		#check that this appointment doesn't conflict with any of the doctor's appointments
		if(du != None and s != None):
			for a in Appointment.objects.getAllAppointments(du):
				#if we are updating an appointment, we want to skip over the appointment we are updating, otherwise is error as a conflict with itself
				if a.pk != self.appID:
					if s <= a.dateAndTimeStart <= s+d:
						self.add_error('dateAndTimeStart', "That doctor already has an appointment during that time.")

		#check that this appointment doesn't conflict with any of the patient's appointments
		if(pu != None and s != None):
			for a in Appointment.objects.getAllAppointments(pu):
				#if we are updating an appointment, we want to skip over the appointment we are updating, otherwise is error as a conflict with itself
				if a.pk != self.appID:
					if s <= a.dateAndTimeStart <= s+d:
						self.add_error('dateAndTimeStart', "That patient already has an appointment during that time.")

		return self.cleaned_data

class AppointmentFormForDoctor(ModelForm):
	'''
	Form for an Appointment object, for Doctors
	'''

	def __init__(self, *args, **kwargs):
		self.doctorUsername = kwargs.pop('doctor')
		self.appID = kwargs.pop('appID', None)
		super(AppointmentFormForDoctor, self).__init__(*args, **kwargs)

	class Meta:
		model = Appointment
		fields = ('__all__')
		widgets = {'dateAndTimeStart': DateTimeInput(attrs={'class': 'startInput'}), 'duration': DateTimeInput(attrs={'class': 'durationInput'}),}
		exclude = ('doctor','dateAndTimeEnd')
		labels = { 'dateAndTimeStart':'When? *', 'duration':'How long? *', 'location':'Where?', 'desc':'For what? *', 'patient':'Patient','doctor':'Doctor *', }
	def clean(self):
		p = self.cleaned_data.get('patient', None)
		pu = None
		if(p != None):
			pu = p.username
		du = self.doctorUsername
		s = self.cleaned_data.get('dateAndTimeStart', None)
		d = self.cleaned_data.get('duration', None)

		#check that doctor is selected, if patient selected check doctor and patient relevevance
		if(du == None):
			self.add_error('doctor', 'Please select a doctor.')
		if(du and pu):
			if(p.primaryCareProvider.username != du):
				self.add_error('patient', "Chosen doctor is not the patient's doctor")

		#check duration format (django does this for us)
		if(s == None):
			return self.cleaned_data

		#check duration format
		if(d == None):
			return self.cleaned_data
	
		#check that appointment isn't made in past
		if(s != None):
			sn = s.replace(tzinfo=None)
			if( sn < datetime.now()):
				self.add_error('dateAndTimeStart', "Can't make an appointment in the past")
	
		#check that this appointment doesn't conflict with any of the doctor's appointments
		if(du != None and s != None):
			for a in Appointment.objects.getAllAppointments(du):
				#if we are updating an appointment, we want to skip over the appointment we are updating, otherwise is error as a conflict with itself
				if a.pk != self.appID:
					if s <= a.dateAndTimeStart <= s+d:
						self.add_error('dateAndTimeStart', "That doctor already has an appointment during that time.")

		#check that this appointment doesn't conflict with any of the patient's appointments
		if(pu != None and s != None):
			for a in Appointment.objects.getAllAppointments(pu):
				#if we are updating an appointment, we want to skip over the appointment we are updating, otherwise is error as a conflict with itself
				if a.pk != self.appID:
					if s <= a.dateAndTimeStart <= s+d:
						self.add_error('dateAndTimeStart', "That patient already has an appointment during that time.")

		return self.cleaned_data

class AppointmentFormForNurse(ModelForm):
	'''
	Form for an Appointment object, for Nurses
	'''

	def __init__(self, *args, **kwargs):
		self.appID = kwargs.pop('appID', None)
		super(AppointmentFormForNurse, self).__init__(*args, **kwargs)

	class Meta:
		model = Appointment
		fields = ('__all__')
		exclude = ('dateAndTimeEnd',)
		widgets = {'dateAndTimeStart': DateTimeInput(attrs={'class': 'startInput'}), 'duration': DateTimeInput(attrs={'class': 'durationInput'}),}
		labels = { 'dateAndTimeStart':'When? *', 'duration':'How long? *', 'location':'Where?', 'desc':'For what? *', 'patient':'Patient','doctor':'Doctor *', }
	def clean(self):
		p = self.cleaned_data.get('patient', None)
		pu = None
		if(p != None):
			pu = p.username
		do = self.cleaned_data.get('doctor', None)
		du = None
		if(do != None):
			du = do.username
		s = self.cleaned_data.get('dateAndTimeStart', None)
		d = self.cleaned_data.get('duration', None)

		#check that doctor is selected, if patient selected check doctor and patient relevevance
		if(du == None):
			self.add_error('doctor', 'Please select a doctor.')
		if(du and pu):
			if(p.primaryCareProvider.username != du):
				self.add_error('patient', "Chosen doctor is not the patient's doctor")

		#check duration format (django does this for us)
		if(s == None):
			return self.cleaned_data

		#check duration format
		if(d == None):
			return self.cleaned_data
	
		#check that appointment isn't made in past
		if(s != None):
			sn = s.replace(tzinfo=None)
			if( sn < datetime.now()):
				self.add_error('dateAndTimeStart', "Can't make an appointment in the past")
	
		#check that this appointment doesn't conflict with any of the doctor's appointments
		if(du != None and s != None):
			for a in Appointment.objects.getAllAppointments(du):
				#if we are updating an appointment, we want to skip over the appointment we are updating, otherwise is error as a conflict with itself
				if a.pk != self.appID:
					if s <= a.dateAndTimeStart <= s+d:
						self.add_error('dateAndTimeStart', "That doctor already has an appointment during that time.")

		#check that this appointment doesn't conflict with any of the patient's appointments
		if(pu != None and s != None):
			for a in Appointment.objects.getAllAppointments(pu):
				#if we are updating an appointment, we want to skip over the appointment we are updating, otherwise is error as a conflict with itself
				if a.pk != self.appID:
					if s <= a.dateAndTimeStart <= s+d:
						self.add_error('dateAndTimeStart', "That patient already has an appointment during that time.")

		return self.cleaned_data

class ImportModel(models.Model):
	upload = models.FileField(upload_to="importUploads/")

class ImportForm(Form):
	upload = FileField()

class EntryLog(models.Model):
	'''
	Model for an EntryLog object
	'''
	createdAt = models.DateTimeField(auto_now_add=True)
	requestUser = models.CharField(max_length=100, blank=True, null=True)
	requestPath = models.TextField(blank=True, null=True)
	requestMethod = models.CharField(max_length=4, blank=True, null=True)
	requestSecure = models.NullBooleanField(default=False, blank=True, null=True)
	requestAddress = models.GenericIPAddressField(blank=True, null=True)
	desc = models.CharField(max_length=600, blank=True, null=True)
	atHospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name='atHospital', blank=True, null=True)

class Notification(models.Model):
	'''
	Model for a notification object
	'''
	createdAt = models.DateTimeField(auto_now_add=True)
	toNotify = models.ForeignKey('HealthNetUser', on_delete=models.CASCADE)
	toNotifyUsername = models.CharField(max_length=200)
	desc = models.TextField(blank=True, null=True)
	read = models.BooleanField()

class StatsSelectionForm(Form):
	'''
	Form to be used to get date range of statistics
	'''
	start = DateField()
	end = DateField()

	def clean(self):
		s = self.cleaned_data['start']
		e = self.cleaned_data['end']
		if e < s:
			self.add_error('start', 'Please select an end time after the start time')
		return self.cleaned_data
