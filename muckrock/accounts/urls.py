"""
URL mappings for the accounts application
"""

from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required
import django.contrib.auth.views as auth_views

import muckrock.accounts.views as views
from muckrock.forms import PasswordResetForm

urlpatterns = patterns(
    '',
    url(r'^$',
        views.AccountsView.as_view(),
        name='accounts'),
    url(r'^signup/$',
        views.AccountsView.as_view(),
        name='accounts-signup'),
    url(r'^signup/basic/$',
        views.BasicSignupView.as_view(),
        name='accounts-signup-basic'),
    url(r'^signup/professional/$',
        views.ProfessionalSignupView.as_view(),
        name='accounts-signup-professional'),
    url(r'^signup/organization/$',
        views.OrganizationSignupView.as_view(),
        name='accounts-signup-organization'),
    url(r'^login/$',
        auth_views.login,
        {'template_name': 'forms/account/login.html'},
        name='acct-login'),
    url(r'^logout/$',
        views.account_logout,
        name='acct-logout'),
    url(r'^change_pw/$',
        auth_views.password_change,
        {'template_name': 'forms/account/pw_change.html',
         'post_change_redirect': 'acct-change-pw-done'},
        name='acct-change-pw'
    ),
    url(r'^change_pw_done/$',
        auth_views.password_change_done,
        {'template_name': 'forms/account/pw_change_done.html'},
        name='acct-change-pw-done'
    ),
    url(r'^reset_pw/$',
        auth_views.password_reset,
        {'template_name': 'forms/account/pw_reset_part1.html',
         'post_reset_redirect': 'acct-reset-pw-done',
         'password_reset_form': PasswordResetForm},
        name='acct-reset-pw'),
    url(r'^reset_pw/done/$',
        auth_views.password_reset_done,
        {'template_name': 'forms/account/pw_reset_part1_done.html'},
        name='acct-reset-pw-done'),
    url(r'^reset_pw/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
        auth_views.password_reset_confirm,
        {'template_name': 'forms/account/pw_reset_part2.html'},
        name='password_reset_confirm'),
    url(r'^reset_pw/complete/$',
        auth_views.password_reset_complete,
        {'template_name': 'forms/account/pw_reset_part2_done.html'},
        name='password_reset_complete'),
    url(r'^complete_registration',
        views.RegistrationCompletionView.as_view(),
        name='accounts-complete-registration'),
    url(r'^profile/$',
        login_required(views.profile),
        name='acct-my-profile'),
    url(r'^profile/(?P<username>[\w\-.@ ]+)/$',
        views.profile,
        name='acct-profile'),
    url(r'^profile/(?P<username>[\w\-.@ ]+)/buy_requests/$',
        views.buy_requests,
        name='acct-buy-requests'),
    url(r'^notifications/$',
        views.NotificationList.as_view(),
        name='acct-notifications'),
    url(r'^settings/$',
        views.profile_settings,
        name='acct-settings'),
    url(r'^settings/verify_email/$',
        views.verify_email,
        name='acct-verify-email'),
     url(r'^proxies/$',
        views.ProxyList.as_view(),
        name='accounts-proxies'),
    url(r'^stripe_webhook_v2/$',
        views.stripe_webhook,
        name='acct-webhook-v2'),
)
