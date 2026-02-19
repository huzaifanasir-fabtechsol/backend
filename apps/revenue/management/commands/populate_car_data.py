from django.core.management.base import BaseCommand
from apps.revenue.models import CarCategory, Auction
from apps.account.models import User
from django.db import IntegrityError

class Command(BaseCommand):
    help = 'Populate car categories and auctions'

    def handle(self, *args, **options):
        # Get first user or create a default one
        user = User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR('No users found. Please create a user first.'))
            return

        # Car categories data
        car_data = {
            'TOYOTA': [
                'Toyota Yaris', 'Toyota Yaris Cross', 'Toyota Corolla Hatchback', 'Toyota Glanza (India)',
                'Toyota Agya / Wigo', 'Toyota Aygo X', 'Toyota Corolla', 'Toyota Camry', 'Toyota Yaris Sedan',
                'Toyota Avalon', 'Toyota Crown', 'Toyota Belta', 'Toyota Premio', 'Toyota Allion',
                'Toyota RAV4', 'Toyota Fortuner', 'Toyota Land Cruiser', 'Toyota Land Cruiser Prado',
                'Toyota Highlander', 'Toyota Corolla Cross', 'Toyota Urban Cruiser', 'Toyota Rush',
                'Toyota Sequoia', 'Toyota Venza', 'Toyota 4Runner', 'Toyota Harrier', 'Toyota C-HR',
                'Toyota Innova', 'Toyota Innova HyCross', 'Toyota Avanza', 'Toyota Veloz', 'Toyota Sienta',
                'Toyota Alphard', 'Toyota Vellfire', 'Toyota HiAce', 'Toyota Hilux', 'Toyota Tacoma',
                'Toyota Tundra', 'Toyota Prius', 'Toyota bZ4X', 'Toyota Corolla Hybrid', 'Toyota Camry Hybrid'
            ],
            'SUZUKI': [
                'Alto', 'Alto Lapin', 'Wagon R', 'Wagon R Smile', 'Spacia', 'Spacia Custom',
                'Spacia Gear', 'Hustler', 'Jimny (Kei version)', 'Swift', 'Swift Sport',
                'Baleno (limited availability)', 'Ignis', 'Solio', 'Solio Bandit', 'Jimny Sierra',
                'Escudo (Vitara)', 'Xbee (Crossbee)', 'Landy (rebadged Toyota Noah/Voxy)',
                'Mini EV (concept / limited)', 'Every', 'Every Wagon', 'Carry Truck', 'Super Carry'
            ],
            'DAIHATSU': [
                'Kei Car Mira', 'Kei Car Mira e:S', 'Kei Car Mira Tocot', 'Kei Car Cast',
                'Kei Car Cast Style', 'Kei Car Cast Activa', 'Kei Car Cast Sport', 'Kei Car Move',
                'Kei Car Move Custom', 'Kei Car Move Canbus', 'Kei Car Tanto', 'Kei Car Tanto Custom',
                'Kei Car Tanto FunCross', 'Kei Car Tanto Exe (older)', 'Kei Car Wake',
                'Kei Car Hijjet Cargo', 'Kei Car Hijjet Truck', 'Compact Car Boon', 'Compact Car Thor',
                'Compact Car Thor Custom', 'SUV Rocky', 'SUV Taft', 'MPV Sigra (limited markets)',
                'MPV Xenia (limited markets)', 'Commercial Hijjet Cargo', 'Commercial Hijjet Truck',
                'Commercial Atrai', 'Commercial Atrai Wagon'
            ],
            'HONDA': [
                'Kei Car N-BOX', 'Kei Car N-BOX Custom', 'Kei Car N-WGN', 'Kei Car N-WGN Custom',
                'Kei Car N-One', 'Compact Car Fit', 'Compact Car Fit Crosstar', 'Compact Car Freed',
                'Compact Car Freed+ (Plus)', 'MUNEEB', 'Sedan Civic', 'Sedan Civic e:HEV',
                'Sedan Accord', 'Sedan Grace (older)', 'Sedan Insight (older)', 'SUV Vezel (HR-V Japan)',
                'SUV ZR-V', 'SUV CR-V', 'SUV WR-V (new)', 'SUV CR-V e:HEV', 'SUV CR-V PHEV',
                'Minivan Step WGN', 'Minivan Step WGN Air', 'Minivan Step WGN Spada',
                'Minivan Odyssey (Japan limited)', 'Sports Civic Type R', 'Sports S660 (discontinued)',
                'Sports NSX (discontinued)', 'Electric e:Ny1 (Japan launch)', 'Electric Honda e (limited)',
                'Commercial N-Van', 'Commercial N-Van+ Style', 'Commercial Acty (older)'
            ],
            'MITSUBISHI': [
                'Kei Car eK Wagon', 'Kei Car eK X', 'Kei Car eK Space', 'Kei Car eK X Space',
                'Kei Car eK X EV', 'Kei Car Minicab MiEV (Electric)', 'Kei Car Minicab Truck',
                'Kei Car Minicab Van', 'Compact Delica Mini', 'Compact Mirage (limited availability)',
                'Compact Lancer (older)', 'SUV Outlander', 'SUV Outlander PHEV', 'SUV Eclipse Cross',
                'SUV Eclipse Cross PHEV', 'SUV RVR (ASX)', 'SUV Pajero (discontinued Japan)',
                'SUV Pajero Mini (older)', 'MPV Delica D:2', 'MPV Delica D:5',
                'Commercial Minicab Van', 'Commercial Minicab Truck', 'Commercial Delica Van'
            ],
            'VOLKSWAGEN': [
                'Hatchback Polo', 'Hatchback Golf', 'Hatchback Golf Variant', 'Hatchback Beetle (discontinued)',
                'Sedan Passat', 'Sedan Passat Variant', 'Sedan Arteon', 'Sedan Arteon Shooting Brake',
                'SUV T-Cross', 'SUV T-Roc', 'SUV Tiguan', 'SUV Tiguan Allspace', 'SUV Touareg',
                'EV ID.4', 'EV ID. Buzz (incoming / limited)', 'MPV Sharan (discontinued)',
                'MPV Touran (limited availability)'
            ],
            'BMW': [
                'Hatchback 1 Series', 'Sedan 2 Series Gran Coupe', 'Sedan 3 Series Sedan',
                'Sedan 3 Series Touring', 'Sedan 5 Series Sedan', 'Sedan 5 Series Touring',
                'Sedan 7 Series', 'Sedan i7 (Electric)', 'Sedan 8 Series Gran Coupe',
                'Coupe 2 Series Coupe', 'Coupe 4 Series Coupe', 'Coupe 8 Series Coupe',
                'Convertible 4 Series Convertible', 'Convertible 8 Series Convertible',
                'Convertible Z4 Roadster', 'SUV X1', 'SUV X2', 'SUV X3', 'SUV X3 M', 'SUV X4',
                'SUV X4 M', 'SUV X5', 'SUV X5 M', 'SUV X6', 'SUV X6 M', 'SUV X7',
                'SUV XM (Performance SUV)', 'Electric iX1', 'Electric iX2', 'Electric iX3',
                'Electric i4', 'Electric i5', 'Electric i7', 'Electric iX'
            ],
            'SUBARU': [
                'Kei Car Chiffon', 'Kei Car Chiffon Custom', 'Kei Car Stella', 'Kei Car Stella Custom',
                'Kei Car Pleo Plus', 'Kei Car Sambar Truck', 'Kei Car Sambar Van', 'Compact Justy',
                'Compact Impreza', 'Compact Impreza Sport', 'Compact Levorg', 'Compact Levorg Layback',
                'Sedan WRX S4', 'Sedan Legacy B4 (older)', 'SUV Forester', 'SUV Outback',
                'SUV Crosstrek', 'SUV XV (older)', 'SUV Ascent (Japan limited)', 'Sports BRZ',
                'Electric Solterra'
            ]
        }

        # Auction data
        auctions = [
            'USS – Used Car System Solutions', 'TAA – Toyota Auto Auction', 'JU Group',
            'ARAI AUCTION', 'CAA', 'HAA', 'NAA – Nissan Auto Auction', 'ZIP Osaka',
            'BCN Auction', 'Bay Auc', 'SAA – Subaru Auto Auction', 'LAA – Lexus Auto Auction',
            'USS Tokyo', 'TAA Tokyo', 'JU Tokyo', 'ARAI Oyama', 'CAA Chubu', 'HAA Kobe',
            'NAA Tokyo', 'ZIP Osaka (independent auction)', 'BCN Kansai', 'Bay Auc Tokyo',
            'SAA Tokyo', 'LAA Tokyo', 'USS Nagoya', 'TAA Yokohama', 'JU Saitama',
            'ARAI Bayside', 'CAA Tokyo', 'HAA Osaka', 'NAA Nagoya', 'BCN Tokyo',
            'Bay Auc Nagoya', 'SAA Nagoya', 'LAA Nagoya', 'USS Osaka', 'TAA Chubu',
            'JU Chiba', 'ARAI Sendai', 'CAA Gifu', 'NAA Osaka', 'SAA Osaka',
            'USS Yokohama', 'TAA Kansai', 'JU Kanagawa', 'NAA Kyushu', 'USS Sapporo',
            'TAA Kyushu', 'JU Aichi', 'USS Fukuoka', 'TAA Hokkaido', 'JU Fukuoka',
            'USS Kobe', 'TAA Hiroshima', 'JU Hokkaido', 'USS Tohoku', 'JU Hiroshima',
            'USS Shizuoka', 'JU Shizuoka', 'USS Gunma', 'JU Niigata', 'USS Niigata',
            'JU Gunma', 'USS Kyushu', 'JU Tochigi', 'USS Okayama', 'JU Miyagi'
        ]

        # Create car categories - handle unique company constraint
        created_categories = 0
        companies_created = set()
        
        for company, models in car_data.items():
            # First, create or get the company entry
            if company not in companies_created:
                try:
                    company_category, created = CarCategory.objects.get_or_create(
                        company=company,
                        defaults={'name': f'{company} Brand', 'user': user}
                    )
                    if created:
                        created_categories += 1
                        companies_created.add(company)
                except IntegrityError:
                    # Company already exists, get it
                    company_category = CarCategory.objects.filter(company=company).first()
                    companies_created.add(company)
            
            # Then create individual car models
            for model in models:
                try:
                    category, created = CarCategory.objects.get_or_create(
                        name=model,
                        defaults={'company': f'{company}_{model[:20]}', 'user': user}
                    )
                    if created:
                        created_categories += 1
                except IntegrityError:
                    # Skip if already exists
                    continue

        # Create auctions
        created_auctions = 0
        for auction_name in auctions:
            auction, created = Auction.objects.get_or_create(
                name=auction_name,
                defaults={'user': user}
            )
            if created:
                created_auctions += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_categories} car categories and {created_auctions} auctions'
            )
        )