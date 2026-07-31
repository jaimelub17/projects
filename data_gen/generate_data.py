"""Generates synthetic seed data for the Oura Corporate Scorecard project.

Not real Oura data. Volumes and growth are scaled to loosely track Oura's
real 2024-2025 trajectory (~2x YoY revenue). random.seed(42) makes output
reproducible.

Structure (v3 -- rebuilt after the Step 11 realism audit):
  1. Orders are generated FIRST, chronologically, from the growth curve.
  2. Customers are DERIVED from orders -- ~90% of orders create a new
     customer, ~10% are repeat purchases (upgrades/gifts, biased toward
     early customers, who realistically upgrade Gen3 -> Ring 4). This gives
     ~1.1 orders per customer, matching real ring-buyer behavior. The v2
     generator instead scattered 21K orders over a fixed pool of 2,000
     customers (10.2 orders each -- absurd) which also silently capped the
     subscription business at ~1% of revenue instead of Oura's real ~20%.
  3. signup_date = the customer's first order date, and subscriptions
     attach 0-30 days AFTER that first ring purchase (a membership without
     a ring makes no sense) at a ~90% attach rate, matching Oura's
     reportedly very high real attach. Churn follows a retention/hazard
     curve (highest risk in months 1-2, 2% floor after month 6).
  4. A small, controlled set of data-quality issues (nulls, duplicates,
     orphaned foreign keys, bad values) is injected on purpose, at known
     rates, so the dbt staging layer and tests have real problems to catch.

Known honest deviation: our 2025 subscription revenue share lands around
~8-12%, not Oura's real ~20% -- their share reflects membership cohorts
accumulated over many more years than this 2-year window. Documented in
SCHEMA.md rather than distorting other numbers to force it.
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

SEEDS_DIR = Path(__file__).resolve().parent.parent / "dbt" / "seeds"
SEEDS_DIR.mkdir(parents=True, exist_ok=True)

START_DATE = date(2024, 1, 1)
END_DATE = date(2025, 12, 31)

SUBSCRIPTION_PRICE = 5.99
REPEAT_PURCHASE_RATE = 0.10    # ~10% of orders are an existing customer buying again
SUBSCRIBER_ATTACH_RATE = 0.90  # share of customers who start a membership after buying

# Intentional data-quality injection rates (documented in SCHEMA.md).
DQ_NULL_GEO_RATE = 0.01           # orders missing geo tag (channel integration gap)
DQ_DUP_ORDER_RATE = 0.005         # exact duplicate order rows (pipeline replay bug)
DQ_ORPHAN_CUSTOMER_RATE = 0.003   # orders referencing a customer not yet synced
DQ_BAD_VALUE_RATE = 0.002         # nonsensical quantity/price (entry glitch)
DQ_NULL_CHANNEL_RATE = 0.005      # customers missing acquisition channel
DQ_DUP_SIGNUP_RATE = 0.01         # duplicate signup events (webhook double-fire)
DQ_ORPHAN_CLAIM_RATE = 0.01       # warranty claims referencing an unsynced order

GEOS = [  # geo_id, country, region, state
    (1, "United States", "West", "CA"),
    (2, "United States", "West", "WA"),
    (3, "United States", "East", "NY"),
    (4, "United States", "East", "MA"),
    (5, "United States", "Central", "TX"),
    (6, "Canada", "North America", "ON"),
    (7, "United Kingdom", "Europe", ""),
    (8, "Germany", "Europe", ""),
    (9, "Australia", "Oceania", ""),
]
GEO_WEIGHTS = [30, 15, 20, 10, 15, 5, 8, 5, 2]

CHANNELS = [  # channel_id, channel_name
    (1, "D2C Web"),
    (2, "Amazon"),
    (3, "Target"),
    (4, "Best Buy"),
    (5, "International Retail"),
]
CHANNEL_WEIGHTS = [35, 30, 15, 10, 10]

# product_id, ring_model, color, list_price, unit_cost
# unit_cost set for ~57% gross margin, benchmarked against Garmin's Fitness
# segment gross margin of 59% (Q4 2025 10-K) -- Oura doesn't file public
# financials, so a public wearables comparable is the closest grounding
# available. See SCHEMA.md "Modeling assumptions" for the source.
PRODUCTS = [
    (1, "Gen3", "Silver", 299.00, 129.00),
    (2, "Gen3", "Black", 299.00, 129.00),
    (3, "Gen3", "Gold", 329.00, 142.00),
    (4, "Ring 4", "Silver", 349.00, 150.00),
    (5, "Ring 4", "Black", 349.00, 150.00),
    (6, "Ring 4", "Brushed Titanium", 499.00, 215.00),
]
PRODUCT_WEIGHTS = [15, 15, 10, 25, 25, 10]
PRODUCT_BY_ID = {p[0]: p for p in PRODUCTS}

dq_counts = {}  # tracks how many rows each DQ rule actually touched


def write_csv(filename, header, rows):
    path = SEEDS_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  wrote {len(rows):>6} rows -> {path.name}")


def month_growth_factor(d: date) -> float:
    """~5.95%/month compounding (1.0595^12 ~= 2.0x/yr, matching Oura's real
    ~2x YoY revenue growth), plus a Nov/Dec seasonality bump."""
    months_elapsed = (d.year - START_DATE.year) * 12 + (d.month - START_DATE.month)
    growth = 1.0595 ** months_elapsed
    seasonal = 1.6 if d.month in (11, 12) else 1.0
    return growth * seasonal


def churn_hazard(tenure_months: int) -> float:
    """Retention curve: churn risk is highest in a subscriber's first couple
    months and declines with tenure -- the real shape of subscription churn,
    not a flat monthly coin-flip."""
    if tenure_months <= 1:
        return 0.12
    if tenure_months == 2:
        return 0.08
    if tenure_months == 3:
        return 0.06
    if tenure_months <= 6:
        return 0.04
    return 0.02


# ---------- dimensions ----------

write_csv("seed_geo.csv", ["geo_id", "country", "region", "state"], GEOS)
write_csv("seed_channels.csv", ["channel_id", "channel_name"], CHANNELS)
write_csv(
    "seed_products.csv",
    ["product_id", "ring_model", "color", "list_price", "unit_cost"],
    PRODUCTS,
)

# ---------- phase 1: orders, chronological, customer unassigned ----------

orders = []  # [order_id, customer_id, product_id, order_date_iso, geo_id, channel_id, qty, unit_price, unit_cost, discount]
order_id = 1
d = START_DATE
BASELINE_ORDERS_PER_DAY = 12
while d <= END_DATE:
    n_orders = max(0, round(random.gauss(BASELINE_ORDERS_PER_DAY * month_growth_factor(d), 3)))
    for _ in range(n_orders):
        product_id = random.choices([p[0] for p in PRODUCTS], weights=PRODUCT_WEIGHTS)[0]
        _, _, _, list_price, unit_cost = PRODUCT_BY_ID[product_id]
        quantity = 1 if random.random() < 0.92 else 2
        discount_pct = random.choices([0, 0.10, 0.15], weights=[75, 15, 10])[0]
        geo_id = random.choices([g[0] for g in GEOS], weights=GEO_WEIGHTS)[0]
        channel_id = random.choices([c[0] for c in CHANNELS], weights=CHANNEL_WEIGHTS)[0]
        unit_price = round(list_price * (1 - discount_pct), 2)
        orders.append(
            [
                order_id,
                None,  # customer assigned in phase 2
                product_id,
                d.isoformat(),
                geo_id,
                channel_id,
                quantity,
                unit_price,
                unit_cost,
                round(list_price - unit_price, 2),
            ]
        )
        order_id += 1
    d += timedelta(days=1)

# ---------- phase 2: customers DERIVED from orders ----------
# Orders are chronological, so a "repeat" draw from existing ids naturally
# skews toward early customers -- who realistically upgrade Gen3 -> Ring 4.

customers = []  # [customer_id, signup_date_iso, geo_id, acquisition_channel_id]
next_customer_id = 1
for o in orders:
    if customers and random.random() < REPEAT_PURCHASE_RATE:
        o[1] = random.randint(1, next_customer_id - 1)
    else:
        cid = next_customer_id
        next_customer_id += 1
        # customer's home geo + acquisition channel come from their first order
        customers.append([cid, o[3], o[4], o[5]])
        o[1] = cid

# ---------- phase 3: subscriptions, anchored to the FIRST RING PURCHASE ----------

sub_events = []
event_id = 1
for cid, signup_date_str, _geo, _ch in customers:
    if random.random() > SUBSCRIBER_ATTACH_RATE:
        continue
    first_order_dt = date.fromisoformat(signup_date_str)
    sub_start = first_order_dt + timedelta(days=random.randint(0, 30))
    if sub_start > END_DATE:
        continue
    sub_events.append([event_id, cid, sub_start.isoformat(), "signup", SUBSCRIPTION_PRICE, SUBSCRIPTION_PRICE])
    event_id += 1

    cursor = sub_start
    tenure_months = 0
    while True:
        cursor = cursor + timedelta(days=30)
        tenure_months += 1
        if cursor > END_DATE:
            break
        if random.random() < churn_hazard(tenure_months):
            sub_events.append([event_id, cid, cursor.isoformat(), "cancel", SUBSCRIPTION_PRICE, -SUBSCRIPTION_PRICE])
            event_id += 1
            break

# ---------- phase 4: DQ injection into orders ----------

for row in orders:
    if random.random() < DQ_NULL_GEO_RATE:
        row[4] = ""
        dq_counts["orders_null_geo"] = dq_counts.get("orders_null_geo", 0) + 1
    if random.random() < DQ_ORPHAN_CUSTOMER_RATE:
        row[1] = 90000 + random.randint(1, 500)  # references a customer_id that doesn't exist
        dq_counts["orders_orphan_customer"] = dq_counts.get("orders_orphan_customer", 0) + 1
    if random.random() < DQ_BAD_VALUE_RATE:
        if random.random() < 0.5:
            row[6] = 0  # zero quantity: entry glitch
        else:
            row[7] = 0.0  # zero unit_price: comp/free unit logged wrong
        dq_counts["orders_bad_value"] = dq_counts.get("orders_bad_value", 0) + 1

dup_candidates = random.sample(orders, k=int(len(orders) * DQ_DUP_ORDER_RATE))
for row in dup_candidates:
    orders.append(list(row))
dq_counts["orders_duplicated"] = len(dup_candidates)

write_csv(
    "seed_orders.csv",
    [
        "order_id",
        "customer_id",
        "product_id",
        "order_date",
        "geo_id",
        "channel_id",
        "quantity",
        "unit_price",
        "unit_cost",
        "discount_amount",
    ],
    orders,
)

# ---------- phase 5: claims from orders (post-injection, like a real messy pipeline) ----------

claims = []
claim_id = 1
CLAIM_RATE = 0.03
for o in orders:
    if random.random() > CLAIM_RATE:
        continue
    order_id_, _, product_id, order_date_str, *_rest = o
    unit_price = o[7]
    unit_cost = o[8]
    order_dt = date.fromisoformat(order_date_str)
    claim_dt = order_dt + timedelta(days=random.randint(10, 45))
    if claim_dt > END_DATE:
        claim_dt = END_DATE
    claim_type = random.choices(["warranty", "return"], weights=[70, 30])[0]
    if claim_type == "warranty":
        resolution = random.choice(["replaced", "repaired"])
        cost_to_company = unit_cost
    else:
        resolution = "refunded"
        cost_to_company = unit_price
    ref_order_id = order_id_
    if random.random() < DQ_ORPHAN_CLAIM_RATE:
        ref_order_id = 900000 + random.randint(1, 500)  # claim logged before order fully synced
        dq_counts["claims_orphan_order"] = dq_counts.get("claims_orphan_order", 0) + 1
    claims.append([claim_id, ref_order_id, claim_dt.isoformat(), claim_type, resolution, cost_to_company])
    claim_id += 1

write_csv(
    "seed_returns_warranty.csv",
    ["claim_id", "order_id", "claim_date", "claim_type", "resolution", "cost_to_company"],
    claims,
)

# ---------- phase 6: DQ injection into customers + subscriptions, then write ----------

for row in customers:
    if random.random() < DQ_NULL_CHANNEL_RATE:
        row[3] = ""
        dq_counts["customers_null_channel"] = dq_counts.get("customers_null_channel", 0) + 1

write_csv(
    "seed_customers.csv",
    ["customer_id", "signup_date", "geo_id", "acquisition_channel_id"],
    customers,
)

signup_rows = [r for r in sub_events if r[3] == "signup"]
dup_signups = random.sample(signup_rows, k=int(len(signup_rows) * DQ_DUP_SIGNUP_RATE))
for row in dup_signups:
    sub_events.append(list(row))  # exact duplicate, including event_id -> uniqueness test target
dq_counts["subscriptions_duplicated_signup"] = len(dup_signups)

write_csv(
    "seed_subscription_events.csv",
    ["event_id", "customer_id", "event_date", "event_type", "plan_price", "mrr_delta"],
    sub_events,
)

# ---------- summary ----------

n_subscribers = len({r[1] for r in sub_events if r[3] == "signup"})
print(f"\nDone. Orders: {len(orders)} | Customers: {len(customers)} "
      f"({len(orders)/len(customers):.2f} orders/customer)")
print(f"Subscribers: {n_subscribers} ({100*n_subscribers/len(customers):.0f}% attach) "
      f"| Subscription events: {len(sub_events)} | Claims: {len(claims)}")
print("\nInjected data-quality issues (by design, for dbt tests to catch):")
for k, v in sorted(dq_counts.items()):
    print(f"  {k}: {v}")
