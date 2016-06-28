HealthNet is an electronic medical database interface that allows for patients, nurses
and doctors to organize their appointments, prescriptions and other infornmation across multiple hospitals.

~~~~LAUNCH INSTRUCTIONS:

To launch the site, navigate to the HealthNet directory (with manage.py in it) and simply run the command: python manage.py runserver
and navigate in a web browser to the address printed.

~~~~SYSTEM REQUIRNMENTS:

To run HealthNet, have the following in the version as listed or higher:
Django 1.9
Python 3.4.3

~~~~SYSTEM QUESTIONS:

Why are their multiple versions of an administrator?

If you navigate to the /admin page, you will be prompted to enter in admin credentials.
These are not the same as the credentials of any admin in HealthNet.
HealthNet has an Administrator account, which allows you to control any aspect of the system.
The technology that HealthNet runs on has a seperate administration, which should not be used.

Why am I not seeing all of my patients/doctors/nurses? Why are my appointment incorrect?

The infornmation that HealthNet displays is largely relevent what hospital you are curretnly
working in. If you are logged in as a doctor or administrator, you can change what
hospital you are curretnly operating in by clicking the 'currently in hospital' link on the right side of the top control bar.

Can't I just navigate to the deleteProfile/<username> URL to delete someone?

Yes, there are certain pages on the site which can be 'URL-hacked'. Please avoid manually
typing in URLs and use the displayed HealthNet links.

Is HealthNet asynchronous?

No, if a patient and a doctor are updating the same appointment at the same time, a race condition will be generated.

----BUGS:

-Updating images for a specific healthtest is buggy.

-Importing system infornmation make not work completly.

-Exporting system infornmation when there are appointments in the selected export date range will crash it
