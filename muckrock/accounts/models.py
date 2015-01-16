"""
Models for the accounts application
"""

from django.contrib.auth.models import User
from django.contrib.localflavor.us.models import PhoneNumberField, USStateField
from django.core.mail import EmailMessage
from django.db import models
from django.template.loader import render_to_string

from easy_thumbnails.fields import ThumbnailerImageField
from datetime import datetime
from itertools import groupby
from urlauth.models import AuthKey
import dbsettings
import stripe

from muckrock.foia.models import FOIARequest
from muckrock.jurisdiction.models import Jurisdiction
from muckrock.organization.models import Organization
from muckrock.settings import MONTHLY_REQUESTS, STRIPE_SECRET_KEY
from muckrock.values import TextValue

stripe.api_key = STRIPE_SECRET_KEY

class EmailOptions(dbsettings.Group):
    """DB settings for sending email"""
    email_footer = TextValue('email footer')

options = EmailOptions()

ACCT_TYPES = [
    ('admin', 'Admin'),
    ('beta', 'Beta'),
    ('community', 'Community'),
    ('pro', 'Professional'),
    ('proxy', 'Proxy'),
]

class Profile(models.Model):
    """User profile information for muckrock"""
    # pylint: disable=too-many-public-methods

    email_prefs = (
        ('instant', 'Instant'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
    )

    user = models.ForeignKey(User, unique=True)
    address1 = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='address'
    )
    address2 = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='address (line 2)'
    )
    city = models.CharField(max_length=60, blank=True)
    state = USStateField(
        blank=True,
        help_text=('Your state will be made public on this site.'
                   'If you do not want this information to be public,'
                   ' please leave blank.')
    )
    zip_code = models.CharField(max_length=10, blank=True)
    phone = PhoneNumberField(blank=True)
    follows_foia = models.ManyToManyField(
        FOIARequest,
        related_name='followed_by',
        blank=True
    )
    follows_question = models.ManyToManyField(
        'qanda.Question',
        related_name='followed_by',
        blank=True
    )
    notifications = models.ManyToManyField(
        FOIARequest,
        related_name='notify',
        blank=True
    )
    follow_questions = models.BooleanField(default=False)
    acct_type = models.CharField(max_length=10, choices=ACCT_TYPES)
    organization = models.ForeignKey(Organization, blank=True, null=True, related_name='users')

    # email confirmation
    email_confirmed = models.BooleanField(default=False)
    confirmation_key = models.CharField(max_length=24, blank=True)
    key_expire_date = models.DateField(blank=True, null=True)

    # extended information
    profile = models.TextField(blank=True)
    location = models.ForeignKey(Jurisdiction, blank=True, null=True)
    public_email = models.EmailField(max_length=255, blank=True)
    pgp_public_key = models.TextField(blank=True)
    website = models.URLField(
        max_length=255,
        blank=True,
        help_text='Begin with http://'
    )
    twitter = models.CharField(max_length=255, blank=True)
    linkedin = models.URLField(
        max_length=255,
        blank=True,
        help_text='Begin with http://'
    )
    avatar = ThumbnailerImageField(
        upload_to='account_images',
        blank=True, null=True,
        resize_source={'size': (200, 200), 'crop': 'smart'}
    )

    # prefrences
    email_pref = models.CharField(
        max_length=10,
        choices=email_prefs,
        default='daily',
        verbose_name='Email Preference',
        help_text=('Receive email updates to your requests instantly'
                   ' or in a daily or weekly digest')
    )
    use_autologin = models.BooleanField(
        default=True,
        help_text=('Links you receive in emails from us will contain'
                   ' a one time token to automatically log you in')
    )

    # paid for requests
    num_requests = models.IntegerField(default=0)
    # for limiting # of requests / month
    monthly_requests = models.IntegerField(default=0)
    date_update = models.DateField()
    # for stripe
    stripe_id = models.CharField(max_length=255, blank=True)

    def __unicode__(self):
        return u"%s's Profile" % unicode(self.user).capitalize()

    @models.permalink
    def get_absolute_url(self):
        """The url for this object"""
        # pylint: disable=E1101
        return ('acct-profile', [], {'user_name': self.user.username})

    def is_member_of(self, organization):
        """Answers whether the profile is a member of the passed organization"""
        return self.organization == organization

    def get_monthly_requests(self):
        """Get the number of requests left for this month"""
        not_this_month = self.date_update.month != datetime.now().month
        not_this_year = self.date_update.year != datetime.now().year
        # update requests if they have not yet been updated this month
        if not_this_month or not_this_year:
            self.date_update = datetime.now()
            self.monthly_requests = MONTHLY_REQUESTS.get(self.acct_type, 0)
            self.save()
        return self.monthly_requests

    def total_requests(self):
        """Get sum of paid for requests and monthly requests"""
        org_reqs = self.organization.get_requests() if self.organization else 0
        return self.num_requests + self.get_monthly_requests() + org_reqs

    def make_request(self):
        """Decrement the user's request amount by one"""
        organization = self.organization
        if organization and organization.get_requests() > 0:
            organization.num_requests -= 1
            organization.save()
            return True
        if self.get_monthly_requests() > 0:
            self.monthly_requests -= 1
        elif self.num_requests > 0:
            self.num_requests -= 1
        else:
            return False
        self.save()
        return True

    def multiple_requests(self, num):
        """How many requests of each type would be used for this user to make num requests"""
        request_dict = {'org_requests': 0, 'monthly_requests': 0,
                        'reg_requests': 0, 'extra_requests': 0}

        org_reqs = self.organization.get_requests()
        if org_reqs > num:
            request_dict['org_requests'] = num
            return request_dict
        else:
            request_dict['org_requests'] = org_reqs
            num -= org_reqs

        monthly = self.get_monthly_requests()
        if monthly > num:
            request_dict['monthly_requests'] = num
            return request_dict
        else:
            request_dict['monthly_requests'] = monthly
            num -= monthly

        if self.num_requests > num:
            request_dict['reg_requests'] = num
            return request_dict
        else:
            request_dict['reg_requests'] = self.num_requests
            request_dict['extra_requests'] = num - self.num_requests
            return request_dict

    def can_embargo(self):
        """Is this user allowed to embargo?"""
        return self.acct_type in ['admin', 'beta', 'pro', 'proxy']

    def can_view_emails(self):
        """Is this user allowed to view all emails and private contact information?"""
        return self.acct_type in ['admin', 'pro']

    def customer(self):
        """Get stripe customer or create one if it doesn't exist"""
        try:
            customer = stripe.Customer.retrieve(self.stripe_id)
        except stripe.InvalidRequestError:
            customer = stripe.Customer.create(
                description=self.user.username,
                email=self.user.email
            )
            self.stripe_id = customer.id
            self.save()
        finally:
            return customer

    def pay(self, token, amount, desc):
        """Create a stripe charge for the user"""
        # pylint: disable=E1101
        return stripe.Charge.create(
            amount=amount,
            currency='usd',
            card=token,
            description='%s: %s' % (self.user.username, desc)
        )

    def api_pay(self, amount, desc):
        """Create a stripe charge for the user through the API"""
        # pylint: disable=E1101
        customer = self.customer()
        desc = '%s: %s' % (self.user.username, desc)
        # always use card on file
        stripe.Charge.create(
            amount=amount,
            currency='usd',
            customer=customer.id,
            description=desc
        )

    def notify(self, foia):
        """Notify a user that foia has been updated or mark to be notified later
           according to preference"""
        # pylint: disable=E1101

        if self.email_pref == 'instant':
            link = self.wrap_url(foia.get_absolute_url())

            msg = render_to_string('text/foia/mail.txt', {
                'name': self.user.get_full_name(),
                'title': foia.title,
                'status': foia.get_status_display(),
                'link': link,
                'follow': self.user != foia.user,
                'footer': options.email_footer
            })
            email = EmailMessage(
                subject='[MuckRock] FOI request "%s" has been updated' % foia.title,
                body=msg,
                from_email='info@muckrock.com',
                to=[self.user.email],
                bcc=['diagnostics@muckrock.com']
            )
            email.send(fail_silently=False)

        else:
            self.notifications.add(foia)
            self.save()

    def send_notifications(self):
        """Send deferred notifications"""
        # pylint: disable=E1101

        subjects = {
            'done': "you've got new MuckRock docs!",
            'partial': "you've got new MuckRock docs!",
            'rejected': 'an agency rejected a MuckRock request - appeal?',
            'fix': 'we need help fixing a MuckRock request.',
            'payment': 'an agency wants payment for a MuckRock request.'
        }
        category = {
            'done': 'Completed Requests',
            'partial': 'Completed Requests',
            'rejected': 'Rejected Requests',
            'fix': 'Requests Needing Action',
            'payment': 'Requests Needing Action',
        }
        status_order = ['done', 'partial', 'rejected', 'fix', 'payment',
                        'no_docs', 'abandoned', 'appealing', 'started',
                        'submitted', 'ack', 'processed']

        def get_subject(status, total_foias):
            """Get subject for a given status"""
            if status in subjects:
                return subjects[status]
            elif total_foias > 1:
                return '%d MuckRock requests have updates' % total_foias
            else:
                return 'a MuckRock request has been updated'

        foias = sorted(
            self.notifications.all(),
            key=lambda f: status_order.index(f.status) if f.status in status_order else 100
        )
        grouped_foias = list((s, list(fs)) for s, fs in groupby(
            foias,
            lambda f: category.get(f.status, 'Recently Updated Requests')
        ))
        if not grouped_foias:
            return
        if len(grouped_foias) == 1:
            subject = '%s, %s' % (
                self.user.first_name,
                get_subject(grouped_foias[0][1][0].status, len(foias))
            )
        else:
            subject = '%s, %s  Plus, %s' % (
                self.user.first_name,
                get_subject(grouped_foias[0][1][0].status, len(foias)),
                get_subject(grouped_foias[1][1][0].status, len(foias))
            )

        msg = render_to_string('text/user/notify_mail.txt', {
            'name': self.user.get_full_name(),
            'foias': grouped_foias,
            'footer': options.email_footer
        })
        email = EmailMessage(
            subject=subject,
            body=msg,
            from_email='info@muckrock.com',
            to=[self.user.email],
            bcc=['diagnostics@muckrock.com']
        )
        email.send(fail_silently=False)

        self.notifications.clear()

    def wrap_url(self, link):
        """Wrap a URL for autologin"""
        if self.use_autologin:
            return AuthKey.objects.wrap_url(link, uid=self.user.pk)
        else:
            return link

class Statistics(models.Model):
    """Nightly statistics"""
    # pylint: disable=invalid-name
    date = models.DateField()
    total_requests = models.IntegerField()
    total_requests_success = models.IntegerField()
    total_requests_denied = models.IntegerField()
    total_requests_draft = models.IntegerField(null=True)
    total_requests_submitted = models.IntegerField(null=True)
    total_requests_awaiting_ack = models.IntegerField(null=True)
    total_requests_awaiting_response = models.IntegerField(null=True)
    total_requests_awaiting_appeal = models.IntegerField(null=True)
    total_requests_fix_required = models.IntegerField(null=True)
    total_requests_payment_required = models.IntegerField(null=True)
    total_requests_no_docs = models.IntegerField(null=True)
    total_requests_partial = models.IntegerField(null=True)
    total_requests_abandoned = models.IntegerField(null=True)

    orphaned_communications = models.IntegerField(null=True)

    total_agencies = models.IntegerField()
    stale_agencies = models.IntegerField(null=True)
    unapproved_agencies = models.IntegerField(null=True)

    total_pages = models.IntegerField()
    total_users = models.IntegerField()
    users_today = models.ManyToManyField(User)
    total_fees = models.IntegerField()
    pro_users = models.IntegerField(null=True)
    pro_user_names = models.TextField(blank=True)
    total_page_views = models.IntegerField(null=True)
    daily_requests_pro = models.IntegerField(null=True)
    daily_requests_community = models.IntegerField(null=True)
    daily_requests_beta = models.IntegerField(null=True)
    daily_articles = models.IntegerField(null=True)

    def __unicode__(self):
        return 'Stats for %s' % self.date

    class Meta:
        # pylint: disable=R0903
        ordering = ['-date']
        verbose_name_plural = 'statistics'

