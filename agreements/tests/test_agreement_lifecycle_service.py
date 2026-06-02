from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase

from agreements.models.agreements import (
    AgreementHistory,
    AgreementStatus,
)


from agreements.service import AgreementLifecycleService
from core.factories.agreement_factories import AssetAgreementFactory
from users.factories.user_factories import (
    UserFactory,
)


class AgreementLifecycleServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    # =================================================
    # Expire Agreement
    # =================================================

    def test_expire_agreement_marks_status_expired(self):

        agreement = AssetAgreementFactory(
             expired=True,
            status=AgreementStatus.ACTIVE,
        )

        changed = (
            AgreementLifecycleService
            .expire_agreement(
                agreement=agreement,
                user=self.user,
            )
        )

        agreement.refresh_from_db()

        self.assertTrue(changed)

        self.assertEqual(
            agreement.status,
            AgreementStatus.EXPIRED,
        )

    def test_expire_agreement_creates_history_record(self):

        agreement = AssetAgreementFactory(
            expired=True,
            status=AgreementStatus.ACTIVE,
        )

        AgreementLifecycleService.expire_agreement(
            agreement=agreement,
            user=self.user,
        )

        history = (
            AgreementHistory.objects
            .get(agreement=agreement)
        )

        self.assertEqual(
            history.event_type,
            AgreementHistory.EventType.EXPIRED,
        )

        self.assertEqual(
            history.previous_status,
            AgreementStatus.ACTIVE,
        )

        self.assertEqual(
            history.new_status,
            AgreementStatus.EXPIRED,
        )

        self.assertEqual(
            history.user,
            self.user,
        )

    def test_expire_agreement_returns_false_when_already_expired(self):

        agreement = AssetAgreementFactory(
            status=AgreementStatus.EXPIRED,
        )

        changed = (
            AgreementLifecycleService
            .expire_agreement(
                agreement=agreement,
                user=self.user,
            )
        )

        self.assertFalse(changed)

        self.assertEqual(
            AgreementHistory.objects.count(),
            0,
        )

    # =================================================
    # Terminate Agreement
    # =================================================

    def test_terminate_agreement_marks_status_terminated(self):

        agreement = AssetAgreementFactory(
            status=AgreementStatus.ACTIVE,
        )

        AgreementLifecycleService.terminate_agreement(
            agreement=agreement,
            user=self.user,
        )

        agreement.refresh_from_db()

        self.assertEqual(
            agreement.status,
            AgreementStatus.TERMINATED,
        )

    def test_terminate_agreement_creates_history_record(self):

        agreement = AssetAgreementFactory(
            status=AgreementStatus.ACTIVE,
        )

        AgreementLifecycleService.terminate_agreement(
            agreement=agreement,
            user=self.user,
        )

        history = (
            AgreementHistory.objects
            .get(agreement=agreement)
        )

        self.assertEqual(
            history.event_type,
            AgreementHistory.EventType.TERMINATED,
        )

        self.assertEqual(
            history.previous_status,
            AgreementStatus.ACTIVE,
        )

        self.assertEqual(
            history.new_status,
            AgreementStatus.TERMINATED,
        )

    def test_cannot_terminate_already_terminated_agreement(self):

        agreement = AssetAgreementFactory(
            status=AgreementStatus.TERMINATED,
        )

        with self.assertRaises(ValidationError):

            AgreementLifecycleService.terminate_agreement(
                agreement=agreement,
                user=self.user,
            )

    # =================================================
    # Extend Agreement
    # =================================================

    def test_extend_agreement_updates_expiry_date(self):

        original_expiry = (
            date.today()
            + timedelta(days=30)
        )

        new_expiry = (
            date.today()
            + timedelta(days=90)
        )

        agreement = AssetAgreementFactory(
            status=AgreementStatus.ACTIVE,
            expiry_date=original_expiry,
        )

        AgreementLifecycleService.extend_agreement(
            agreement=agreement,
            new_expiry_date=new_expiry,
            user=self.user,
        )

        agreement.refresh_from_db()

        self.assertEqual(
            agreement.expiry_date,
            new_expiry,
        )

    def test_extend_agreement_creates_history_record(self):

        original_expiry = (
            date.today()
            + timedelta(days=30)
        )

        new_expiry = (
            date.today()
            + timedelta(days=90)
        )

        agreement = AssetAgreementFactory(
            expiry_date=original_expiry,
        )

        AgreementLifecycleService.extend_agreement(
            agreement=agreement,
            new_expiry_date=new_expiry,
            user=self.user,
        )

        history = (
            AgreementHistory.objects
            .get(agreement=agreement)
        )

        self.assertEqual(
            history.event_type,
            AgreementHistory.EventType.EXTENDED,
        )

        self.assertEqual(
            history.previous_expiry_date,
            original_expiry,
        )

        self.assertEqual(
            history.new_expiry_date,
            new_expiry,
        )

    def test_cannot_extend_terminated_agreement(self):

        agreement = AssetAgreementFactory(
            status=AgreementStatus.TERMINATED,
            expiry_date=(
                date.today()
                + timedelta(days=30)
            ),
        )

        with self.assertRaises(ValidationError):

            AgreementLifecycleService.extend_agreement(
                agreement=agreement,
                new_expiry_date=(
                    date.today()
                    + timedelta(days=60)
                ),
                user=self.user,
            )

    def test_cannot_extend_agreement_without_expiry_date(self):

        agreement = AssetAgreementFactory()

        agreement.expiry_date = None
        agreement.renewal_date = None

        agreement.save(
            update_fields=[
                "expiry_date",
                "renewal_date",
            ]
        )

        with self.assertRaises(ValidationError):

            AgreementLifecycleService.extend_agreement(
                agreement=agreement,
                new_expiry_date=(
                    date.today()
                    + timedelta(days=30)
                ),
                user=self.user,
            )

    def test_cannot_extend_with_earlier_expiry_date(self):

        agreement = AssetAgreementFactory(
            expiry_date=(
                date.today()
                + timedelta(days=60)
            ),
        )

        with self.assertRaises(ValidationError):

            AgreementLifecycleService.extend_agreement(
                agreement=agreement,
                new_expiry_date=(
                    date.today()
                    + timedelta(days=30)
                ),
                user=self.user,
            )

    # =================================================
    # Renew Agreement
    # =================================================

    def test_renew_agreement_updates_dates(self):

        agreement = AssetAgreementFactory(
            status=AgreementStatus.ACTIVE,
            expiry_date=(
                date.today()
                + timedelta(days=30)
            ),
            renewal_date=(
                date.today()
                + timedelta(days=15)
            ),
        )

        new_expiry = (
            date.today()
            + timedelta(days=365)
        )

        new_renewal = (
            date.today()
            + timedelta(days=330)
        )

        AgreementLifecycleService.renew_agreement(
            agreement=agreement,
            new_expiry_date=new_expiry,
            new_renewal_date=new_renewal,
            user=self.user,
        )

        agreement.refresh_from_db()

        self.assertEqual(
            agreement.expiry_date,
            new_expiry,
        )

        self.assertEqual(
            agreement.renewal_date,
            new_renewal,
        )

    def test_renew_expired_agreement_reactivates_it(self):

        agreement = AssetAgreementFactory(
            status=AgreementStatus.EXPIRED,
            start_date=date.today() - timedelta(days=365),
            expiry_date=date.today() - timedelta(days=1),
            renewal_date=date.today() - timedelta(days=30),
        )

        AgreementLifecycleService.renew_agreement(
            agreement=agreement,
            new_expiry_date=(
                date.today()
                + timedelta(days=365)
            ),
            new_renewal_date=(
                date.today()+ timedelta(days=330)
            ),
            user=self.user,
        )

        agreement.refresh_from_db()

        self.assertEqual(
            agreement.status,
            AgreementStatus.ACTIVE,
        )

    def test_renew_creates_history_record(self):

        agreement = AssetAgreementFactory(
            status=AgreementStatus.ACTIVE,
            expiry_date=(
                date.today()
                + timedelta(days=30)
            ),
            renewal_date=(
                date.today()
                + timedelta(days=15)
            ),
        )

        AgreementLifecycleService.renew_agreement(
            agreement=agreement,
            new_expiry_date=(
                date.today()
                + timedelta(days=365)
            ),
            new_renewal_date=(
                date.today()
                + timedelta(days=330)
            ),
            user=self.user,
        )

        history = (
            AgreementHistory.objects
            .get(agreement=agreement)
        )

        self.assertEqual(
            history.event_type,
            AgreementHistory.EventType.RENEWED,
        )

    def test_cannot_renew_terminated_agreement(self):

        agreement = AssetAgreementFactory(
            status=AgreementStatus.TERMINATED,
        )

        with self.assertRaises(ValidationError):

            AgreementLifecycleService.renew_agreement(
                agreement=agreement,
                new_expiry_date=(
                    date.today()
                    + timedelta(days=365)
                ),
                user=self.user,
            )

    def test_cannot_renew_with_earlier_expiry_date(self):

        agreement = AssetAgreementFactory(
            expiry_date=(
                date.today()
                + timedelta(days=365)
            ),
        )

        with self.assertRaises(ValidationError):

            AgreementLifecycleService.renew_agreement(
                agreement=agreement,
                new_expiry_date=(
                    date.today()
                    + timedelta(days=30)
                ),
                user=self.user,
            )