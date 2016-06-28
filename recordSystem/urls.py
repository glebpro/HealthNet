'''
Controls how URLs will be handeled
Author: Gleb Promokhov
'''

from django.conf.urls import url

from . import views

app_name = 'recordSystem' 
urlpatterns = [
    url(r'^$', views.indexPage, name='indexPage'),
    url(r'^login/$', views.loginPage, name='loginPage'),
    url(r'^logout/$', views.logoutPage, name='logoutPage'),
    url(r'^systemLogs/$', views.viewEntryLogs, name='systemLogsPage'),
    url(r'^newFirstAdministrator/$', views.newFirstAdministrator, name='newFirstAdministratorPage'),
    url(r'^newPatient/$', views.newPatient, name='newPatientPage'),
    url(r'^newAdministrator/$', views.newAdministrator, name='newAdministratorPage'),
    url(r'^newDoctor/$', views.newDoctor, name='newDoctorPage'),
    url(r'^newNurse/$', views.newNurse, name='newNursePage'),
    url(r'^newFirstHospital/$', views.newFirstHospital, name='newFirstHospitalPage'),
    url(r'^newHospital/$', views.newHospitalPage, name='newHospitalPage'),
    url(r'^hospitalSelection/$', views.hospitalSelectionPage, name='hospitalSelectionPage'),
    url(r'^profile/(?P<username>\w+)/$', views.profilePage, name='profilePage'),
    url(r'^deleteProfile/(?P<username>\w+)/$', views.deleteProfile, name='deleteProfilePage'),
    url(r'^newAppointment/$', views.newAppointment, name='newAppointmentPage'),
    url(r'^deleteAppointment/(?P<appID>\w+)/$', views.deleteAppointment, name='deleteAppointmentPage'),
    url(r'^appointment/(?P<appID>\w+)/$', views.appointmentPage, name='appointmentsPage'),
    url(r'^newPrescription/$', views.newPrescription, name='newPrescriptionPage'),
    url(r'^deletePrescription/(?P<presID>\w+)/$', views.deletePrescription, name='deletePrescriptionPage'),
    url(r'^prescription/(?P<presID>\w+)/$', views.updatePrescription, name='updatePrescriptionPage'),
    url(r'^newHealthTest/$', views.newHealthTest, name='newHealthTestPage'),
    url(r'^deleteHealthTest/(?P<testID>\w+)/$', views.deleteHealthTest, name='deleteHealthTestPage'),
    url(r'^healthTest/(?P<testID>\w+)/$', views.updateHealthTest, name='updateHealthTestPage'),
    url(r'^releaseHealthTest/(?P<testID>\w+)/(?P<pUserName>\w+)/$', views.releaseHealthTest, name='releaseHealthTestPage'),
    url(r'^transfer/(?P<pUserName>\w+)/$', views.transfer, name='transferPage'),
    url(r'^printInfo/(?P<pUserName>\w+)/$', views.printInfo, name='printInfoPage'),
    url(r'^exportPatientInfo/(?P<pUserName>\w+)/$', views.exportPatientInfo, name='exportPatientInfoPage'),
    url(r'^exportSystemInfo/$', views.exportSystemInfoStandard, name='exportSystemInfoPage'),
    url(r'^exportHospitalInfo/$', views.exportHospitalInfoStandard, name='exportHospitalInfoPage'),
    url(r'^importSystemInfo/$', views.importSystemInfoStandard, name='importSystemInfoPage'),
    url(r'^preStats/$', views.preStats, name='preStatsPage'),
    url(r'^stats/$', views.stats, name='statsPage'),
    url(r'^readNotification/(?P<notifID>\w+)/$', views.readNotification, name='readNotificationPage'),
    url(r'^readAllNotifications/$', views.readAllNotifications, name='readAllNotificationsPage'),
]
