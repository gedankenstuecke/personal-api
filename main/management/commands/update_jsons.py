from django.core.management.base import BaseCommand
from openhumans.models import OpenHumansMember
from main import helpers
import requests


class Command(BaseCommand):
    help = 'Process so far unprocessed data sets'

    def handle(self, *args, **options):
        #how to keep the heroku app alive despite a free dyno :joy:
        requests.get('http://my-personal-api.herokuapp.com/')
        oh_members = OpenHumansMember.objects.all()
        for oh_member in oh_members:
            try:
                if oh_member.list_files() != []:
                    helpers.compile_music(oh_member)
                    # disabled until we fix overland
                    helpers.compile_location(oh_member)
                    helpers.compile_oura_sleep(oh_member)
                    if hasattr(oh_member, 'fitbituser'):
                        helpers.compile_fitbit(oh_member)
