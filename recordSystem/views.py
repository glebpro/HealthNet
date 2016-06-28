'''
Controls how the user can interact with data
Author: Gleb Promokhov
'''
import json
import csv
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import render, get_object_or_404
from django.dispatch import receiver
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.contrib.auth import authenticate, login, logout
from datetime import date, datetime
import datetime as dt
import calendar
from django.shortcuts import render_to_response
from .models import * 
import operator
import re

#standard export/import funcitons
from wsgiref.util import FileWrapper

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~INDEX PAGE
def indexPage(request):
	'''
	Controls the infornmation to be displayed on the homepage/dashboard
	'''
	# Hospital should be registered first
	if (Hospital.objects.count() == 0):
		return HttpResponseRedirect("/newFirstHospital/")

	# Admin should be created second
	if (Administrator.objects.count() == 0):
		return HttpResponseRedirect("/newFirstAdministrator/")

	if request.user.is_authenticated():

		#variables to use
		currentUser = request.user
		currentProfile = HealthNetUser.objects.getChild(currentUser.username)
	
		isAdmin = 0
		isDoctor = 0
		isNurse = 0

		doctors = None
		nurses = None
		admins = None
		patients = None
		yourPatients = None
		yourDoctors = None
		yourNurses = None

		#get links of users that current user is related to in curent hospital
		if(isinstance(currentProfile, Administrator)):
			isAdmin = 1
			doctors = Doctor.objects.filter(hospitals=currentProfile.currentHospital).all()
			nurses = Nurse.objects.filter(currentHospital=currentProfile.currentHospital).all()
			admins = Administrator.objects.filter(hospitals=currentProfile.currentHospital).all()
			patients = Patient.objects.filter(currentHospital=currentProfile.currentHospital).all()
		if(isinstance(currentProfile, Doctor)):
			isDoctor = 1
			yourNurses = Nurse.objects.filter(currentHospital=currentProfile.currentHospital, doctors=currentProfile).all()
			yourPatients = Patient.objects.filter(currentHospital=currentProfile.currentHospital, primaryCareProvider=currentProfile).all()
			doctors = Doctor.objects.filter(hospitals=currentProfile.currentHospital).all()
			nurses = Nurse.objects.filter(currentHospital=currentProfile.currentHospital).all()
			patients = Patient.objects.filter(currentHospital=currentProfile.currentHospital).all()
		if(isinstance(currentProfile, Nurse)):
			isNurse = 1
			yourPatients = Patient.objects.filter(currentHospital=currentProfile.currentHospital, primaryCareProvider__in=currentProfile.doctors.all()).all()
			yourDoctors = currentProfile.doctors.all()
			patients = Patient.objects.filter(currentHospital=currentProfile.currentHospital).all()
			doctors = Doctor.objects.filter(hospitals=currentProfile.currentHospital).all()
		if(isinstance(currentProfile, Patient)):
			yourDoctors = [currentProfile.primaryCareProvider]
			yourNurses = Nurse.objects.filter(doctors=currentProfile.primaryCareProvider).all()

		#get their appointments for calendar
		events = None
		if (isinstance(currentProfile, Patient)):
				events = Appointment.objects.filter(patient=currentProfile).order_by('dateAndTimeStart').values_list('desc', 'dateAndTimeStart', 'dateAndTimeEnd', 'id')
		elif (isinstance(currentProfile, Doctor)):
				events = Appointment.objects.filter(doctor=currentProfile).order_by('dateAndTimeStart').values_list('desc', 'dateAndTimeStart', 'dateAndTimeEnd', 'id')
		elif(isinstance(currentProfile, Nurse)):
				events = Appointment.objects.filter(doctor__in=currentProfile.doctors.all()).order_by('dateAndTimeStart').values_list('desc', 'dateAndTimeStart', 'dateAndTimeEnd', 'id')
		else:
			events = None
	
		#convert appointments into format for FullCalendar
		cleanedTitles = []
		cleanedStartTimes = []
		cleanedEndTimes = []
		if(events):
			for e in events:
				cleanedTitles.append(e[0])
				cleanedStartTimes.append(e[1].isoformat())
				cleanedEndTimes.append(e[2].isoformat())
			cleanedTitles = json.dumps(cleanedTitles)

		#get relevent appointments for upcoming appointments
		apps = Appointment.objects.getUpcomingAppointments(currentUser.username)

		#get relevent notifications
		notifs = Notification.objects.filter(toNotifyUsername=currentUser.username, read=False).all()

		return render(request, 'recordSystem/index.html', {'username': currentProfile.username, 'currentHospital':getCurrentHospital(currentUser.username),
			'apps':apps, 'isAdmin':isAdmin, 'isDoctor':isDoctor, 'isNurse':isNurse,'cleanedTitles':cleanedTitles, 'cleanedStartTimes':cleanedStartTimes, 
			'cleanedEndTimes':cleanedEndTimes, 'doctors':doctors, 'nurses':nurses, 'admins':admins, 'patients':patients, 'yourPatients':yourPatients, 
			'yourDoctors':yourDoctors, 'yourNurses':yourNurses, "notifications":notifs,})

	#if not logged in, show login page
	return render(request, 'recordSystem/login.html')

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~PROFILE PAGE
def profilePage(request, username):
		'''
		Controls the infornmation to be displayed/ how it will be updated on a specific users profile page
		parameters: request (POST or GET), username: username of profile page currently being viewed
		'''

		#set variables
		currentProfile = HealthNetUser.objects.getChild(username)
		viewer = HealthNetUser.objects.getChild(request.user.username)
		pres = None
		tests = None
		apps = None
		
		#quick check
		if(currentProfile == None):
			return render(request, 'recordSystem/profile.html', {'username': request.user.username, 
				'currentHospital':getCurrentHospital(request.user.username), 'message':'This user does not exist', })

		#set permissions
		viewProfile = 1 
		updateProfile = 1
		viewMedical = 1
		updateMedical = 1
		releaseTests = 1
		canTransfer = 1
		viewTests = 1

		#if viewer is a admin, they can do anything
		if(isinstance(viewer, Administrator)):
			viewProfile = 0
			updateProfile = 0
			viewMedical = 0
			updateMedical = 0
			releaseTests = 0
			canTransfer = 0
			if(isinstance(currentProfile, Patient)):
				tests = HealthTest.objects.filter(patient=currentProfile).all()
				pres = Prescription.objects.filter(prescribedTo=currentProfile).all()

		#if viewer is a doctor
		if(isinstance(viewer, Doctor)):
			#can view anything in system
			viewProfile = 0
			viewMedical = 0
			#if viewing one of their patients, they can update profile, medical info, release tests, transfer  
			if(isinstance(currentProfile, Patient)):
				if(currentProfile.primaryCareProvider == viewer):
					updateProfile = 0
					updateMedical = 0
					releaseTests = 0
					canTransfer = 0
					#get all tests and prescriptions of patient
					tests = HealthTest.objects.filter(patient=currentProfile).all()
					pres = Prescription.objects.filter(prescribedTo=currentProfile).all()

		#if viewr is a nurse
		if(isinstance(viewer, Nurse)):
			#can view anyone in their currentHospital
			if(viewer.currentHospital in currentProfile.hospitals.all()):
				viewProfile = 0
				viewMedical = 0
			#if viewing one of their doctors patients, they can update profile, medical info, but not release tests
			if(isinstance(currentProfile, Patient)):
				if(currentProfile.primaryCareProvider in viewer.doctors.all()):
					viewProfile = 0
					viewMedical = 0
					updateProfile = 0
					updateMedical = 0
					#get all tests and prescriptions of patient
					tests = HealthTest.objects.filter(patient=currentProfile).all()
					pres = Prescription.objects.filter(prescribedTo=currentProfile).all()

		#if viewr is a patient
		if(isinstance(viewer, Patient)):
			#can view anyone in their currentHospital, profile only
			if(viewer.currentHospital in currentProfile.hospitals.all()):
				viewProfile = 0
			#if they are viewing their own profile, they can see their medical info (only released tests) 
			if(currentProfile.username == viewer.username):
				viewMedical = 0
				tests = HealthTest.objects.filter(patient=currentProfile, released=True).all()
				pres = Prescription.objects.filter(prescribedTo=currentProfile)
				
		#if viewer is viewing thier own profile, they can update their profileInfo
		#they can't transfer themseleves eitehr
		if(viewer.username == currentProfile.username):
			viewProfile = 0
			updateProfile = 0
			canTransfer = 1
			viewTests = 0
		
		#if currentprofile is not a patient, there's no medical info to view
		if(isinstance(currentProfile, Patient) == False):
			viewMedical = 1
			canTransfer = 1
			pres = None
			tests = None
			
		#if updating profile info
		if request.method == 'POST':
			if(isinstance(currentProfile, Patient)):
				form = currentProfile.getUpdateForm(request, currentProfile.username, currentProfile.healthNumber)
			else:
				form = currentProfile.getUpdateForm(request, currentProfile.username)
			if form.is_valid():
				p = form.save(commit=False)
				if(form.cleaned_data['birthDate']):
					p.age = int(datetime.now().year) - int(form.cleaned_data['birthDate'].year)
				addEntryLog(request, "A user updated their profile infornmation")
				p.save()
				form.save_m2m()
				return HttpResponseRedirect('/')

		#if viewing profile info
		else:
			addEntryLog(request, "An induvidual profile page got viewed")
			form = currentProfile.getInitialForm(currentProfile.username)
	
		return render(request, 'recordSystem/profile.html', {'username': request.user.username, 
			'currentHospital':getCurrentHospital(request.user.username), 'profileForm': form, "prescriptions":pres, "tests":tests,
			'fullName':currentProfile.fullName(), 'viewProfile':viewProfile, 'updateProfile':updateProfile, 'viewMedical':viewMedical, 
			'updateMedical':updateMedical, 'releaseTests':releaseTests, 'message':None, 'canTransfer':canTransfer, 'viewTests':viewTests,
			'uType':currentProfile.getNum(), 'profileUsername':currentProfile.username,})

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~NEW HEALTHTEST
def newHealthTest(request):
	'''
	Handles page for creation of a new Health Test object
	'''

	#some quick checks
	if (isinstance(HealthNetUser.objects.getChild(request.user.username), Patient)):
		return render(request, 'recordSystem/newHealthTest.html',{"username": request.user.username, 
			'currentHospital':getCurrentHospital(request.user.username), 'message':"Patients cannot create their own tests."})

	if(Doctor.objects.count() == 0):
		return render(request, 'recordSystem/newHealthTest.html',{"username": request.user.username, 
			'currentHospital':getCurrentHospital(request.user.username), 'message':"A doctor must be created before any tests can."})

	if(Patient.objects.count() == 0):
		return render(request, 'recordSystem/newHealthTest.html',{"username": request.user.username, 
			'currentHospital':getCurrentHospital(request.user.username), 'message':"A patient must be created before any tests can."})

	#form is submitted
	if request.method == 'POST':
		#populate appropiate form with POST info/ image upload
		currentProfile = HealthNetUser.objects.getChild(request.user.username)
		if(isinstance(currentProfile, Administrator)):
			form = HealthTestFormForAdmin(request.POST,request.FILES)
		if(isinstance(currentProfile, Doctor)):
			form = HealthTestFormForDoctor(request.POST,request.FILES)
		if(isinstance(currentProfile, Nurse)):
			form = HealthTestFormForNurse(request.POST,request.FILES)
		form.setQuerysets(currentProfile) #not really needed
		if form.is_valid():
			f = form.save(commit=False)
			if(form.cleaned_data['image'] != None):
				f.image = form.cleaned_data['image']
			addEntryLog(request, "Created new Test")
			if(isinstance(currentProfile, Doctor)):
				f.doctor = currentProfile
			if(isinstance(currentProfile, Nurse)):
				f.released = False
			f.save()
			#notify the right people
			if(isinstance(currentProfile, Administrator)):
				if(f.released==False):
					addNewNotif(f.doctor, "A new test for %s is waiting approval" % f.patient.fullName())
				else:
					addNewNotif(f.doctor, "A new test for %s has been created " % f.patient.fullName())
			if(isinstance(currentProfile, Nurse)):
				if(f.released==False):
					addNewNotif(f.doctor, "A new test for %s is waiting approval" % f.patient.fullName())
				else:
					addNewNotif(f.doctor, "A new test for %s has been created " % f.patient.fullName())
			if(f.released == True):
				addNewNotif(f.patient, "A new test has been released")
			return HttpResponseRedirect('/')

	#for is first brought up, get appropiate blank form
	else:
		currentProfile = HealthNetUser.objects.getChild(request.user.username)
		if(isinstance(currentProfile, Administrator)):
			form = HealthTestFormForAdmin()
		if(isinstance(currentProfile, Doctor)):
			form = HealthTestFormForDoctor()
		if(isinstance(currentProfile, Nurse)):
			form = HealthTestFormForNurse()
		form.setQuerysets(currentProfile)
 
	return render(request, 'recordSystem/newHealthTest.html',{'testform': form, "username": request.user.username, 
		'currentHospital':getCurrentHospital(request.user.username), 'message':None})

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~UPDATE HEALTHTEST
def updateHealthTest(request, testID):
	'''
	Handles displaying and updating an already created HealthTest
	'''

	#set permissions, patients can view tests but not alter them
	isPatient = 1
	if (isinstance(HealthNetUser.objects.getChild(request.user.username), Patient)):
		isPatient = 0

	#form is submitted
	if request.method == 'POST':
		#get appropiate form, populate with POST/FILES info
		currentProfile = HealthNetUser.objects.getChild(request.user.username)
		if(isinstance(currentProfile, Administrator)):
			form = HealthTestFormForAdmin(request.POST,request.FILES)
		if(isinstance(currentProfile, Doctor)):
			form = HealthTestFormForDoctor(request.POST, request.FILES)
		if(isinstance(currentProfile, Nurse)):
			form = HealthTestFormForNurse(request.POST, request.FILES)
		form.setQuerysets(currentProfile)
		if form.is_valid():
			x = form.save(commit=False)
			if(form.cleaned_data['image'] != None):
				x.image = form.cleaned_data['image']
			addEntryLog(request, "Updated test")
			if(isinstance(currentProfile, Doctor)):
				x.doctor = currentProfile
			if(isinstance(currentProfile, Nurse)):
				x.released = False
			x.pk = testID
			x.save(force_update=True)
			if(isinstance(currentProfile, Administrator)):
				addNewNotif(x.doctor, "A test for %s was modified" % x.patient.fullName())
				if(x.released == True):
					addNewNotif(x.patient, "One of your tests was modified")
			if(isinstance(currentProfile, Doctor)):
				if(x.released == True):
					addNewNotif(x.patient, "One of your tests was modified")
			if(isinstance(currentProfile, Nurse)):
				if(x.released == True):
					addNewNotif(x.patient, "One of your tests was modified")
				addNewNotif(x.doctor, "A test for %s was modified" % x.patient.fullName())
			return HttpResponseRedirect('/profile/%s/' % x.patient.username)
	else:
		#first load form with populated info from given instance of test being viewed
		currentProfile = HealthNetUser.objects.getChild(request.user.username)
		if(isinstance(currentProfile, Administrator)):
			form = HealthTestFormForAdmin(instance=HealthTest.objects.get(id=testID))
		if(isinstance(currentProfile, Doctor) or isinstance(currentProfile, Patient)):
			form = HealthTestFormForDoctor(instance=HealthTest.objects.get(id=testID))
		if(isinstance(currentProfile, Nurse)):
			form = HealthTestFormForNurse(instance=HealthTest.objects.get(id=testID))
		if(isinstance(currentProfile, Patient) == False):
			form.setQuerysets(currentProfile)

	return render(request, 'recordSystem/healthTest.html',{'testform': form, "username": request.user.username, 
		'currentHospital':getCurrentHospital(request.user.username), 'message':None, 'testID':testID, 'isPatient':isPatient,})

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~RELEASE HEATLHTEST
def releaseHealthTest(request, testID, pUserName):
	'''
	Handles releasing of Health Tests
	'''

	h = HealthTest.objects.get(id=testID)
	h.released = True
	addEntryLog(request, "A test got released")
	addNewNotif(h.patient, "A new test has been released")
	h.save()
	return HttpResponseRedirect('/profile/%s/' % pUserName)
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~DELETE HEALTHTEST
def deleteHealthTest(request, testID):
	'''
	Handles deletion of Health Tests
	'''
	b = HealthTest.objects.get(id=testID)
	u = b.patient.username
	addEntryLog(request, "A test got removed")
	b.delete()
	return HttpResponseRedirect('/profile/%s/' % u)
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~NEW PRESCRIPTION
def newPrescription(request):
	'''
	Handles the creation of a new Prescription
	'''

	#quick functional checks
	if (isinstance(HealthNetUser.objects.getChild(request.user.username), Patient)):
		return render(request, 'recordSystem/newPrescription.html',{"username": request.user.username, 
			'currentHospital':getCurrentHospital(request.user.username), 'message':"Patients cannot create their own prescriptions."})

	if(Doctor.objects.count() == 0):
		return render(request, 'recordSystem/newPrescription.html',{"username": request.user.username, 
			'currentHospital':getCurrentHospital(request.user.username), 'message':"A doctor must be created before any prescriptions can."})

	if(Patient.objects.count() == 0):
		return render(request, 'recordSystem/newPrescription.html',{"username": request.user.username, 
			'currentHospital':getCurrentHospital(request.user.username), 'message':"A patient must be created before any prescriptions can."})

	#form is submitted
	if request.method == 'POST':
		#get appropiate form, populate with POST info
		currentProfile = HealthNetUser.objects.getChild(request.user.username)
		if(isinstance(currentProfile, Nurse)):
			pres_form = PrescriptionFormPlus(request.POST, nurse=currentProfile)
		if(isinstance(currentProfile, Administrator)):
			pres_form = PrescriptionFormPlus(request.POST, admin=currentProfile)
		if(isinstance(currentProfile, Doctor)):
			pres_form = PrescriptionForm(request.POST, doctor=currentProfile)
		if pres_form.is_valid():
			x = pres_form.save(commit=False)
			addEntryLog(request, "Created new Prescription")
			if(isinstance(currentProfile, Doctor)):
				x.doctor = currentProfile
			x.save()
			if(isinstance(currentProfile, Doctor)):
				addNewNotif(x.prescribedTo, "A new prescription has been made")
			if(isinstance(currentProfile, Administrator)):
				addNewNotif(x.prescribedTo, "A new prescription has been made")
				addNewNotif(x.doctor, "Admin %s has created a prescription for %s" % (currentProfile.fullName(), x.prescribedTo.fullName()))
			if(isinstance(currentProfile, Nurse)):
				addNewNotif(x.prescribedTo, "A new prescription has been made")
				addNewNotif(x.doctor, "Nurse %s has created a prescription for %s" % (currentProfile.fullName(), x.prescribedTo.fullName()))
			return HttpResponseRedirect('/')
	else:
		#get appropiate blank form
		currentProfile = HealthNetUser.objects.getChild(request.user.username)
		if(isinstance(currentProfile, Nurse)):
			pres_form = PrescriptionFormPlus(nurse=currentProfile)
		if(isinstance(currentProfile, Administrator)):
			pres_form = PrescriptionFormPlus(admin=currentProfile)
		if(isinstance(currentProfile, Doctor)):
			pres_form = PrescriptionForm(doctor=currentProfile)

	return render(request, 'recordSystem/newPrescription.html',{'PForm': pres_form, "username": request.user.username, 
		'currentHospital':getCurrentHospital(request.user.username), 'message':None})

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~UPDATE PRESCRIPTION
def updatePrescription(request, presID):
	'''
	Handles viewing/updating an already exsisting Prescription
	'''

	#quick check
	if (isinstance(HealthNetUser.objects.getChild(request.user.username), Patient)):
		return render(request, 'recordSystem/newPrescription.html',{"username": request.user.username, 
			'currentHospital':getCurrentHospital(request.user.username), 'message':"Patients cannot update their own prescriptions."})

	#form is submitted
	if request.method == 'POST':
		currentProfile = HealthNetUser.objects.getChild(request.user.username)
		if(isinstance(currentProfile, Administrator)):
			pres_form = PrescriptionFormPlus(request.POST, admin=currentProfile)
		if(isinstance(currentProfile, Nurse)):
			pres_form = PrescriptionFormPlus(request.POST, nurse=currentProfile)
		if(isinstance(currentProfile, Doctor)):
			pres_form = PrescriptionForm(request.POST,doctor=currentProfile)
		if pres_form.is_valid():
			x = pres_form.save(commit=False)
			addEntryLog(request, "Updated prescription")
			x.pk = presID
			x.save(force_update=True)
			if(isinstance(currentProfile, Doctor)):
				addNewNotif(x.patient, "A prescription has been updated") 
			if(isinstance(currentProfile, Administrator)):
				addNewNotif(x.patient, "A prescription has been updated") 
				addNewNotif(x.doctor, "Admin %s updated a prescription for %s" % (currentProfile.fullName(), x.patient.fullName()))
			if(isinstance(currentProfile, Nurse)):
				addNewNotif(x.patient, "A prescription has been updated") 
				addNewNotif(x.doctor, "Nurse %s has updated a prescription for %s" % (currentProfile.fullName(), x.patient.fullName()))
			return HttpResponseRedirect('/')
	else:
		currentProfile = HealthNetUser.objects.getChild(request.user.username)
		if(isinstance(currentProfile, Administrator)):
			pres_form = PrescriptionFormPlus(instance=Prescription.objects.get(id=presID), admin=currentProfile)
		if(isinstance(currentProfile, Nurse)):
			pres_form = PrescriptionFormPlus(instance=Prescription.objects.get(id=presID), nurse=currentProfile)
		if(isinstance(currentProfile, Doctor)):
			pres_form = PrescriptionForm(instance=Prescription.objects.get(id=presID),doctor=currentProfile)

	return render(request, 'recordSystem/newPrescription.html',{'PForm': pres_form, "username": request.user.username, 
		'currentHospital':getCurrentHospital(request.user.username), 'message':None})

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~DELETE PRESCRIPTION
def deletePrescription(request, presID):
	''' 
	Handles deletion of already exsisitng Prescription
	'''

	b = Prescription.object.get(id=presID)
	addEntryLog(request, "An prescription is removed")
	addNewNotif(b.patient, "Your prescription for %s has been removed" % b.name) 
	b.delete()
	return HttpResponseRedirect('/')

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~DELETE PROFILE
def deleteProfile(request, username):
	''' 
	Handles deletion of Profile/User
	'''
	h = HealthNetUser.objects.getChild(username)
	u = User.objects.get(username=username)

	if(isinstance(h, Administrator)):
		if Administrator.objects.count() == 1:
			return HttpResponse('There must be at least one administrator active on HealthNet')

	if(isinstance(h, Doctor)):
		if Patient.objects.filter(primaryCareProvider=h):
			return HttpResponse('Please delete all patients of this doctor before deleting this doctor')

	addEntryLog(request, "User  %s deleted" % username)
	h.delete()
	u.delete()
	return HttpResponseRedirect('/')

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~NEW APPOINTMENT
def newAppointment(request):
	''' 
	Handles creation of new Appointment
	'''

	#quick check
	if (Doctor.objects.filter(hospitals=getCurrentHospital(request.user.username)).count() == 0):
		return render(request, 'recordSystem/newAppointment.html', {'username': request.user.username, 
			'currentHospital':getCurrentHospital(request.user.username), 'message':'There are no doctors at this hospital to make appointments with!'})

	currentProfile = HealthNetUser.objects.getChild(request.user.username)

	#form is submitted
	if request.method == 'POST':

		#get appropiate form, populate it with POST info
		if(isinstance(currentProfile, Doctor)):
			form = AppointmentFormForDoctor(request.POST,doctor=currentProfile.username)
		if(isinstance(currentProfile, Nurse)):
			form = AppointmentFormForNurse(request.POST)
		if(isinstance(currentProfile, Administrator)):
			form = AppointmentFormForAdministrator(request.POST)
		if(isinstance(currentProfile, Patient)):
			form = AppointmentFormForPatient(request.POST, patient=currentProfile.username, doctor=currentProfile.primaryCareProvider.username)

		if form.is_valid():

			#set appointment varialbes depending upon who's making the appointment
			appoint = form.save(commit=False)
			if(isinstance(currentProfile, Patient)):
				appoint.patient = currentProfile
				appoint.doctor = currentProfile.primaryCareProvider
				appoint.duration = dt.timedelta(minutes=30)
			if(isinstance(currentProfile, Doctor)):	
				appoint.doctor = currentProfile

			appoint.dateAndTimeEnd = appoint.dateAndTimeStart + appoint.duration
			addEntryLog(request, "Created new Appointment")
			appoint.save()
		
			#notiify the relevant users
			if(isinstance(currentProfile, Patient)):
				addNewNotif(appoint.doctor, "Patient %s has created an appointment with you" % appoint.patient.fullName())
			if(isinstance(currentProfile, Doctor)):
				if(appoint.patient):
					addNewNotif(appoint.patient, "An appointment with your doctor has been made")
			if(isinstance(currentProfile, Administrator)):
				if(appoint.patient):
					addNewNotif(appoint.patient, "An appointment with your doctor has been made")
					addNewNotif(appoint.doctor, "Admin %s has created an appointment with %s" % (currentProfile.fullName(), appoint.patient.fullName()))
				else:
					addNewNotif(appoint.doctor, "Admin %s has created an appointment for you " % currentProfile.fullName())
			if(isinstance(currentProfile, Nurse)):
				if(appoint.patient):
					addNewNotif(appoint.patient, "An appointment with your doctor has been made")
					addNewNotif(appoint.doctor, "Nurse %s has created an appointment with %s" % (currentProfile.fullName(), appoint.patient.fullName()))
				else:
					addNewNotif(appoint.doctor, "Nurse %s has created an appointment for you " % currentProfile.fullName())
			return HttpResponseRedirect('/')
	else:
	
		#bring up appropiate blnank form
		if(isinstance(currentProfile, Doctor)):
			form = AppointmentFormForDoctor(doctor=currentProfile.username)
			form.fields['patient'].queryset = Patient.objects.filter(primaryCareProvider=currentProfile, currentHospital=currentProfile.currentHospital)
		if(isinstance(currentProfile, Nurse)):
			form = AppointmentFormForNurse()
			form.fields['patient'].queryset = Patient.objects.filter(primaryCareProvider__in=currentProfile.doctors.all(), currentHospital=currentProfile.currentHospital)
			form.fields['doctor'].queryset = currentProfile.doctors.all()
		if(isinstance(currentProfile, Administrator)):
			form = AppointmentFormForAdministrator()
			form.fields['doctor'].queryset = Doctor.objects.filter(hospitals=currentProfile.currentHospital) 
			form.fields['patient'].queryset = Patient.objects.filter(currentHospital=currentProfile.currentHospital)
		if(isinstance(currentProfile, Patient)):
			form = AppointmentFormForPatient(patient=currentProfile.username, doctor=currentProfile.primaryCareProvider.username)

	return render(request, 'recordSystem/newAppointment.html', {'AppForm': form, 'username': request.user.username, 
		'currentHospital':getCurrentHospital(request.user.username), 'message':None})

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~UPDATE APPOINTMENT
def appointmentPage(request, appID):
	'''
	Handles viewing/updating an already exsisting Appointment
	'''
	currentAppointment = Appointment.objects.get(id=appID)
	currentProfile = HealthNetUser.objects.getChild(request.user.username)
	
	#form is submitted
	if request.method == 'POST':
		
		#get appropiate form, populate it with POST info
		if(isinstance(currentProfile, Doctor)):
			form = AppointmentFormForDoctor(request.POST, doctor=currentProfile.username, appID=currentAppointment.pk)
		if(isinstance(currentProfile, Nurse)):
			form = AppointmentFormForNurse(request.POST, appID=currentAppointment.pk)
		if(isinstance(currentProfile, Administrator)):
			form = AppointmentFormForAdministrator(request.POST, appID=currentAppointment.pk)
		if(isinstance(currentProfile, Patient)):
			form = AppointmentFormForPatient(request.POST, patient=currentProfile.username, doctor=currentProfile.primaryCareProvider.username, appID=currentAppointment.pk)

		if form.is_valid():
			a = form.save(commit=False)
			addEntryLog(request, "A user updated an appointment")

			#set relevant varialbes
			if(isinstance(currentProfile, Patient)):
				a.patient = currentProfile
				a.doctor = currentProfile.primaryCareProvider
				a.duration = dt.timedelta(minutes=30)
			if(isinstance(currentProfile, Doctor)):	
				a.doctor = currentProfile
			a.dateAndTimeEnd = a.dateAndTimeStart + a.duration
			a.pk = appID
			a.save(force_update=True)

			#notify the relevent users
			if(isinstance(currentProfile, Patient)):
				addNewNotif(a.doctor, "Patient %s has updated an appointment with you" % a.patient.fullName())
			if(isinstance(currentProfile, Doctor)):
				if(a.patient):
					addNewNotif(a.patient, "An appointment with your doctor has been updated")
			if(isinstance(currentProfile, Administrator)):
				if(a.patient):
					addNewNotif(a.patient, "An appointment with your doctor has been updated")
					addNewNotif(a.doctor, "Admin %s has updated n appointment with %s" % (currentProfile.fullName(), a.patient.fullName()))
				else:
					addNewNotif(appoint.doctor, "Admin %s has updated an appointment for you " % currentProfile.fullName())
			if(isinstance(currentProfile, Nurse)):
				if(a.patient):
					addNewNotif(a.doctor, "Nurse %s has updated an appointment with %s" % (currentProfile.fullName(), a.patient.fullName()))
					addNewNotif(a.patient, "An appointment with your doctor has been updated")
				else:
					addNewNotif(appoint.doctor, "Nurse %s has updated an appointment for you " % currentProfile.fullName())
			return HttpResponseRedirect('/')
	else:
		
		#if viewing appointemtn, get appropiate form populated with info from instnace of appointment being viewed
		if(isinstance(currentProfile, Doctor)):
			form = AppointmentFormForDoctor(instance=currentAppointment, doctor=currentProfile.username, appID=currentAppointment.pk)
			form.fields['patient'].queryset = Patient.objects.filter(primaryCareProvider=currentProfile, currentHospital=currentProfile.currentHospital)
		if(isinstance(currentProfile, Nurse)):
			form = AppointmentFormForNurse(instance=currentAppointment, appID=currentAppointment.pk)
			form.fields['patient'].queryset = Patient.objects.filter(primaryCareProvider__in=currentProfile.doctors.all(), currentHospital=currentProfile.currentHospital)
			form.fields['doctor'].queryset = currentProfile.doctors.all()
		if(isinstance(currentProfile, Administrator)):
			form = AppointmentFormForAdministrator(instance=currentAppointment, appID=currentAppointment.pk)
		if(isinstance(currentProfile, Patient)):
			form = AppointmentFormForPatient(instance=currentAppointment, patient=currentProfile.username, doctor=currentProfile.primaryCareProvider.username, appID=currentAppointment.pk)
		addEntryLog(request, "An induvidual appointment got viewed")

	return render(request, 'recordSystem/appointment.html', {'username': request.user.username, 
		'currentHospital':getCurrentHospital(request.user.username), 'appForm': form, 'appID': appID})

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~DELETE APPOINTMENT
def deleteAppointment(request, appID):
	'''
	Handles deletion of an already exsisitng Appointment
	'''
	a = Appointment.objects.get(pk=appID)
	addEntryLog(request, "An appointment got deleted")
	if(a.patient):
		addNewNotif(a.patient, "An appointment with your doctor has been removed")
	addNewNotif(a.doctor, "An appointment of yours has been removed")
	a.delete()
	return HttpResponseRedirect('/')

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~LOGIN
def loginPage(request):
	'''
	Handles login page
	'''

	#form is sumbimitted
	if request.method == 'POST':
		username = request.POST.get('username')
		password = request.POST.get('password')
		user = authenticate(username=username, password=password)

		#if credentials correct, take them to the dashboard page
		if user:
			if user.is_active:
				addEntryLog(request, "A user logged in")
				login(request, user)
				return HttpResponseRedirect('/')
		else:
		#if not, return to login page with displayed error
			return render(request, 'recordSystem/login.html', {'message': "Invalid username or password."})
	else:
		#if viewing login page, load unpopulated login page
		return render(request, 'recordSystem/login.html', {})

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~LOGOUT
def logoutPage(request):
	'''
	Handles logging out of user
	'''
	addEntryLog(request, "A user logged out")
	logout(request)
	return HttpResponseRedirect("/login/")

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~NEW FIRST ADMINISTRATOR
def newFirstAdministrator(request):
	'''
	Handles creation of the first Administrator
	'''

	#quick check
	if (Administrator.objects.count() != 0):
		return HttpResponse("The first administrator has already been registered!")

	#form is submitted
	if request.method == 'POST':

		#populate forms with POST info
		user_form = HealthNetUserForm(request.POST) #for django authentication
		profile_form = AdministratorForm(request.POST) #for HealthNet

		if user_form.is_valid() and profile_form.is_valid():
			user = user_form.save()
			user.set_password(user.password)
			user.first_name = profile_form.cleaned_data['firstName']
			user.last_name = profile_form.cleaned_data['lastName']
			user.email = profile_form.cleaned_data['email']  # populate these fields with profile form data

			# path save user for Authentication and SQLdatabase
			user.save()

			# create Patient
			profile = profile_form.save(commit=False)
			profile.djangoUser = user
			if(profile_form.cleaned_data.get('birthDate')):
				profile.age = int(datetime.now().year) - int(profile_form.cleaned_data['birthDate'].year)
			profile.username = user.username
			addEntryLog(request, "Created first Administrator")
			profile.currentHospital = profile_form.cleaned_data['hospitals'][0]
			profile.save()
			profile_form.save_m2m()

			# log them in (slight hack to do it)
			user.backend = 'django.contrib.auth.backends.ModelBackend'  # to auto-login
			user = authenticate(username=user_form.cleaned_data['username'],
								password=user_form.cleaned_data['password'])
			login(request, user)
			return HttpResponseRedirect('/')
	else:
		#if viewing first administrator page, just get blank forms
		user_form = HealthNetUserForm()
		profile_form = AdministratorForm()

	return render(request, 'recordSystem/newFirstAdministrator.html',{'userForm': user_form, 'profileForm': profile_form, })

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~NEW PATIENT
def newPatient(request):
		'''
		Handles creation of a new patient (patient registration)
		'''

		#quick checks
		if(Doctor.objects.count() == 0):
			return render(request, 'recordSystem/newPatient.html',{ 'message':'No doctors yet! (Please contact the admin )' })
		if(Hospital.objects.count() == 0):
			return render(request, 'recordSystem/newPatient.html',{ 'message':'No hospitals yet! (Please contact the admin )' })

		#form is submitted
		if request.method == 'POST':

				# this form is for the django User creation
				user_form = HealthNetUserForm(request.POST)

				# this is for HealthNet profile creation
				profile_form = PatientForm(request.POST)

				if user_form.is_valid() and profile_form.is_valid():

						# create django user
						user = user_form.save()
						user.set_password(user.password)
						user.first_name = profile_form.cleaned_data['firstName']
						user.last_name = profile_form.cleaned_data['lastName']
						user.email = profile_form.cleaned_data['email']  # populate these fields with profile form data

						# path save user for Authentication and SQLdatabase
						user.save()

						# create Patient
						profile = profile_form.save(commit=False)
						profile.djangoUser = user
						if(profile_form.cleaned_data['birthDate']):
							profile.age = int(datetime.now().year) - int(profile_form.cleaned_data['birthDate'].year)
						profile.username = user.username
						addEntryLog(request, "Created new Patient")
						profile.save()
						profile_form.save_m2m()

						addNewNotif(profile.primaryCareProvider, "A new patient %s has registered with you" % profile.fullName()) 

						# log them in (slight hack to do it)
						user.backend = 'django.contrib.auth.backends.ModelBackend'  # to auto-login
						user = authenticate(username=user_form.cleaned_data['username'],
										password=user_form.cleaned_data['password'])
						login(request, user)
						return HttpResponseRedirect('/')
		else:
				#if just viewing new patient page, get blank forms
				user_form = HealthNetUserForm()
				profile_form = PatientForm()

		return render(request, 'recordSystem/newPatient.html',{'userForm': user_form, 'profileForm': profile_form, 'message':None })

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~NEW ADMINISTRATOR
def newAdministrator(request):
		'''
		Handles creation of a new administrator
		'''
	
		#quick check
		if(isinstance(HealthNetUser.objects.getChild(request.user.username), Administrator) == False):
			return render(request, 'recordSystem/newAdministrator.html', {'username': request.user.username, 
				'currentHospital':getCurrentHospital(request.user.username), 'message':"Only Administrators can create new Administrators" })

		#form is submitted
		if request.method == 'POST':

				# this form is for the django User creation
				user_form = HealthNetUserForm(request.POST)

				# this is for HealthNet Administrator creation
				profile_form = AdministratorForm(request.POST)

				if user_form.is_valid() and profile_form.is_valid():

						# create django user
						user = user_form.save()
						user.set_password(user.password)
						user.first_name = profile_form.cleaned_data['firstName']
						user.last_name = profile_form.cleaned_data['lastName']
						user.email = profile_form.cleaned_data['email']  # populate these fields with profile form data

						# path save user for Authentication and SQLdatabase
						user.save()

						# create Admin
						profile = profile_form.save(commit=False)
						profile.djangoUser = user
						profile.username = user.username
						
						if(profile_form.cleaned_data['birthDate']):
							profile.age = int(datetime.now().year) - int(profile_form.cleaned_data['birthDate'].year)
						addEntryLog(request, "Created new Administrator")
						profile.currentHospital = profile_form.cleaned_data['hospitals'][0]
						profile.save()
						profile_form.save_m2m()
						return HttpResponseRedirect("/")
		else:
				#if just viewing new admin page, get blank forms
				user_form = HealthNetUserForm()
				profile_form = AdministratorForm()

		return render(request, 'recordSystem/newAdministrator.html', {'userForm': user_form, 'profileForm': profile_form, 
			'username': request.user.username, 'currentHospital':getCurrentHospital(request.user.username), 'message':None })

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~NEW DOCTOR
def newDoctor(request):
		'''
		Handles creation of a new Doctor
		'''
		#quick check
		if(isinstance(HealthNetUser.objects.getChild(request.user.username), Administrator) == False):
			return render(request, 'recordSystem/newDoctor.html', {'username': request.user.username, 
				'currentHospital':getCurrentHospital(request.user.username), 'message':"Only Administrators can create new Doctors" })

		#form is submitted
		if request.method == 'POST':

				# this form is for the django User creation
				user_form = HealthNetUserForm(request.POST)

				# this is for HealthNet Doctor creation
				profile_form = DoctorForm(request.POST)

				if user_form.is_valid() and profile_form.is_valid():

						# create django user
						user = user_form.save()
						user.set_password(user.password)
						user.first_name = profile_form.cleaned_data['firstName']
						user.last_name = profile_form.cleaned_data['lastName']
						user.email = profile_form.cleaned_data['email']  # populate these fields with profile form data

						# path save user for Authentication and SQLdatabase
						user.save()

						# create Doctor
						profile = profile_form.save(commit=False)
						profile.djangoUser = user
						profile.username = user.username
						if(profile_form.cleaned_data['birthDate']):
							profile.age = int(datetime.now().year) - int(profile_form.cleaned_data['birthDate'].year)
						profile.currentHospital = profile_form.cleaned_data['hospitals'][0]
						addEntryLog(request, "Created new Doctor")
						profile.save()
						profile_form.save_m2m()

						return HttpResponseRedirect('/')
		else:
				#if viewing new doctor page, just get blank forms
				user_form = HealthNetUserForm()
				profile_form = DoctorForm()

		return render(request, 'recordSystem/newDoctor.html', {'userForm': user_form, 'profileForm': profile_form, 'username': request.user.username, 
			'currentHospital':getCurrentHospital(request.user.username), 'message':None })

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~NEW NURSE
def newNurse(request):
		'''
		Handles creationg of a new Nurse
		'''
		
		#quick checks
		if(Doctor.objects.count() == 0):
			return render(request, 'recordSystem/newNurse.html', {'username': request.user.username, 
				'currentHosptial':getCurrentHospital(request.user.username), 'message':'A doctor must be created before a nurse can!', })
		if(isinstance(HealthNetUser.objects.getChild(request.user.username), Administrator) == False):
			return render(request, 'recordSystem/newDoctor.html', {'username': request.user.username, 
				'currentHospital':getCurrentHospital(request.user.username), 'message':"Only Administrators can create new Nurses." })

		#form is submitted
		if request.method == 'POST':

				# this form is for the django User creation
				user_form = HealthNetUserForm(request.POST)

				# this is for HealthNet Nurse creation
				profile_form = NurseForm(request.POST)

				if user_form.is_valid() and profile_form.is_valid():

						# create django user
						user = user_form.save()
						user.set_password(user.password)
						user.first_name = profile_form.cleaned_data['firstName']
						user.last_name = profile_form.cleaned_data['lastName']
						user.email = profile_form.cleaned_data['email']  # populate these fields with profile form data

						# path save user for Authentication and SQLdatabase
						user.save()

						# create Nurse
						profile = profile_form.save(commit=False)
						profile.djangoUser = user
						profile.username = user.username
						b = profile_form.cleaned_data['birthDate']
						if(profile_form.cleaned_data['birthDate']):
							profile.age = int(datetime.now().year) - int(profile_form.cleaned_data['birthDate'].year)
						addEntryLog(request, "Created new Nurse")
						profile.save()
						profile_form.save_m2m()
						for d in profile.doctors.all():
							addNewNotif(d, "A new nurse %s has registered with you" % profile.fullName()) 
						return HttpResponseRedirect('/')
		else:
				#if just viewing new nurse page, get blank forms
				user_form = HealthNetUserForm()
				profile_form = NurseForm()

		return render(request, 'recordSystem/newNurse.html', {'userForm': user_form, 'profileForm': profile_form, 'username': request.user.username, 
			'currentHospital':getCurrentHospital(request.user.username),'message':None, })

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~NEW FIRST HOSPITAL
def newFirstHospital(request):
	'''
	Handles creation of the first hospital
	'''

	#quick check
	if(Hospital.objects.count() != 0):
		return HttpResponse("The first hosptial has already been created! <a href='/'>Home</a>")

	#form is sbumitted
	if request.method == 'POST':
		form = HospitalForm(request.POST)
		if form.is_valid():
			h = form.save(commit=False)
			addEntryLog(request, "Created new Hospital")
			h.save()
			return HttpResponseRedirect('/')
	else:
		#if viewing new first hospital page, get a blnka form
		form = HospitalForm()

	return render(request, 'recordSystem/newFirstHospital.html', {'hospitalForm': form})

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~NEW HOSPITAL
def newHospitalPage(request):
	'''
	Handles creation of a new Hospital (after first admin and hospital have been created)
	'''
	
	#quick check
	if(isinstance(HealthNetUser.objects.getChild(request.user.username), Administrator) == False):
		return render(request, 'recordSystem/newDoctor.html', {'username': request.user.username, 'currentHospital':getCurrentHospital(request.user.username),			 'message':"Only Administrators can create new Hospitals." })

	#form is submitted
	if request.method == 'POST':
		form = HospitalForm(request.POST)
		if form.is_valid():
			h = form.save(commit=False)
			addEntryLog(request, "Created new Hospital")
			h.save()
			a = HealthNetUser.objects.getChild(request.user.username)
			a.hospitals.add(h)
			a.save()
			return HttpResponseRedirect('/')
	else:
		#if vieiwng new hospital page, get a blank form
		form = HospitalForm()

	return render(request, 'recordSystem/newHospital.html', {'username':request.user.username, 'currentHospital':getCurrentHospital(request.user.username), 
		'hospitalForm': form, 'message':None})

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~HOSPITAL SELECTION
def hospitalSelectionPage(request):
	'''
	Handles changing of a admins/doctors currentHospital
	Most of the infornmation on the site is relevant to the users currentHospital
	'''
	if(isinstance(HealthNetUser.objects.getChild(request.user.username), Administrator) == False and
		isinstance(HealthNetUser.objects.getChild(request.user.username), Doctor) == False):
		return render(request, 'recordSystem/hospitalSelection.html', {'username': request.user.username, 
			'currentHospital':getCurrentHospital(request.user.username), 'message':"Only Administrators or Doctors can change their current hospital." })

	if request.method == 'POST':
		hos = HealthNetUser.objects.getChild(request.user.username).hospitals.all()
		form = HospitalSelectionForm(request.POST,start=getCurrentHospital(request.user.username), fromset= hos)
		if form.is_valid():
			p = HealthNetUser.objects.getChild(request.user.username)
			p.currentHospital = form.cleaned_data['hospital']
			p.save()
			return HttpResponseRedirect('/')
	else:
		hos = HealthNetUser.objects.getChild(request.user.username).hospitals.all()
		form = HospitalSelectionForm(start=getCurrentHospital(request.user.username), fromset= hos)

	return render(request, 'recordSystem/hospitalSelection.html', {'username': request.user.username, 
		'currentHospital':getCurrentHospital(request.user.username), 'hospitalSelectionForm':form, 'message':None, })
	

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~TRANSFER
def transfer(request, pUserName):
	'''
	Handles chaning of a patient's currentHospital
	'''

	p = HealthNetUser.objects.getChild(pUserName)
	if request.method == 'POST':
		form = HospitalTransferForm(request.POST, start=p.currentHospital,patient=p)	
		if form.is_valid():
			p.currentHospital = form.cleaned_data['hospital']
			p.save()
			addNewNotif(p, "You have been transfered to a differnet hospital")
			return HttpResponseRedirect('/profile/%s/' % pUserName)
	else:
		form = HospitalTransferForm(start=p.currentHospital, patient=p)
	
	return render(request, 'recordSystem/hospitalTransfer.html', {'username': request.user.username, 'pUserName':pUserName, 'pName':p.fullName(),
		'currentHospital':getCurrentHospital(request.user.username), 'form':form, 'message':None, })

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~EXPORT PATIENT DATA
def exportPatientInfo(request, pUserName):
	'''
	Handles exporting of a specific patients data (profile+medical) into csv format
	'''

	exp = HealthNetExport()
	i = Patient.objects.get(username=pUserName)
	u = User.objects.get(username=i.username)
	exp.add_patient(pk=i.pk, username=i.username, password_hash=u.password, first_name=i.firstName, health_number=i.healthNumber,
		middle_name=i.middleName, last_name=i.lastName, dob=i.birthDate, addr=i.address, email=i.email,
		phone=i.phoneNumber, emergency_contact=i.emergencyContact, eye_color=i.eyeColor,bloodtype=i.bloodType, height=i.height,
		weight=i.weight, primary_hospital_id=i.currentHospital.pk,
		primary_doctor_id=i.primaryCareProvider.pk,
		doctor_ids=[])
	r = HttpResponse((exp.export_json()))
	r['Content-Disposition'] = 'attachment; filename=%sExport.json' % i.username
	return r
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~EXPORT SYSTEM DATA
def exportSystemInfoStandard(request):

	exp = HealthNetExport()

	for h in Hospital.objects.all():
		exp.add_hospital(pk=h.pk, name=h.name, addr=h.address)

	for i in Administrator.objects.all():
		u = User.objects.get(username=i.username)
		exp.add_admin(pk=i.pk, username=i.username, password_hash=u.password, first_name=i.firstName,
			last_name=i.lastName, middle_name=i.middleName, dob=i.birthDate, addr=i.address, email=i.email,
			phone=i.phoneNumber,
			primary_hospital_id=i.currentHospital.pk, hospital_ids=[h.pk for h in i.hospitals.all()])

	for i in Doctor.objects.all():
		u = User.objects.get(username=i.username)
		exp.add_doctor(pk=i.pk, username=i.username, password_hash=u.password, first_name=i.firstName,
			last_name=i.lastName, middle_name=i.middleName, dob=i.birthDate, addr=i.address, email=i.email,
			phone=i.phoneNumber,
			hospital_ids=[h.pk for h in i.hospitals.all()], patient_ids=[p.pk for p in Patient.objects.filter(primaryCareProvider=i).all()])

	for i in Nurse.objects.all():
		u = User.objects.get(username=i.username)
		exp.add_nurse(pk=i.pk, username=i.username, password_hash=u.password, first_name=i.firstName,
			last_name=i.lastName, middle_name=i.middleName, dob=i.birthDate, addr=i.address, email=i.email,
			phone=i.phoneNumber,
			primary_hospital_id=i.currentHospital.pk,
			doctor_ids=[d.pk for d in i.doctors.all()])

	for i in Patient.objects.all():
		u = User.objects.get(username=i.username)
		exp.add_patient(pk=i.pk, username=i.username, password_hash=u.password, first_name=i.firstName,
			middle_name=i.middleName, last_name=i.lastName, dob=i.birthDate, addr=i.address, email=i.email,
			phone=i.phoneNumber, emergency_contact=i.emergencyContact, eye_color=i.eyeColor,bloodtype=i.bloodType, height=i.height,
			weight=i.weight, primary_hospital_id=i.currentHospital.pk,
			primary_doctor_id=i.primaryCareProvider.pk,
			doctor_ids=[])

	for i in Appointment.objects.all():
		exp.add_appointment(start=i.dateAndTimeStart, end=dateAndTimeEnd, location=i.location, description=i.desc,
		doctor_ids=[i.doctor.pk],
		patient_ids=[i.patient.pk],
		nurse_ids=[])

	for i in Prescription.objects.all():
		exp.add_prescription(name=i.name, dosage=i.dosage,
			notes=i.notes,
			doctor_id=i.doctor.pk, patient_id=i.prescribedTo.pk)
	r = HttpResponse((exp.export_json()))
	r['Content-Disposition'] = 'attachment; filename=healthNetExport.json'
	return r

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~EXPORT HOSPITAL DATA
def exportHospitalInfoStandard(request):

	h = HealthNetUser.objects.getChild(request.user.username).currentHospital

	exp = HealthNetExport()

	exp.add_hospital(pk=h.pk, name=h.name, addr=h.address)

	for i in Administrator.objects.filter(hospitals=h).all():
		u = User.objects.get(username=i.username)
		exp.add_admin(pk=i.pk, username=i.username, password_hash=u.password, first_name=i.firstName,
			last_name=i.lastName, middle_name=i.middleName, dob=i.birthDate, addr=i.address, email=i.email,
			phone=i.phoneNumber,
			primary_hospital_id=i.currentHospital.pk, hospital_ids=[h.pk for h in i.hospitals.all()])

	for i in Doctor.objects.filter(hospitals=h).all():
		u = User.objects.get(username=i.username)
		exp.add_doctor(pk=i.pk, username=i.username, password_hash=u.password, first_name=i.firstName,
			last_name=i.lastName, middle_name=i.middleName, dob=i.birthDate, addr=i.address, email=i.email,
			phone=i.phoneNumber,
			hospital_ids=[h.pk for h in i.hospitals.all()], patient_ids=[p.pk for p in Patient.objects.filter(primaryCareProvider=i).all()])

	for i in Nurse.objects.filter(currentHospital=h).all():
		u = User.objects.get(username=i.username)
		exp.add_nurse(pk=i.pk, username=i.username, password_hash=u.password, first_name=i.firstName,
			last_name=i.lastName, middle_name=i.middleName, dob=i.birthDate, addr=i.address, email=i.email,
			phone=i.phoneNumber,
			primary_hospital_id=i.currentHospital.pk,
			doctor_ids=[d.pk for d in i.doctors.all()])

	for i in Patient.objects.filter(currentHospital=h).all():
		u = User.objects.get(username=i.username)
		exp.add_patient(pk=i.pk, username=i.username, password_hash=u.password, health_number=i.healthNumber,first_name=i.firstName,
			middle_name=i.middleName, last_name=i.lastName, dob=i.birthDate, addr=i.address, email=i.email,
			phone=i.phoneNumber, emergency_contact=i.emergencyContact, eye_color=i.eyeColor,bloodtype=i.bloodType, height=i.height,
			weight=i.weight, primary_hospital_id=i.currentHospital.pk,
			primary_doctor_id=i.primaryCareProvider.pk,
			doctor_ids=[])

	for i in Appointment.objects.filter(doctor__in=Doctor.objects.filter(hospitals=h).all(), patient__in=Patient.objects.filter(currentHospital=h).all()).all():
		exp.add_appointment(start=i.dateAndTimeStart, end=dateAndTimeEnd, location=i.location, description=i.desc,
		doctor_ids=[i.doctor.pk],
		patient_ids=[i.patient.pk],
		nurse_ids=[])

	for i in Prescription.objects.filter(doctor__in=Doctor.objects.filter(hospitals=h).all(), prescribedTo=Patient.objects.filter(currentHospital=h).all()).all():
		exp.add_prescription(name=i.name, dosage=i.dosage,
			notes=i.notes,
			doctor_id=i.doctor.pk, patient_id=i.prescribedTo.pk)

	r = HttpResponse((exp.export_json()))
	r['Content-Disposition'] = ('attachment; filename=%sExport.json' % h.name)
	return r

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~IMPORT SYSTEM DATA
def importSystemInfoStandard(request):
	if request.method == 'POST':
		form = ImportForm(request.POST, request.FILES)
		if form.is_valid():
			s = request.FILES['upload'].read().decode()
			upload(request, s)
			return HttpResponseRedirect('/')
	else:
		form = ImportForm()

	return render(request, 'recordSystem/upload.html', {'form':form})

def upload(request, data):
	imp = HealthNetImport(data,createHospital,createAdmin,createDoctor,createNurse,createPatient,createAppointment,createPrescription,createHealthTest)
	imp.import_all()
	
def createHospital(name, addr):
	h = Hospital.objects.get_or_create(name=name, address=addr)

def createAdmin(username, password_hash, first_name, middle_name, last_name, dob, addr, email, phone, primary_hospital_id, hospital_ids):
	User.objects.get_or_create(username=username, password=password_hash)
	u = User.objects.get(username=username)
	Administrator.objects.get_or_create(djangoUser=u, username=username, currentHospital=Hospital.objects.get(pk=primary_hospital_id+1),firstName=first_name, middleName=middle_name, lastName=last_name, birthDate=dob, address=addr, email=email, phoneNumber=phone)
	a = Administrator.objects.get(username=username)
	for h in hospital_ids:
		ho = Hospital.objects.get(pk=h+1)
		a.hospitals.add(ho)

def createDoctor(username, password_hash, first_name, middle_name, last_name, dob, addr, email, phone, hospital_ids, patient_ids):
	User.objects.get_or_create(username=username, password=password_hash)
	u = User.objects.get(username=username)
	Doctor.objects.get_or_create(djangoUser=u, username=username, currentHospital=Hospital.objects.get(pk=hospital_ids[0]+1), firstName=first_name, middleName=middle_name, lastName=last_name, birthDate=dob, address=addr, email=email, phoneNumber=phone)
	d = Doctor.objects.get(username=username)
	for h in hospital_ids:
		ho = Hospital.objects.get(pk=h+1)
		d.hospitals.add(ho)
	for p in patient_ids:
		po = Patient.objects.get(pk=p+1)
		d.patients.add(po)

def createNurse(username, password_hash, first_name, middle_name, last_name, dob, addr, email, phone, primary_hospital_id, doctor_ids):
	User.objects.get_or_create(username=username, password=password_hash)
	u = User.objects.get(username=username)
	Nurse.objects.get_or_create(djangoUser=u, username=username, currentHospital=Hospital.objects.get(pk=primary_hospital_id), firstName=first_name, middleName=middle_name, lastName=last_name, birthDate=dob, address=addr, email=email, phoneNumber=phone)
	n = Nurse.objects.get(username=username)
	for d in doctor_ids:
		do = Doctor.objects.get(pk=d+1)
		n.doctors.add(do)

def createPatient(username, password_hash,health_number, first_name, middle_name, last_name, dob, addr, email, phone, emergency_contact, eye_color, bloodtype, weight, height, primary_hospital_id, primary_doctor_id, doctor_ids):
	u = User.objects.get_or_create(username=username, password=password_hash)
	p = Patient.objects.get_or_create(djangoUser=u, username=username, healthNumber=health_number, currentHospital=Hospital.objects.get(pk=primary_hospital_id+1), primaryCareProvider=Doctor.objects.get(pk=primary_doctor_id+1), firstName=first_name, middleName=middle_name, lastName=last_name, birthDate=dob, address=addr, email=email, phoneNumber=phone, emergencyContact=emerygency_contact, eyeColor=eye_color, bloodType=bloodtype, weight=weight, height=height)

def createAppointment(start, end,location, description, doctor_ids, nurse_ids, patient_ids):
	a = Appointment.objects.get_or_create(dateAndTimeStart=start, dateAndTimeEnd=end, duration=(end-start), desc=description,location=location,patient=Patient.objects.get(pk=patient_ids[0]+1), doctor=Doctor.objects.get(pk=doctor_ids[0]+1))

def createPrescription(name, dosage, notes,doctor_id, patient_id):
	p = Prescription.objects.get_or_create(name=name,dosage=dosage, notes=notes,doctor=Doctor.objects.get(pk=doctor_id+1),prescribedTo=Patient.objects.get(pk=patient_id+1))

def createHealthTest(name,date,description,results,released,doctor_id,patient_id):
	h = HealthTest.objects.get_or_create(title=name,date=date,desc=description,results=results,released=released,doctor=Doctor.objects.get(pk=doctor_id+1),patient=Patient.objects.get(pk=patient_id+1))

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~PRINT PATIENT INFO
def printInfo(request, pUserName):
	'''
	Handles displaying page to print of specific patient info
	'''
	p = Patient.objects.get(username=pUserName)
	pres = Prescription.objects.filter(prescribedTo=p).all()
	tests = HealthTest.objects.filter(patient=p, released=True)
	pcpemail = p.primaryCareProvider.email
	hAddress = p.currentHospital.address
	return render(request, 'recordSystem/printInfo.html', {'p':p, 'pres':pres, 'tests':tests,'pcpemail':pcpemail,'hAddress':hAddress,})
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ENTRY LOGS
def viewEntryLogs(request):
	'''
	Handles displaying of system logs
	'''
	if request.user.is_authenticated():
		addEntryLog(request, "System logs were viewed")
		els = EntryLog.objects.filter(atHospital=getCurrentHospital(request.user.username)).all()
		return render(request, 'recordsystem/systemlogs.html', {'logs': els, 'username': (request.user.username), 'currentHospital':getCurrentHospital(request.user.username)})
	else:
		return HttpResponse("please log in to view system logs")

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~STATISTICS
def preStats(request):
	
	if request.method == 'POST':
		form = StatsSelectionForm(request.POST)
		if form.is_valid():
			s = form.cleaned_data['start']
			e = form.cleaned_data['end']
			return stats(request, e, s)
	else:
		form = StatsSelectionForm()
	
	return render(request, 'recordsystem/preStats.html', {'username': (request.user.username), 'currentHospital':getCurrentHospital(request.user.username), 'form':form})
		
def stats(request, e, s):
	'''
	Handles displaying of system stastics
	'''
	addEntryLog(request, "Stats were viewed")

	#~~~get system stats
	if(Prescription.objects.count() != 0):
		systemMostDrugs = {} 
		for p in Prescription.objects.filter(date__gt=s,date__lt=e).all():
			if p.name in systemMostDrugs:
				systemMostDrugs[p.name]+=1
			else:
				systemMostDrugs[p.name]=1
		systemMostDrug = sorted(systemMostDrugs.items(), key=operator.itemgetter(0))[0][0]
	else:
		systemMostDrug = "No prescriptions made"

	if(HealthTest.objects.count() != 0):
		systemMostTests = {} 
		for p in HealthTest.objects.filter(date__gt=s,date__lt=e).all():
			if p.title in systemMostTests:
				systemMostDrugs[p.title]+=1
			else:
				systemMostDrugs[p.title]=1
		systemMostTest = sorted(systemMostTests.items(), key=operator.itemgetter(0))[0][0]
	else:
		systemMostTest = "No tests were made"

	systemAdminCount = Administrator.objects.filter(date__gt=s,date__lt=e).count()
	systemDoctorCount = Doctor.objects.filter(date__gt=s,date__lt=e).count()
	systemNurseCount = Nurse.objects.filter(date__gt=s,date__lt=e).count()
	systemPatientCount = Patient.objects.filter(date__gt=s,date__lt=e).count()

	if(Doctor.objects.count() != 0):
		systemBusyDoctors = {} 
		for p in Appointment.objects.all():
			if p.doctor.username in systemBusyDoctors:
				systemBusyDoctors[p.doctor.username]+=1
			else:
				systemBusyDoctors[p.doctor.username]=1
		systemBusyDoctor = sorted(systemBusyDoctors.items(), key=operator.itemgetter(0))[0][0]
	else:
		systemBusyDoctor = None


	#get current hosptial stats
	h = getCurrentHospital(request.user.username)
	d = Doctor.objects.filter(hospitals=h,date__gt=s,date__lt=e).all()

	if(HealthTest.objects.filter(doctor__in=d).count() != 0):
		hospitalMostTests = {} 
		for p in HealthTest.objects.filter(doctor__in=d,date__gt=s,date__lt=e).all():
			if p.title in systemMostTests:
				hospitalMostTests[p.title]+=1
			else:
				hospitalMostsTests[p.title]=1
		hospitalMostTest = sorted(hospitalMostTests.items(), key=operator.itemgetter(0))[0][0]
	else:
		hospitalMostTest = "No tests were made in this hospital"

	if(Prescription.objects.filter(doctor__in=d).count() != 0):
		hospitalMostDrugs = {} 
		for p in Prescription.objects.filter(doctor__in=d,date__gt=s,date__lt=e).all():
			if p.name in hospitalMostDrugs:
				hospitalMostDrugs[p.name]+=1
			else:
				hospitalMostDrugs[p.name]=1
		hospitalMostDrug = sorted(hospitalMostDrugs.items(), key=operator.itemgetter(0))[0][0]
	else:
		hospitalMostDrug = "No tests were made in this hospital"

	hospitalAdminCount = Administrator.objects.filter(hospitals=h,date__gt=s,date__lt=e).count()
	hospitalDoctorCount = Doctor.objects.filter(hospitals=h,date__gt=s,date__lt=e).count()
	hospitalNurseCount = Nurse.objects.filter(currentHospital=h,date__gt=s,date__lt=e).count()
	hospitalPatientCount = Patient.objects.filter(currentHospital=h,date__gt=s,date__lt=e).count()

	if(d.count() != 0):
		hospitalBusyDoctors = {} 
		for p in Appointment.objects.filter(date__gt=s,date__lt=e).all():
			if(p.doctor.username in hospitalBusyDoctors):
				hospitalBusyDoctors[p.doctor.username]+=1
			elif(p.doctor.username in d.values_list('username', flat=True)):
				hospitalBusyDoctors[p.doctor.username]=1
		hospitalBusyDoctor = sorted(hospitalBusyDoctors.items(), key=operator.itemgetter(0))[0][0]
	else:
		hospitalBusyDoctor = None
    
	return render(request, 'recordsystem/stats.html', {'username':(request.user.username), 'currentHospital':getCurrentHospital(request.user.username),
			'sMD':systemMostDrug, 'sMT':systemMostTest, 'sAC':systemAdminCount, 'sDC':systemDoctorCount, 'sNC':systemNurseCount, 'sPC':systemPatientCount,
			'sBD':systemBusyDoctor, 'hMD':hospitalMostDrug, 'hMT':hospitalMostTest, 
			'hAC':hospitalAdminCount, 'hDC':hospitalDoctorCount, 'hNC':hospitalNurseCount,
			'hPC':hospitalPatientCount, 'hBD':hospitalBusyDoctor,})

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~NOTIFICATION
def readNotification(request, notifID):
	'''
	Read notification button is clicked
	'''
	n = Notification.objects.get(pk=notifID)
	n.read = True
	n.pk = notifID
	n.save(force_update=True)
	return HttpResponseRedirect('/')

def readAllNotifications(request):
	'''
	Read all notifications button has been clicked
	'''
	notif = Notification.objects.filter(toNotifyUsername=(request.user.username),read = False).all()
	for n in notif:
		n.read = True
		n.save()
	return HttpResponseRedirect('/')
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~FUNCTIONS FOR THIS FILE
def addEntryLog(request, d):
#make a new entry log with request and description
#will be logged in hospital the user performed the action in 
    e = EntryLog(
        desc=d,
        createdAt=datetime.now(),
		requestUser=request.user.username,
        requestPath=request.path,
        requestMethod=request.method,
        requestSecure=request.is_secure(),
		requestAddress=request.META['REMOTE_ADDR'],
		atHospital=getCurrentHospital(request.user.username),
    )
    if isinstance(request.user, Administrator) or isinstance(request.user, Doctor) or isinstance(request.user,Nurse) or isinstance(request.user, Patient):
        if request.user.is_authenticated():
            e.requestuser = request.user

    e.save()

def addNewNotif(forWhom, desc):
	'''
	Creates a new notification object
	'''
	n = Notification(
		createdAt = datetime.now(),
		toNotify = forWhom,
		toNotifyUsername = forWhom.username,
		desc = desc,
		read = False,
	)
	n.save()


def getCurrentHospital(u):
	'''
	Gets current hospital of a user, given their username
	'''
	a = HealthNetUser.objects.getChild(u)
	if(a):
		return a.currentHospital
