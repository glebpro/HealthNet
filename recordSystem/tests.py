from .models import *

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import AnonymousUser, User

from .views import newPatient


# Create your tests here.

# Tests all the creation of all the different models
class CreationUsers(TestCase):
    def setUp(self):
        hospital1 = Hospital.objects.create("TESTINGHOSPITAl", "TESTINGLOCATION")
        admin1 = User.objects.create_user("TESTINGADMIN", "useradmin@test.com", "TESTINGPASSWORD0")
        Administrator.objects.create(username="TESTINGADMIN", djangoUser=admin1, firstName="TESTFIRSTNAMEADMIN",
                                     lastName="TESTLASTNAMEADMIN")

    def test_patients(self):
        user2 = User.objects.create_user("TESTINGUSER1", "user1@test.com", "TESTINGPASSWORD1")
        Patient.objects.create(username="TESTINGUSER1", djangoUser=user2, firstName="TESINGFIRSTNAME1",
                               lastName="TESTINGLASTNAME1", healthNumber="TAAAAAAAAAA1")
        testpat = Patient.objects.get(username="TESTINGUSER1")
        self.assertEqual(testpat.fullname(), "TESTINGFIRSTNAME1  TESTLASTNAME1")
        self.assertEqual(testpat.healthNumber, "TAAAAAAAAAA1")

    def test_newAdmin(self):
        admin2 = User.objects.create_user("TESTINGADMIN2", "useradmin2@test.com", "TESTINGPASSWORD2")
        Administrator.objects.create(username="TESTINGADMIN2", djangoUser=admin2, firstName="TESTFIRSTNAMEADMIN2",
                                     lastName="TESTLASTNAMEADMIN2")
        testadmin = Administrator.objects.get(username="TESTINGADMIN2")
        self.assertEqual(testadmin.fullname(), "TESTFIRSTNAMEADMIN2  TESTLASTNAMEADMIN2")

    def test_doctor(self):
        doc = User.objects.create_user("TESTINGDOC", "userdoc@test.com", "TESTINGPASSWORD3")
        Doctor.objects.create(username="TESTINGDOC", djangoUser=doc, firstName="TESTFIRSTNAMEDOC",
                              lastName="TESTLASTNAMEDOC")
        testdoc = Doctor.objects.get(username="TESTINGDOC")
        self.assertEqual(testdoc.fullname(), "TESTFIRSTNAMEDOC  TESTLASTNAMEDOC")

    def test_nurse(self):
        nurse = User.objects.create_user("TESTINGNURSE", "usernurse@test.com", "TESTINGPASSWORD4")
        Doctor.objects.create(username="TESTINGNURSE", djangoUser=nurse, firstName="TESTFIRSTNAMENURSE",
                              lastName="TESTLASTNAMENURSE")
        testnurse = Nurse.objects.get(username="TESTINGNURSE")
        self.assertEqual(testnurse.fullname(), "TESTFIRSTNAMENURSE  TESTLASTNAMENURSE")

    def test_Test(self):
        Test.objects.create(date=datetime.date(2010, 1, 1),title="testing",results="success",notes="process complete")
        testTest = Test.objects.get(title="testing")
        self.assertEqual(testTest.date,datetime.date(2010, 1, 1))
        self.assertEqual(testTest.results,"success")
        self.assertEqual(testTest.notes,"process complete")


    def test_Appointment(self):
        user2 = User.objects.create_user("TESTINGUSER1", "user1@test.com", "TESTINGPASSWORD1")
        Patient.objects.create(username="TESTINGUSER1", djangoUser=user2, firstName="TESINGFIRSTNAME1",
                               lastName="TESTINGLASTNAME1", healthNumber="TAAAAAAAAAA1")
        testpat = Patient.objects.get(username="TESTINGUSER1")
        doc = User.objects.create_user("TESTINGDOC", "userdoc@test.com", "TESTINGPASSWORD3")
        Doctor.objects.create(username="TESTINGDOC", djangoUser=doc, firstName="TESTFIRSTNAMEDOC",
                              lastName="TESTLASTNAMEDOC")
        testdoc = Doctor.objects.get(username="TESTINGDOC")

        date = models.DateTimeField(default=datetime.now, editable=False,)
        dura = date.time
        appoint = Appointment.objects.create(dateAndTimeStart=date,duration=dura,location="TestLocation",desc="TestStart",patient=testpat,doctor=testdoc)
        self.assertEqual(appoint.dateAndTimeStart,date)
        self.assertEqual(appoint.duration,dura)
        self.assertEqual(appoint.location, "TestLocation")
        self.assertEqual(appoint.desc,"TestStart")
        self.assertEqual(appoint.patient, testpat)
        self.assertEqual(appoint.doctor, testdoc)

    def test_Prescription(self):
        Prescription.objects.create(name="TestStart", dosage="TestAmountStart", notes="TestDescriptionStart")
        prescript = Prescription.objects.get(name="TestStart")
        self.assertEqual(prescript.dosage,"TestAmountStart")
        self.assertEqual(prescript.notes, "TestDescriptionStart")


#Test all the different updates to the  models
class UpdateProfile(TestCase):
    def setUp(self):
        hospital1 = Hospital.objects.create("TESTINGHOSPITAl", "TESTINGLOCATION")
        admin1 = User.objects.create_user("TESTINGADMIN", "useradmin@test.com", "TESTINGPASSWORD0")
        Administrator.objects.create(username="TESTINGADMIN", djangoUser=admin1, firstName="TESTFIRSTNAMEADMIN",
                                     lastName="TESTLASTNAMEADMIN")

    def pat_update(self):
        user2 = User.objects.create_user("TESTINGUSER1", "user1@test.com", "TESTINGPASSWORD1")
        Patient.objects.create(username="TESTINGUSER1", djangoUser=user2, firstName="TESTINGFIRSTNAME1",
                               lastName="TESTINGLASTNAME1", healthNumber="TAAAAAAAAAA1")
        testpat = Patient.objects.get(username="TESTINGUSER1")
        testpat.firstName = "TESTINGFIRSTNAME12"
        self.assertEqual(testpat.fullname(), "TESTINGFIRSTNAME12  TESTINGFIRSTLAST1")
        testpat.lastName = "TESTINGLASTNAME12"
        self.assertEqual(testpat.fullname(), "TESTINGFIRSTNAME12  TESTINGFIRSTLAST12")
        testpat.healthNumber = "TAAAAAAAAA12"
        self.assertEqual(testpat.healthNumber, "TAAAAAAAAA12")

    def admin_update(self):
        admin2 = User.objects.create_user("TESTINGADMIN2", "useradmin2@test.com", "TESTINGPASSWORD2")
        Administrator.objects.create(username="TESTINGADMIN2", djangoUser=admin2, firstName="TESTFIRSTNAMEADMIN2",
                                     lastName="TESTLASTNAMEADMIN2")
        testadmin = Administrator.objects.get(username="TESTINGADMIN2")
        testadmin.firstName = "TESTFIRSTNAMEADMIN22"
        self.assertEqual(testadmin.fullname(), "TESTINGFIRSTNAMEADMIN22  TESTLASTNAMEADMIN2")
        testadmin.lastName = "TESTLASTNAMEADMIN22"
        self.assertEqual(testadmin.fullname(), "TESTINGFIRSTNAMEADMIN22  TESTLASTNAMEADMIN22")

    def doc_update(self):
        doc = User.objects.create_user("TESTINGDOC", "userdoc@test.com", "TESTINGPASSWORD3")
        Doctor.objects.create(username="TESTINGDOC", djangoUser=doc, firstName="TESTFIRSTNAMEDOC",
                              lastName="TESTLASTNAMEDOC")
        testdoc = Doctor.objects.get(username="TESTINGDOC")
        testdoc.firstName = "TESTFIRSTNAMEDOC2"
        self.assertEqual(testdoc.fullname(), "TESTINGFIRSTNAMEDOC2  TESTLASTNAMEDOC")
        testdoc.lastName = "TESTLASTNAMEDOC2"
        self.assertEqual(testdoc.fullname(), "TESTINGFIRSTNAMEDOC2  TESTFIRSTLASTNAMEDOC2")

    def nurse_update(self):
        nurse = User.objects.create_user("TESTINGNURSE", "usernurse@test.com", "TESTINGPASSWORD4")
        Doctor.objects.create(username="TESTINGNURSE", djangoUser=nurse, firstName="TESTFIRSTNAMENURSE",
                              lastName="TESTLASTNAMENURSE")
        testnurse = Nurse.objects.get(username="TESTINGNURSE")
        testnurse.firstName = "TESTFIRSTNAMENNURSE2"
        self.assertEqual(testnurse.fullname(), "TESTINGFIRSTNAMENURSE2  TESTLASTNAMENURSE")
        testnurse.lastName = "TESTLASTNAMENURSE2"
        self.assertEqual(testnurse.fullname(), "TESTINGFIRSTNAMENURSE2  TESTFIRSTLASTNAMENURSE2")


    def test_update(self):
        Test.objects.create(date=datetime.date(2010, 1, 1),title="testing",results="success",notes="process complete")
        testTest = Test.objects.get(title="testing")
        testTest.date = date=datetime.date(2010, 1, 2)
        self.assertEqual(testTest.date,datetime.date(2010, 1, 2))
        testTest.results = "SUCCESSFULL"
        self.assertEqual(testTest.results, "SUCCESSFULL")
        testTest.results = "Process Over"
        self.assertEqual(testTest.notes, "Process Over")

    def appoint_update(self):
        user2 = User.objects.create_user("TESTINGUSER1", "user1@test.com", "TESTINGPASSWORD1")
        Patient.objects.create(username="TESTINGUSER1", djangoUser=user2, firstName="TESINGFIRSTNAME1",
                               lastName="TESTINGLASTNAME1", healthNumber="TAAAAAAAAAA1")
        testpat = Patient.objects.get(username="TESTINGUSER1")
        doc = User.objects.create_user("TESTINGDOC", "userdoc@test.com", "TESTINGPASSWORD3")
        Doctor.objects.create(username="TESTINGDOC", djangoUser=doc, firstName="TESTFIRSTNAMEDOC",
                              lastName="TESTLASTNAMEDOC")
        testdoc = Doctor.objects.get(username="TESTINGDOC")

        date = models.DateTimeField(default=datetime.now, editable=False,)
        dura = date.time
        appoint = Appointment.objects.create(dateAndTimeStart=date,duration=dura,location="TestLocation",desc="TestStart",patient=testpat,doctor=testdoc)

        dateNew = models.DateTimeField(default=datetime.now, editable=False)
        duraNew = dateNew.time

        end = User.objects.create_user("TESTINGUSEREnd", "userEnd@test.com", "TESTINGPASSWORDEnd")
        Patient.objects.create(username="TESTINGUSEREnd", djangoUser=end, firstName="TESINGFIRSTNAMEEnd",
                               lastName="TESTINGLASTNAMEEnd", healthNumber="TAAAAAAAAAA2")
        Newtestpat = Patient.objects.get(username="TESTINGUSEREnd")
        start = User.objects.create_user("TESTINGDOCStart", "userdocStart@test.com", "TESTINGPASSWORDStart")
        Doctor.objects.create(username="TESTINGDOCStart", djangoUser=start, firstName="TESTFIRSTNAMEDOCStart",
                              lastName="TESTLASTNAMEDOCStart")
        Newtestdoc = Doctor.objects.get(username="TESTINGDOCStart")

        appoint.dateAndTimeStart = dateNew
        self.assertEqual(appoint.dateAndTimeStart, dateNew)
        appoint.duration = duraNew
        self.assertEqual(appoint.duration, duraNew)
        appoint.location = "TestLocationSuccess"
        self.assertEqual(appoint.location, "TestLocationSuccess")
        appoint.desc = "TestEnd"
        self.assertEqual(appoint.desc, "TestEnd")
        appoint.patient = Newtestpat
        self.assertEqual(appoint.patient, Newtestpat)
        appoint.doctor = Newtestdoc
        self.assertEqual(appoint.doctor, Newtestdoc)

    def prescrip_update(self):
        Prescription.objects.create(name="TestStart", dosage="TestAmountStart", notes="TestDescriptionStart")
        prescript = Prescription.objects.get(name="TestStart")

        prescript.name = "TestEnd"
        self.assertEqual(prescript.name, "TestEnd")
        prescript.dosage = "TestAmountEnd"
        self.assertEqual(prescript.dosage, "TestAmountEnd")
        prescript.notes = "TestDescriptionEnd"
        self.assertEqual(prescript.notes, "TestDescriptionEnd")
















