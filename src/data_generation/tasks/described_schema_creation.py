import json
import random
import string

from data_generation.tasks.base_task import BaseDataTask

_FREE_FORM_CHANCE = 0.3  # probability that any given seed is replaced with an open-ended constraint

_FIRST_NAMES = [
    "Alice", "Bob", "Carlos", "Diana", "Erik", "Fatima", "George", "Hannah",
    "Ivan", "Julia", "Kevin", "Laura", "Mohammed", "Nina", "Oscar", "Priya",
    "Quinn", "Rachel", "Samuel", "Tina", "Umar", "Vera", "William", "Xena",
    "Yusuf", "Zoe", "Aisha", "Benjamin", "Camille", "David", "Elena", "Felix",
    "Grace", "Hiroshi", "Ingrid", "James", "Kofi", "Lena", "Marcus", "Nadia",
    "Oliver", "Petra", "Raj", "Sofia", "Thomas", "Uma", "Viktor", "Wendy",
    "Xiulan", "Yasmin", "Andrei", "Beatriz", "Chen", "Daria", "Emeka",
    "Francesca", "Giulio", "Hana", "Ibrahim", "Jade", "Karim", "Leila",
    "Mateo", "Nour", "Olusegun", "Pilar", "Ravi", "Svetlana", "Tariq",
    "Ursula", "Valeria", "Winston", "Xander", "Yolanda", "Zeynep", "Aaron",
    "Brigitte", "Ciro", "Desiree", "Edouard", "Florencia", "Gideon", "Hyun",
    "Ines", "Jonas", "Khadija", "Lorenzo", "Miriam", "Niels", "Olga",
    "Pascal", "Renata", "Serge", "Tamara", "Ulrich", "Vivek", "Wanjiru",
    "Xochitl", "Yannick", "Zara",
]
_LAST_NAMES = [
    "Smith", "Chen", "Garcia", "Okafor", "Patel", "Kim", "Müller", "Silva",
    "Rossi", "Tanaka", "Nguyen", "Ali", "Brown", "Johansson", "Cohen",
    "Fernandez", "Ivanova", "Park", "Andersen", "Dubois", "Nakamura", "Osei",
    "Petrov", "Reyes", "Svensson", "Torres", "Ueda", "Vasquez", "Wang",
    "Yamamoto", "Zhang", "Abubakar", "Bergmann", "Castro", "Diallo", "Endo",
    "Fischer", "Gonzalez", "Hernandez", "Ishikawa", "Jensen", "Kimura",
    "Lopez", "Martinez", "Nkrumah", "Olsen", "Papadopoulos", "Queiroz",
    "Romero", "Santos", "Takahashi", "Ustinov", "Villanueva", "Wilson",
    "Xu", "Yilmaz", "Zuberi", "Abbas", "Bautista", "Cardoso", "Dlamini",
    "Eriksson", "Fourie", "Gupta", "Halvorsen", "Ito", "Jovanovic", "Kraft",
    "Lima", "Mensah", "Navarro", "Okeke", "Popescu", "Ramos", "Schneider",
    "Tran", "Usman", "Vidal", "Watanabe", "Xie", "Yoo", "Zawadzki",
    "Amara", "Björk", "Cortez", "Dube", "Esposito", "Ferreira", "Gomes",
    "Hassan", "Ibarra", "Johansson", "Kato", "Larsson", "Moreau", "Nielsen",
    "Ozturk", "Pereira", "Ruiz", "Sousa", "Tremblay", "Volkov",
]
_COMPANIES = [
    "Acme Corp", "Globex", "Initech", "Umbrella Ltd", "Stark Industries",
    "Wayne Enterprises", "Oscorp", "Massive Dynamic", "Soylent Corp",
    "Cyberdyne Systems", "Weyland-Yutani", "Tyrell Corp", "Aperture Science",
    "Black Mesa", "Nakatomi Trading", "Gekko & Co", "Dunder Mifflin",
    "Vandelay Industries", "Prestige Worldwide", "Bluth Company",
    "Sabre Corp", "Goliath National Bank", "Pied Piper", "Hooli",
    "Vehement Capital", "Gringotts Bank", "Veridian Dynamics",
    "Momcorp", "Planet Express", "Sombra Technology", "Abstergo Industries",
    "Vault-Tec", "OCP", "Rekall Inc", "Genco Pura", "Oceanic Airlines",
    "Dharma Initiative", "Virtucon", "Strickland Propane", "Dinoco",
    "Nomanisan Corp", "Virtucon", "Pendant Publishing", "Bambino Ltd",
    "Pembrooke Industries", "Stratton Oakmont", "Praxis Corp",
    "Enkidu Software", "Meadow Creek Holdings", "Solaris Systems",
    "Meridian Analytics", "Northgate Logistics", "Silverline Consulting",
    "Quantum Dynamics", "Nexus Technologies", "Apex Solutions",
    "Horizon Ventures", "Cascade Networks", "Summit Digital",
    "Redwood Labs", "Ironclad Security", "Ember Finance", "Cobalt Health",
    "Drift Media", "Anchor Insurance", "Mosaic Architecture", "Sprout Farms",
    "Forge Manufacturing", "Tidal Energy", "Crest Biotech", "Fulcrum Law",
    "Lattice Robotics", "Prism Design", "Alloy Metals", "Basin Resources",
    "Canopy Retail", "Depot Logistics", "Ember Capital", "Flint Mining",
    "Grove Properties", "Harbor Marine", "Isle Travel", "Jade Textiles",
    "Knoll Furniture", "Ledge Construction", "Maple Foods", "Nimbus Cloud",
    "Orbit Aerospace", "Plank Timber", "Ridge Pharmaceuticals", "Shore Hotels",
    "Tide Renewable", "Uplift Education", "Vale Agriculture", "Wick Publishing",
    "Xcel Rail", "Yard Nurseries", "Zenith Electronics",
]
_PRODUCTS = [
    "wireless headphones", "standing desk", "ergonomic chair", "laptop bag",
    "mechanical keyboard", "USB-C hub", "monitor arm", "webcam",
    "noise-cancelling earbuds", "portable charger", "smart watch",
    "fitness tracker", "tablet case", "phone stand", "LED desk lamp",
    "coffee grinder", "espresso machine", "blender", "air fryer", "instant pot",
    "running shoes", "backpack", "winter jacket", "yoga mat", "water bottle",
    "bicycle helmet", "camping tent", "sleeping bag", "hiking boots",
    "sunglasses", "wallet", "leather belt", "rain jacket", "duffel bag",
    "electric scooter", "skateboard", "surf board", "tennis racket",
    "basketball", "golf clubs", "ski goggles", "climbing harness",
    "road bike", "mountain bike frame", "kayak paddle", "snorkel set",
    "drone", "action camera", "tripod", "printer ink cartridge",
    "external SSD", "gaming mouse", "VR headset", "smart speaker",
    "robot vacuum", "air purifier", "humidifier", "electric toothbrush",
    "blood pressure monitor", "thermometer", "first aid kit", "sunscreen",
    "face moisturizer", "shampoo set", "beard trimmer", "hair dryer",
    "cutting board", "chef's knife", "cast iron skillet", "wine glasses",
    "lunch box", "reusable bags", "plant pot", "garden hose",
    "power drill", "tape measure", "level tool", "paint roller",
    "floor tiles", "door handle", "smoke detector", "surge protector",
]
_DATES = [
    "2024-01-15", "2024-02-28", "2024-03-10", "2024-04-22", "2024-05-05",
    "2024-06-18", "2024-07-30", "2024-08-14", "2024-09-03", "2024-10-27",
    "2024-11-11", "2024-12-25", "2025-01-08", "2025-02-14", "2025-03-21",
    "2025-04-07", "2025-05-19", "2025-06-02", "2025-07-16", "2025-08-29",
    "2023-03-15", "2023-05-22", "2023-07-04", "2023-09-30", "2023-11-17",
    "2022-02-01", "2022-04-13", "2022-06-06", "2022-08-20", "2022-10-31",
]

_CITIES = [
    "New York", "London", "Tokyo", "São Paulo", "Berlin", "Lagos", "Sydney",
    "Mumbai", "Toronto", "Paris", "Seoul", "Cairo", "Amsterdam", "Nairobi",
    "Buenos Aires", "Mexico City", "Jakarta", "Istanbul", "Karachi", "Dhaka",
    "Manila", "Osaka", "Beijing", "Shanghai", "Los Angeles", "Chicago",
    "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego",
    "Dallas", "San Jose", "Austin", "Jacksonville", "Madrid", "Barcelona",
    "Rome", "Milan", "Vienna", "Prague", "Warsaw", "Budapest", "Bucharest",
    "Stockholm", "Copenhagen", "Helsinki", "Oslo", "Zurich", "Brussels",
    "Lisbon", "Athens", "Dublin", "Edinburgh", "Manchester", "Birmingham",
    "Lyon", "Marseille", "Hamburg", "Munich", "Cologne", "Frankfurt",
    "Kyiv", "Minsk", "Riga", "Tallinn", "Vilnius", "Tbilisi", "Baku",
    "Yerevan", "Almaty", "Tashkent", "Tehran", "Baghdad", "Riyadh",
    "Dubai", "Beirut", "Amman", "Casablanca", "Tunis", "Accra", "Dakar",
    "Abidjan", "Kampala", "Dar es Salaam", "Addis Ababa", "Kinshasa",
    "Johannesburg", "Cape Town", "Pretoria", "Luanda", "Khartoum",
    "Guangzhou", "Shenzhen", "Chengdu", "Wuhan", "Kolkata", "Chennai",
    "Bangalore", "Hyderabad", "Lahore", "Colombo", "Kathmandu", "Yangon",
    "Bangkok", "Kuala Lumpur", "Singapore", "Ho Chi Minh City", "Hanoi",
]


class DescribedSchemaCreationTask(BaseDataTask):

    # ── seed helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _free_form():
        return random.random() < _FREE_FORM_CHANCE

    @staticmethod
    def _rand_letter():
        return random.choice(string.ascii_uppercase)

    @staticmethod
    def _rand_length(lo, hi):
        return random.randint(lo, hi)

    def _seed_name(self):
        if self._free_form():
            letter = self._rand_letter()
            length = self._rand_length(5, 12)
            return f"a person whose first name starts with '{letter}' and is {length} characters long"
        return f"{random.choice(_FIRST_NAMES)} {random.choice(_LAST_NAMES)}"

    def _seed_city(self):
        if self._free_form():
            letter = self._rand_letter()
            return f"a city name starting with the letter '{letter}'"
        return random.choice(_CITIES)

    def _seed_company(self):
        if self._free_form():
            letter = self._rand_letter()
            length = self._rand_length(6, 14)
            return f"a company name starting with '{letter}' and {length} characters long"
        return random.choice(_COMPANIES)

    def _seed_product(self):
        if self._free_form():
            letter = self._rand_letter()
            return f"a product name starting with the letter '{letter}'"
        return random.choice(_PRODUCTS)

    def _seed_date(self):
        if self._free_form():
            year = random.randint(2020, 2025)
            return f"a date in {year}"
        return random.choice(_DATES)

    def _seed_amount(self):
        if self._free_form():
            lo = random.choice([1, 10, 100, 1000])
            hi = lo * random.randint(5, 50)
            return f"an amount between {lo} and {hi}"
        return random.randint(1, 9999)

    def generate(self, schema_path, llm_provider, max_retries):
        """Returns (messages, valid_json_str) or None."""
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        description = self._resolve_description(schema, llm_provider)
        initial_messages = self._build_described_schema_creation_prompt(schema, description)
        result = self._run_fix_loop(schema, initial_messages, llm_provider, max_retries)
        if result is None:
            return None
        valid_json_str, messages = result
        return messages, valid_json_str

    def _resolve_description(self, schema, llm_provider):
        seeds = {
            "name": self._seed_name(),
            "city": self._seed_city(),
            "company": self._seed_company(),
            "product": self._seed_product(),
            "date": self._seed_date(),
            "amount": self._seed_amount(),
        }
        seed_hint = (
            "Use these seed values where they fit the schema "
            "(ignore ones that don't apply): "
            + ", ".join(f"{k}={v}" for k, v in seeds.items())
            + "."
        )

        schema_context = ""
        meta = [schema.get("title", ""), schema.get("description", "")]
        combined = " — ".join(p for p in meta if p).strip()
        if combined:
            schema_context = f"Schema summary: {combined}\n\n"

        prompt = [{
            "role": "user",
            "content": (
                f"{schema_context}"
                f"Schema:\n{json.dumps(schema, indent=2)}\n\n"
                f"Write one short sentence describing a specific fictional instance of this data. "
                f"{seed_hint} "
                "Invent any remaining values as needed. "
                "Phrase it as an instruction, e.g. 'Create a user record for Peter Piper "
                "with email pp@mail.com whose account is active.' "
                "Output only the sentence, nothing else."
            ),
        }]
        desc, _ = llm_provider.generate(prompt)
        return desc.strip()
