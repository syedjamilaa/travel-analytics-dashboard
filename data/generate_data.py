import pandas as pd
import numpy as np
import sqlite3
import random
from faker import Faker
from datetime import datetime, timedelta
import os

fake = Faker()
np.random.seed(42)
random.seed(42)

print("🚀 Starting data generation...")

# ── CONFIG ──────────────────────────────────────────
N_USERS      = 5_000
N_PROPERTIES = 1_000
N_BOOKINGS   = 20_000
N_EVENTS     = 80_000   # funnel events (search/view/cart/book)
# ────────────────────────────────────────────────────


# ═══════════════════════════════════════════════════
# TABLE 1: USERS
# ═══════════════════════════════════════════════════
# Business logic:
#   - Mobile users will later show higher conversion (pattern)
#   - Mix of new vs returning users for cohort analysis

print("📋 Generating users...")

devices   = ['mobile', 'desktop', 'tablet']
# Mobile gets higher weight → drives the pattern we'll discover
device_weights = [0.55, 0.35, 0.10]

user_types = ['new', 'returning']

users = pd.DataFrame({
    'user_id':        range(1, N_USERS + 1),
    'name':           [fake.name()          for _ in range(N_USERS)],
    'email':          [fake.unique.email()  for _ in range(N_USERS)],
    'country':        [fake.country()       for _ in range(N_USERS)],
    'device':         np.random.choice(devices, N_USERS, p=device_weights),
    'user_type':      np.random.choice(user_types, N_USERS, p=[0.4, 0.6]),
    'signup_date':    [
        fake.date_between(start_date='-2y', end_date='today')
        for _ in range(N_USERS)
    ],
    'age':            np.random.randint(18, 65, N_USERS),
})

print(f"   ✅ {len(users):,} users created")


# ═══════════════════════════════════════════════════
# TABLE 2: PROPERTIES
# ═══════════════════════════════════════════════════
# Business logic:
#   - Top destinations get more properties (Pareto)
#   - Rating will correlate with cancellation rate later

print("🏨 Generating properties...")

# Top destinations get 60% of properties → Pareto revenue effect
top_destinations = [
    'Paris', 'New York', 'Tokyo', 'Dubai', 'London',
    'Bali', 'Barcelona', 'Singapore'
]
other_destinations = [
    'Berlin', 'Amsterdam', 'Sydney', 'Bangkok', 'Istanbul',
    'Rome', 'Toronto', 'Cape Town', 'Mumbai', 'Lisbon',
    'Prague', 'Vienna', 'Seoul', 'Mexico City', 'Zurich'
]

all_destinations = top_destinations + other_destinations

# 60% of properties in top 8 destinations
dest_weights = (
    [0.6 / len(top_destinations)]  * len(top_destinations) +
    [0.4 / len(other_destinations)] * len(other_destinations)
)

property_types = ['Hotel', 'Resort', 'Villa', 'Apartment', 'Hostel']

# Rating skewed toward higher values (realistic)
ratings = np.clip(np.random.normal(loc=3.8, scale=0.8, size=N_PROPERTIES), 1, 5)
ratings = np.round(ratings, 1)

properties = pd.DataFrame({
    'property_id':   range(1, N_PROPERTIES + 1),
    'name':          [fake.company() + ' ' + random.choice(['Hotel','Resort','Suites','Inn'])
                      for _ in range(N_PROPERTIES)],
    'destination':   np.random.choice(all_destinations, N_PROPERTIES, p=dest_weights),
    'property_type': np.random.choice(property_types, N_PROPERTIES,
                                       p=[0.4, 0.2, 0.15, 0.15, 0.1]),
    'rating':        ratings,
    'price_per_night': np.round(
                        np.random.lognormal(mean=4.8, sigma=0.6, size=N_PROPERTIES), 2
                     ),  # log-normal → realistic price spread
    'total_rooms':   np.random.randint(5, 300, N_PROPERTIES),
    'amenities':     [random.choice(['Pool,Gym,Spa', 'Pool,WiFi', 'Gym,WiFi',
                                     'Spa,Restaurant', 'WiFi only'])
                      for _ in range(N_PROPERTIES)],
})

print(f"   ✅ {len(properties):,} properties created")


# ═══════════════════════════════════════════════════
# TABLE 3: BOOKINGS
# ═══════════════════════════════════════════════════
# Business logic:
#   - Top destinations get disproportionate revenue (Pareto)
#   - Low-rated properties → higher cancellation rate
#   - Weekend check-ins → higher prices (time variation)
#   - Mobile users → slightly lower avg booking value
#     but higher volume

print("📅 Generating bookings...")

statuses = ['confirmed', 'cancelled', 'completed']
booking_records = []

# Pre-compute which properties are "top destination"
top_dest_mask = properties['destination'].isin(top_destinations).values
top_dest_ids  = properties[top_dest_mask]['property_id'].tolist()
other_dest_ids= properties[~top_dest_mask]['property_id'].tolist()

for i in range(1, N_BOOKINGS + 1):
    user_id = random.randint(1, N_USERS)
    user    = users[users['user_id'] == user_id].iloc[0]

    # Pareto: 70% of bookings go to top destinations
    if random.random() < 0.70:
        prop_id = random.choice(top_dest_ids)
    else:
        prop_id = random.choice(other_dest_ids)

    prop    = properties[properties['property_id'] == prop_id].iloc[0]

    # Date range: last 2 years
    checkin = fake.date_between(start_date='-2y', end_date='today')
    nights  = random.randint(1, 14)
    checkout= checkin + timedelta(days=nights)

    # Weekend premium (+20% price)
    is_weekend = checkin.weekday() >= 5
    price_mult = 1.2 if is_weekend else 1.0

    total_price = round(prop['price_per_night'] * nights * price_mult, 2)

    # Cancellation logic: low-rated properties cancel more
    rating = prop['rating']
    if rating < 3.0:
        cancel_prob = 0.45   # 45% cancellation for poor properties
    elif rating < 4.0:
        cancel_prob = 0.20
    else:
        cancel_prob = 0.08   # Only 8% for top-rated

    rand = random.random()
    if rand < cancel_prob:
        status = 'cancelled'
    elif rand < cancel_prob + 0.15:
        status = 'confirmed'
    else:
        status = 'completed'

    booking_records.append({
        'booking_id':   i,
        'user_id':      user_id,
        'property_id':  prop_id,
        'destination':  prop['destination'],
        'checkin_date': checkin,
        'checkout_date':checkout,
        'nights':       nights,
        'total_price':  total_price,
        'status':       status,
        'device':       user['device'],
        'is_weekend':   int(is_weekend),
    })

bookings = pd.DataFrame(booking_records)
print(f"   ✅ {len(bookings):,} bookings created")


# ═══════════════════════════════════════════════════
# TABLE 4: EVENTS (Funnel Tracking)
# ═══════════════════════════════════════════════════
# Business logic:
#   - Funnel: search → view → cart → booking
#   - Each step has realistic drop-off rates
#   - Mobile users drop off less (higher conversion)
#   - This table powers the funnel chart

print("🔍 Generating funnel events...")

funnel_steps = ['search', 'view', 'cart', 'booking']

# Drop-off rates PER STEP (what % continue to next step)
# Desktop:  search→view 60%, view→cart 35%, cart→booking 40%
# Mobile:   search→view 65%, view→cart 42%, cart→booking 52%
conversion_rates = {
    'desktop': [1.0, 0.60, 0.35, 0.40],
    'mobile':  [1.0, 0.65, 0.42, 0.52],
    'tablet':  [1.0, 0.62, 0.37, 0.44],
}

event_records = []
event_id = 1
target_events = N_EVENTS

sessions_needed = target_events // 4  # rough estimate

for _ in range(sessions_needed):
    user_id = random.randint(1, N_USERS)
    device  = users[users['user_id'] == user_id]['device'].values[0]
    rates   = conversion_rates[device]

    event_time = fake.date_time_between(start_date='-2y', end_date='now')

    for step_idx, step in enumerate(funnel_steps):
        if random.random() <= rates[step_idx]:
            event_records.append({
                'event_id':   event_id,
                'user_id':    user_id,
                'event_type': step,
                'device':     device,
                'timestamp':  event_time + timedelta(minutes=step_idx * random.randint(1, 10)),
                'destination': random.choice(all_destinations),
            })
            event_id += 1
        else:
            break  # user dropped off — no further steps recorded

events = pd.DataFrame(event_records)
print(f"   ✅ {len(events):,} events created")


# ═══════════════════════════════════════════════════
# LOAD INTO SQLITE
# ═══════════════════════════════════════════════════

print("\n💾 Loading into SQLite database...")

db_path = os.path.join(os.path.dirname(__file__), 'travel.db')
conn    = sqlite3.connect(db_path)

users.to_sql('users',       conn, if_exists='replace', index=False)
properties.to_sql('properties', conn, if_exists='replace', index=False)
bookings.to_sql('bookings', conn, if_exists='replace', index=False)
events.to_sql('events',     conn, if_exists='replace', index=False)

conn.close()

# ── Summary ──
total = len(users) + len(properties) + len(bookings) + len(events)
print(f"""
╔══════════════════════════════════════╗
║        DATA GENERATION COMPLETE      ║
╠══════════════════════════════════════╣
║  users       : {len(users):>8,} rows          ║
║  properties  : {len(properties):>8,} rows          ║
║  bookings    : {len(bookings):>8,} rows          ║
║  events      : {len(events):>8,} rows          ║
╠══════════════════════════════════════╣
║  TOTAL ROWS  : {total:>8,} rows          ║
║  Database    : data/travel.db        ║
╚══════════════════════════════════════╝
""")