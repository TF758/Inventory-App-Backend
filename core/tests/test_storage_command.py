from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase


class StorageCheckCommandTests(SimpleTestCase):
    def test_command_verifies_both_application_storage_aliases(self):
        output = StringIO()

        call_command("check_storage", stdout=output)

        command_output = output.getvalue()
        self.assertIn("Storage alias 'default' verified.", command_output)
        self.assertIn("Storage alias 'reports' verified.", command_output)
