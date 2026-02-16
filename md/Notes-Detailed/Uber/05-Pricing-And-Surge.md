# UBER SYSTEM DESIGN
*Chapter 5: Dynamic Pricing and Surge*

Dynamic pricing (surge) is controversial but essential for balancing
supply and demand. This chapter covers how surge pricing works, its
algorithms, and implementation challenges.

## SECTION 5.1: WHY DYNAMIC PRICING?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE SUPPLY-DEMAND PROBLEM                                            |
|                                                                         |
|  Normal conditions:                                                    |
|  --------------------                                                   |
|  Riders: 1,000/hour      Drivers: 1,200 available                    |
|  > Everyone gets a ride quickly                                      |
|                                                                         |
|  High demand (concert ends, rain, New Year's Eve):                   |
|  ------------------------------------------------                       |
|  Riders: 5,000/hour      Drivers: 1,200 available                    |
|  > Wait times spike to 30+ minutes                                   |
|  > Rider satisfaction drops                                          |
|  > Drivers overwhelmed                                               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  HOW SURGE HELPS                                                       |
|                                                                         |
|  1. DEMAND REDUCTION                                                   |
|     * Higher prices > some riders wait or use alternatives          |
|     * Demand drops from 5,000 to 3,000                               |
|                                                                         |
|  2. SUPPLY INCREASE                                                    |
|     * Higher earnings > more drivers come online                    |
|     * Drivers in nearby areas drive to surge zone                   |
|     * Supply increases from 1,200 to 2,000                          |
|                                                                         |
|  3. MARKET EQUILIBRIUM                                                 |
|     * Price adjusts until supply ≈ demand                           |
|     * Wait times stay reasonable (5-10 min)                         |
|                                                                         |
|  WITHOUT SURGE:                    WITH SURGE:                        |
|                                                                         |
|  Demand: ████████████████████     Demand: ████████████               |
|  Supply: ████████                 Supply: █████████████             |
|          ^                                ^                           |
|          Gap (30 min wait)                Balanced (5 min)           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.2: SURGE MULTIPLIER CALCULATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BASIC FORMULA                                                         |
|                                                                         |
|  surge_multiplier = f(demand, supply)                                 |
|                                                                         |
|  Simple approach:                                                      |
|  -----------------                                                      |
|                                                                         |
|  demand_supply_ratio = active_requests / available_drivers           |
|                                                                         |
|  if ratio < 1.0:                                                      |
|      surge = 1.0  (no surge)                                         |
|  elif ratio < 2.0:                                                    |
|      surge = 1.0 + (ratio - 1.0) * 0.5  (1.0x to 1.5x)             |
|  elif ratio < 4.0:                                                    |
|      surge = 1.5 + (ratio - 2.0) * 0.5  (1.5x to 2.5x)             |
|  else:                                                                 |
|      surge = min(ratio * 0.6, 5.0)  (cap at 5.0x)                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  METRICS USED                                                          |
|                                                                         |
|  DEMAND INDICATORS:                                                    |
|  * Active ride requests in area                                      |
|  * App opens (riders checking prices)                                |
|  * Predicted demand (ML model)                                       |
|  * Event data (concert ending, game ending)                         |
|                                                                         |
|  SUPPLY INDICATORS:                                                    |
|  * Available drivers in area                                         |
|  * Drivers en route to area                                          |
|  * Average ETA in area                                               |
|  * Driver acceptance rate                                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  ADVANCED FORMULA (ML-Based)                                          |
|                                                                         |
|  def calculate_surge(zone_id, current_time):                         |
|      # Get real-time metrics                                         |
|      requests = count_active_requests(zone_id)                       |
|      drivers = count_available_drivers(zone_id)                      |
|      avg_eta = get_average_eta(zone_id)                              |
|      acceptance_rate = get_acceptance_rate(zone_id)                  |
|                                                                         |
|      # Historical patterns                                            |
|      historical_surge = get_historical_surge(                        |
|          zone_id,                                                      |
|          day_of_week=current_time.weekday(),                         |
|          hour=current_time.hour                                       |
|      )                                                                 |
|                                                                         |
|      # Event adjustments                                              |
|      events = get_nearby_events(zone_id, current_time)               |
|      event_factor = calculate_event_impact(events)                   |
|                                                                         |
|      # Weather impact                                                 |
|      weather = get_weather(zone_id)                                  |
|      weather_factor = 1.0 + (0.3 if weather.is_raining else 0)      |
|                                                                         |
|      # Combine factors                                                |
|      base_surge = max(1.0, requests / max(drivers, 1))              |
|      eta_factor = 1.0 + max(0, (avg_eta - 5) / 10)  # penalize >5min|
|                                                                         |
|      surge = (                                                         |
|          base_surge *                                                  |
|          historical_surge *                                           |
|          event_factor *                                               |
|          weather_factor *                                             |
|          (1.0 / acceptance_rate)  # low acceptance = high demand    |
|      )                                                                 |
|                                                                         |
|      # Apply caps and smoothing                                       |
|      return smooth_surge(zone_id, min(surge, MAX_SURGE))             |
|                                                                         |
|  MAX_SURGE typically 5.0x to 8.0x depending on market               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.3: SURGE ZONES (GEOFENCING)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY ZONES?                                                            |
|                                                                         |
|  Surge varies by location:                                            |
|  * Airport surging, downtown normal                                  |
|  * Stadium area surging, suburbs normal                              |
|                                                                         |
|  Need to divide city into zones for localized pricing.               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  ZONE DEFINITION APPROACHES                                           |
|                                                                         |
|  1. HEXAGONAL GRID (H3 - Uber's choice)                              |
|  =======================================                                |
|                                                                         |
|      _____         _____         _____                                 |
|     /     \       /     \       /     \                                |
|    / 1.5x  \_____/ 1.0x  \_____/ 2.0x  \                              |
|    \       /     \       /     \       /                              |
|     \_____/ 1.2x  \_____/ 1.0x  \_____/                               |
|     /     \       /     \       /     \                                |
|    / 1.8x  \_____/ 1.3x  \_____/ 1.0x  \                              |
|    \       /     \       /     \       /                              |
|     \_____/       \_____/       \_____/                               |
|                                                                         |
|  WHY HEXAGONS?                                                         |
|  * All neighbors equidistant (unlike squares)                        |
|  * No diagonal ambiguity                                             |
|  * Smoother zone transitions                                         |
|  * 6 neighbors vs 4/8 for squares                                    |
|                                                                         |
|  H3 library provides hierarchical hex grid                           |
|  Resolution 7 ≈ 5km² cells (good for surge)                         |
|                                                                         |
|  2. DYNAMIC CLUSTERING                                                |
|  =====================                                                  |
|                                                                         |
|  Instead of fixed grid, cluster based on demand:                     |
|                                                                         |
|  * K-means clustering on ride requests                               |
|  * Zones grow/shrink based on activity                              |
|  * More granular in dense areas                                      |
|                                                                         |
|  More complex, harder to explain to users.                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.4: SURGE PRICING SERVICE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SURGE SERVICE ARCHITECTURE                                           |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  +---------------------------------------------------------+   |  |
|  |  |              Metrics Aggregator                         |   |  |
|  |  |  (Collects demand/supply every 30 seconds)             |   |  |
|  |  +---------------------------------------------------------+   |  |
|  |       |                    |                    |              |  |
|  |       v                    v                    v              |  |
|  |  +----------+        +----------+        +----------+         |  |
|  |  | Request  |        | Driver   |        | ETA      |         |  |
|  |  | Counter  |        | Counter  |        | Service  |         |  |
|  |  |          |        |          |        |          |         |  |
|  |  | Requests |        | Available|        | Avg ETA  |         |  |
|  |  | per zone |        | per zone |        | per zone |         |  |
|  |  +----------+        +----------+        +----------+         |  |
|  |       |                    |                    |              |  |
|  |       +--------------------+--------------------+              |  |
|  |                            |                                    |  |
|  |                            v                                    |  |
|  |  +---------------------------------------------------------+   |  |
|  |  |              Surge Calculator                           |   |  |
|  |  |  (Runs every 1-2 minutes)                              |   |  |
|  |  |  - Calculate surge for each zone                       |   |  |
|  |  |  - Apply smoothing                                     |   |  |
|  |  |  - Validate against caps                               |   |  |
|  |  +---------------------------------------------------------+   |  |
|  |                            |                                    |  |
|  |                            v                                    |  |
|  |  +---------------------------------------------------------+   |  |
|  |  |              Surge Store (Redis)                        |   |  |
|  |  |  Key: surge:{zone_id}                                  |   |  |
|  |  |  Value: { multiplier, updated_at, expires_at }         |   |  |
|  |  |  TTL: 5 minutes                                        |   |  |
|  |  +---------------------------------------------------------+   |  |
|  |                            |                                    |  |
|  |       +--------------------+--------------------+              |  |
|  |       v                    v                    v              |  |
|  |  +----------+        +----------+        +----------+         |  |
|  |  | Rider    |        | Pricing  |        | Driver   |         |  |
|  |  | App      |        | Service  |        | App      |         |  |
|  |  |          |        |          |        |          |         |  |
|  |  | Show     |        | Apply to |        | Show     |         |  |
|  |  | surge on |        | fare     |        | surge    |         |  |
|  |  | map      |        | estimate |        | zones    |         |  |
|  |  +----------+        +----------+        +----------+         |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.5: FARE CALCULATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FARE COMPONENTS                                                       |
|                                                                         |
|  fare = base_fare                                                      |
|       + (distance_rate × distance_km)                                 |
|       + (time_rate × duration_minutes)                                |
|       + booking_fee                                                    |
|       + tolls                                                          |
|       + airport_fee                                                    |
|                                                                         |
|  WITH SURGE:                                                           |
|  fare = (base_fare + distance + time) × surge_multiplier             |
|       + booking_fee  (not surged)                                     |
|       + tolls        (not surged)                                     |
|       + fees         (not surged)                                     |
|                                                                         |
|  EXAMPLE:                                                              |
|  ---------                                                              |
|  Base fare: $2.50                                                     |
|  Distance: 5 km × $1.50/km = $7.50                                   |
|  Time: 15 min × $0.30/min = $4.50                                    |
|  Subtotal: $14.50                                                     |
|                                                                         |
|  Surge: 1.8x                                                          |
|  Surged subtotal: $14.50 × 1.8 = $26.10                              |
|                                                                         |
|  Booking fee: $2.00                                                   |
|  Total: $28.10                                                        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  FARE ESTIMATION                                                       |
|                                                                         |
|  def estimate_fare(pickup, dropoff, ride_type):                      |
|      # Get route                                                      |
|      route = routing_service.get_route(pickup, dropoff)              |
|      distance_km = route.distance / 1000                              |
|      duration_min = route.duration / 60                               |
|                                                                         |
|      # Get rates for ride type (UberX, UberXL, etc.)                |
|      rates = get_rates(ride_type, pickup.city)                       |
|                                                                         |
|      # Calculate base fare                                            |
|      base = rates.base_fare                                           |
|      distance_charge = distance_km * rates.per_km                    |
|      time_charge = duration_min * rates.per_minute                   |
|      subtotal = base + distance_charge + time_charge                 |
|                                                                         |
|      # Apply minimum fare                                             |
|      subtotal = max(subtotal, rates.minimum_fare)                    |
|                                                                         |
|      # Get surge                                                      |
|      zone = get_zone(pickup)                                          |
|      surge = surge_service.get_surge(zone)                           |
|                                                                         |
|      # Apply surge                                                    |
|      surged_subtotal = subtotal * surge                              |
|                                                                         |
|      # Add fixed fees                                                 |
|      total = surged_subtotal + rates.booking_fee                     |
|                                                                         |
|      return FareEstimate(                                              |
|          low=total * 0.9,   # -10% buffer                            |
|          high=total * 1.1,  # +10% buffer                            |
|          surge=surge                                                   |
|      )                                                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.6: SURGE SMOOTHING AND UX

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY SMOOTHING?                                                        |
|                                                                         |
|  Problem: Raw surge is volatile.                                      |
|  * 1.5x > 2.3x > 1.8x > 2.1x (every 30 seconds)                    |
|  * Confusing for riders                                              |
|  * "I just checked and it was cheaper!"                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SMOOTHING TECHNIQUES                                                  |
|                                                                         |
|  1. MOVING AVERAGE                                                     |
|     smooth_surge = 0.7 * current_surge + 0.3 * previous_surge       |
|                                                                         |
|  2. STEP INCREMENTS                                                    |
|     Surge only changes in 0.25x steps                                |
|     1.0 > 1.25 > 1.5 > 1.75 > 2.0 ...                              |
|                                                                         |
|  3. MINIMUM DURATION                                                   |
|     Surge stays at level for at least 2 minutes                      |
|     Can't jump from 1.5x to 2.5x instantly                          |
|                                                                         |
|  4. HYSTERESIS                                                         |
|     Surge goes UP faster than DOWN                                   |
|     (Incentivize drivers to come online)                             |
|                                                                         |
|     if new_surge > current_surge:                                    |
|         # Quick ramp up                                               |
|         return current_surge + min(0.5, new_surge - current_surge)  |
|     else:                                                              |
|         # Slow ramp down                                              |
|         return current_surge - min(0.25, current_surge - new_surge) |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  USER EXPERIENCE                                                       |
|                                                                         |
|  1. UPFRONT PRICING                                                    |
|     Show final price, not multiplier                                 |
|     "$28.50" instead of "2.3x surge"                                |
|     Less confusion, more predictable                                  |
|                                                                         |
|  2. SURGE CONFIRMATION                                                 |
|     "Prices are higher due to increased demand"                      |
|     "1.8x - Pay $35.00 instead of $19.44"                           |
|     User must confirm before booking                                  |
|                                                                         |
|  3. WAIT FOR LOWER PRICE                                              |
|     "Surge is expected to drop in ~10 minutes"                       |
|     "Notify me when prices drop"                                     |
|                                                                         |
|  4. HEAT MAP                                                           |
|     Show riders where surge is high/low                              |
|     "Walk 2 blocks for 20% cheaper ride"                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.7: DRIVER INCENTIVES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SURGE NOTIFICATION TO DRIVERS                                        |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |   Driver App Screen:                                           |  |
|  |                                                                 |  |
|  |   +-------------------------------------------------------+    |  |
|  |   |                                                       |    |  |
|  |   |   📍 Surge Area Nearby!                              |    |  |
|  |   |                                                       |    |  |
|  |   |   Downtown (2.3x)         ███████████████████  2.3x  |    |  |
|  |   |   Airport (1.8x)          ██████████████       1.8x  |    |  |
|  |   |   Stadium (3.0x)          ████████████████████ 3.0x  |    |  |
|  |   |                                                       |    |  |
|  |   |   🚗 Drive to Stadium to earn 3x on next trip       |    |  |
|  |   |                                                       |    |  |
|  |   +-------------------------------------------------------+    |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  DRIVER EARNINGS                                                       |
|  ----------------                                                       |
|                                                                         |
|  Base trip: Driver earns $15                                         |
|  With 2.0x surge: Driver earns $15 × 2.0 = $30                      |
|                                                                         |
|  (Platform fee applies to base, not surge in some markets)           |
|                                                                         |
|  QUESTS AND BONUSES                                                    |
|  -------------------                                                    |
|                                                                         |
|  In addition to surge:                                                |
|  * "Complete 10 trips, earn $50 bonus"                              |
|  * "Drive during Friday 5-9 PM, earn 1.5x on all trips"            |
|  * "Stay in surge zone for 30 min, guaranteed $X"                   |
|                                                                         |
|  These incentives are pre-calculated based on demand predictions.   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DYNAMIC PRICING - KEY TAKEAWAYS                                      |
|                                                                         |
|  PURPOSE                                                               |
|  -------                                                               |
|  * Balance supply and demand                                         |
|  * Reduce wait times during high demand                              |
|  * Incentivize drivers to high-demand areas                          |
|                                                                         |
|  CALCULATION                                                           |
|  -----------                                                           |
|  * Base: demand/supply ratio                                         |
|  * Adjusted by: historical patterns, weather, events, ETA           |
|  * Capped (typically 5-8x max)                                       |
|                                                                         |
|  ZONES                                                                 |
|  -----                                                                 |
|  * Hexagonal grid (H3) for uniform zones                            |
|  * Surge calculated per zone every 1-2 minutes                      |
|  * Stored in Redis for fast lookup                                   |
|                                                                         |
|  SMOOTHING                                                             |
|  ---------                                                             |
|  * Moving average                                                    |
|  * Step increments (0.25x)                                          |
|  * Hysteresis (up fast, down slow)                                  |
|                                                                         |
|  INTERVIEW TIP                                                         |
|  -------------                                                         |
|  Explain the economics (supply/demand balance).                      |
|  Discuss zone definition (why hexagons).                             |
|  Address UX (smoothing, upfront pricing).                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 5

