'''
Controls what models are able to be administrated
through the Djanog administration panel
Author: Gleb Promokhov
'''

from django.contrib import admin
from .models import *

admin.site.register(Hospital)
admin.site.register(Administrator)
admin.site.register(Doctor)
admin.site.register(Patient)
admin.site.register(Nurse)
admin.site.register(Appointment)
admin.site.register(EntryLog)
admin.site.register(Prescription)
admin.site.register(HealthTest)
