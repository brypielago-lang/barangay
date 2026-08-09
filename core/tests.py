from datetime import date
from django.test import TestCase
from .models import Resident

class ResidentTests(TestCase):
    def test_resident_number_is_generated(self):
        resident = Resident.objects.create(first_name='Ana', last_name='Santos', birth_date=date(2000, 1, 1), sex='F', address='Purok 1')
        self.assertTrue(resident.resident_no.startswith('RES-'))
