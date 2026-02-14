from django.core.management.base import BaseCommand
from apps.account.models import User

class Command(BaseCommand):
    help = 'Create a normal user'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str)
        parser.add_argument('email', type=str)
        parser.add_argument('password', type=str)
        parser.add_argument('--staff', action='store_true', help='Make user a staff member')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f'User {username} already exists'))
            return
        
        user = User.objects.create_user(username=username, email=email, password=password)
        if options['staff']:
            user.is_staff = True
            user.save()
        self.stdout.write(self.style.SUCCESS(f'User {username} created successfully'))
