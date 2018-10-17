from django.db import models
import arrow
import requests
from datetime import timedelta
from django.conf import settings
from openhumans.models import OpenHumansMember
# Create your models here.


class FitbitUser(models.Model):
    """docstring for FB user"""
    oh_member = models.OneToOneField(
                    OpenHumansMember,
                    on_delete=models.CASCADE)
    personal_client_id = models.CharField(max_length=512)
    personal_client_secret = models.CharField(max_length=512)
    access_token = models.CharField(max_length=512, default='')
    refresh_token = models.CharField(max_length=512, default='')
    expires_in = models.CharField(max_length=512, default='')
    scope = models.CharField(max_length=512, default='')
    token_type = models.CharField(max_length=512, default='')

    @staticmethod
    def get_expiration(expires_in):
        return (arrow.now() + timedelta(seconds=expires_in)).format()

    def get_access_token(self):
        """
        Return access token. Refresh first if necessary.
        """
        # Also refresh if nearly expired (less than 60s remaining).
        delta = timedelta(seconds=60)
        if arrow.get(self.expires_in) - delta < arrow.now():
            self._refresh_tokens()
        return self.access_token

    def _refresh_tokens(self):
        """
        Refresh access token.
        """
        print("calling refresh token method in class")
        redirect_uri = settings.OPENHUMANS_APP_BASE_URL+'/fitbit/authorized'
        response = requests.post(
            'https://api.fitbit.com/oauth2/token',
            data={
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'redirect_uri': redirect_uri},
            auth=requests.auth.HTTPBasicAuth(
                self.personal_client_id,
                self.personal_client_secret))
        print(response.text)
        if response.status_code == 200:
            data = response.json()
            self.access_token = data['access_token']
            self.refresh_token = data['refresh_token']
            self.token_expires = self.get_expiration(data['expires_in'])
            self.scope = data['scope']
            self.userid = data['user_id']
            self.save()
            return True
        return False


class Data(models.Model):
    oh_member = models.ForeignKey(
                    OpenHumansMember,
                    on_delete=models.CASCADE)
    data_type = models.CharField(max_length=512)
    data = models.TextField(default="{}")
