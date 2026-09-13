# BMTC BOARDING POINT RECOMMENDER

## Complete Product Context, Vision, Research, Decisions, and Engineering Handoff

You are taking over an ongoing product-building project.

Do NOT treat this as a generic request to "make a bus app."

The project has already gone through product discovery, competitor reconnaissance, data-source investigation, and architectural discussion. The purpose of this document is to transfer the complete context so that you do not restart the reasoning from zero or accidentally build the wrong product.

---

# 1. THE PROJECT IN ONE SENTENCE

We are building a **Bengaluru-focused web application that tells a person exactly which BMTC boarding point they should walk to, and which bus/service they should board, given their current location and destination.**

The key idea is:

> **Don't merely tell the user the nearest bus stop. Tell them the best place to physically walk to in order to catch the right BMTC bus.**

That distinction is the foundation of the product.

---

# 2. WHY THIS PROJECT EXISTS

The idea came from a real Bengaluru experience.

The founder uses BMTC buses extensively because they are a practical low-cost transportation option.

A real journey involved travelling from **Bommasandra to Corporation Circle** for work.

The difficult part was not necessarily knowing that BMTC buses exist.

The difficult part happened while returning.

From an unfamiliar location, the user knew the destination but did not know:

* which nearby bus stop was the correct one
* which side of the road they should stand on
* whether the physically closest stop served the correct direction
* whether another nearby stop was actually better
* where exactly they should walk
* which BMTC service they should board

This revealed a more specific problem than ordinary route planning.

The problem is:

> **"I'm standing here. I need to go there. Where exactly should I walk so I can catch the right BMTC bus?"**

This is the problem we want to solve.

---

# 3. ORIGINAL IDEA VS ACTUAL PRODUCT

The original idea was:

> User enters current location and destination → application finds the nearest BMTC bus stop.

That idea was investigated.

It is NOT sufficiently differentiated.

There are already products that can provide nearby stops, routes, or transit directions, including:

* Google Maps
* Namma BMTC
* Tummoc
* Moovit
* BMTC Routes
* BMTC Guide
* Bangalore Local Bus Guide
* other Bengaluru transit applications

There is no point rebuilding another generic "bus route finder."

Therefore, the product was reframed.

---

# 4. THE ACTUAL PRODUCT VISION

The vision is:

> **Make BMTC usable for people who know where they want to go but don't understand Bengaluru's bus-stop geography.**

The application should remove the cognitive burden of figuring out:

> "Which stop?"

> "Which direction?"

> "Which side?"

> "How far do I walk?"

> "Which bus?"

Instead, the user should receive one clear action.

For example:

```text
You are here.

Walk 350 m
≈ 4 minutes

Go to:
Corporation Circle Bus Stop

Board:
365-A

Towards:
Bommasandra

Expected journey:
~48 min
```

The exact numbers above are illustrative, not hardcoded requirements.

The important thing is the **action-oriented output**.

---

# 5. WHAT MAKES THIS DIFFERENT

The product is NOT trying to compete with Google Maps by becoming a better universal maps application.

It is also NOT trying to replace Namma BMTC.

The potential differentiation is:

### Destination-aware boarding-point selection.

Suppose the user is near three bus stops:

```text
Stop A = 150 m away
Stop B = 250 m away
Stop C = 400 m away
```

A naive system says:

> Stop A is nearest.

Our system asks:

> Which of these stops gives this user the best BMTC journey to their destination?

Maybe:

```text
Stop A
150 m walk
wrong direction
2 transfers

Stop B
250 m walk
direct bus
correct direction

Stop C
400 m walk
direct bus
better frequency
```

The correct recommendation may therefore be Stop B or C.

That is the core algorithmic/product problem.

---

# 6. THE PRODUCT PROMISE

The V1 promise should be extremely narrow:

> **"Tell me where to walk to catch the right BMTC bus."**

Do not turn V1 into:

* a general travel super-app
* a Google Maps clone
* a full public transit platform
* a social network
* an AI chatbot
* a live bus tracking platform
* a ticketing platform
* a BMTC replacement

The product wins or loses based on whether it solves the boarding-point problem better than existing alternatives.

---

# 7. TARGET USER

The primary user is someone in Bengaluru who:

* uses BMTC
* knows their destination
* may not know Bengaluru's bus-stop layout
* may be unfamiliar with the current area
* wants the simplest possible instruction
* does not want to understand transit graphs
* does not want to search through dozens of routes
* may be using a phone while physically standing on the street

Potential users include:

### 1. New Bengaluru residents

People who recently moved to Bengaluru.

### 2. Students

People frequently travelling to colleges, hostels, internships, etc.

### 3. Workers

People travelling to unfamiliar offices or industrial areas.

### 4. Occasional BMTC users

People who normally use cabs/metros but occasionally use buses to save money.

### 5. People travelling outside their usual area

Even experienced Bengaluru residents don't know every bus stop in the city.

---

# 8. UX PHILOSOPHY

The user should not have to understand BMTC.

The system should understand BMTC for them.

The ideal interaction is:

```text
OPEN WEBSITE

↓
Allow location

↓
Enter destination

↓
GET ANSWER

"Walk 300 m to X"

"Board 500-CH"

"Towards Y"

"Get down at Z"
```

The interface should feel extremely simple.

No login should be required.

No account should be required.

No complicated onboarding should be required.

No unnecessary forms.

---

# 9. WHY NO LOGIN

There is no obvious reason V1 requires identity.

The user wants a transit answer.

They do not need:

* profile creation
* password
* social login
* account management

Removing authentication also reduces:

* development time
* infrastructure
* privacy concerns
* friction
* operational complexity

This is a product decision, not a technical limitation.

---

# 10. THE CORE USER FLOW

The first version should roughly follow:

```text
                USER
                  │
                  ▼
        Open the web application
                  │
                  ▼
       Obtain current location
                  │
                  ▼
        Enter destination
                  │
                  ▼
      Resolve destination location
                  │
                  ▼
      Find nearby BMTC boarding stops
                  │
                  ▼
   Determine which routes/services serve
          useful destinations
                  │
                  ▼
       Evaluate possible journeys
                  │
                  ▼
    Rank possible boarding points
                  │
                  ▼
       Return best recommendation
                  │
                  ▼
      Give simple walking instruction
```

---

# 11. THE CORE ALGORITHM

Conceptually:

```text
USER LOCATION
      ↓
NEARBY BMTC STOPS
      ↓
CANDIDATE ROUTES
      ↓
DESTINATION REACHABILITY
      ↓
DIRECTION VALIDATION
      ↓
WALKING COST
      ↓
TRANSFER COST
      ↓
ROUTE QUALITY
      ↓
BEST BOARDING POINT
```

The ranking function should eventually consider things such as:

* walking distance
* walking time
* direct vs transfer journey
* route direction
* whether the route gets meaningfully close to the destination
* number of transfers
* possibly service frequency
* eventually live ETA
* potentially physical road-side information

But do NOT implement every factor immediately.

First prove that the basic recommendation works.

---

# 12. VERY IMPORTANT: NEAREST STOP ≠ BEST STOP

This is the central technical/product insight.

Consider:

```text
User
 |
 | 100m
 |
Stop A  → buses away from destination

 |
 | 250m
 |
Stop B  → direct bus to destination
```

A nearest-stop system recommends A.

Our product should recommend B.

Therefore the system is fundamentally a **destination-aware ranking system**, not a simple nearest-neighbour lookup.

---

# 13. ANOTHER IMPORTANT PROBLEM: DIRECTION

A BMTC route can operate in different directions.

For example, a route number alone is insufficient.

We may have:

```text
Route 365
→ Bommasandra

Route 365
→ Majestic
```

The user needs the correct direction.

The system therefore needs to understand:

* route
* trip
* direction
* stop sequence
* destination relationship

However:

### DO NOT confuse GTFS `direction_id` with physical road-side information.

`direction_id` can help describe the logical direction of a trip.

It does NOT automatically tell us:

> "Stand on the eastern side of this road."

That distinction matters.

---

# 14. PHYSICAL BOARDING SIDE

One potentially valuable future feature is:

> "Board from this side of the road."

This is much harder than ordinary route planning.

Potential data sources could include:

* road geometry
* stop coordinates
* route geometry
* OSM road data
* stop/platform information
* manually verified data
* crowdsourced corrections

But V1 should NOT pretend we know boarding side if the data cannot support it.

If reliable boarding-side information is unavailable:

> Do not hallucinate it.

Instead provide a correct stop recommendation without inventing a road side.

---

# 15. DATA IS THE BIGGEST RISK

The frontend is not the difficult part.

The hardest part is obtaining reliable BMTC data.

We investigated several possible sources.

The important distinction is:

> **Technically accessible data ≠ legally usable data.**

And:

> **Publicly visible data ≠ open-licensed data.**

And:

> **A GitHub repository containing BMTC data ≠ permission to commercially redistribute BMTC data.**

These distinctions must be preserved throughout development.

---

# 16. DATA SOURCES INVESTIGATED

Potential sources include:

### A. Official BMTC / Namma BMTC

This is the ideal source if a properly documented and licensed dataset/API can be obtained.

Investigate official sources first.

---

### B. Vonter/bmtc-gtfs

Repository:

https://github.com/Vonter/bmtc-gtfs

This is an unofficial/community GTFS dataset derived from BMTC/Namma BMTC-related data.

It is technically very interesting because it contains things such as:

* stops
* routes
* trips
* stop sequences
* shapes
* schedules
* translations
* other GTFS-related information

But it has important limitations.

The repository documentation indicates that the source data is not completely accurate, particularly for timetables and stop timings.

It also does not necessarily represent every BMTC service because of limitations around live-tracking availability.

Most importantly:

### Do not assume the repository's code license grants commercial rights to the underlying BMTC data.

The underlying data rights must be investigated separately.

---

### C. Mobility Database

Mobility Database contains a BMTC feed based on the community GTFS source.

This is useful for discovering and validating feeds.

But:

> The fact that Mobility Database hosts a feed does not automatically mean the underlying data is commercially redistributable.

License and producer rights must be independently verified.

---

### D. OpenCity

OpenCity has several Bengaluru/BMTC datasets, including bus stops and route information.

Potentially useful.

However, a critical finding from our investigation was:

> Some OpenCity BMTC dataset pages explicitly show "No License Provided."

Therefore:

### Do NOT say "OpenCity data is clearly licensed" without checking the exact dataset.

Different datasets may have different licensing conditions.

---

### E. OpenStreetMap

OSM is potentially useful for:

* roads
* pedestrian paths
* sidewalks
* physical geography
* bus stops
* route relations

OSM is open data under the ODbL framework, subject to its attribution/share-alike conditions.

It is potentially useful commercially, but the exact data architecture and attribution requirements must be respected.

Also:

### OSM completeness in Bengaluru must be measured.

Do not assume every sidewalk or pedestrian path is mapped.

---

# 17. DATA SOURCE HIERARCHY

Prefer:

```text
Official BMTC data
       ↓
Properly licensed GTFS
       ↓
OSM + verified transit data
       ↓
Unofficial/community datasets
       ↓
Reverse-engineered APIs
       ↓
Random scraped data
```

The lower we go, the greater the operational/legal/reliability risk.

---

# 18. DATA PROVENANCE

Transit data changes.

Therefore the system should eventually understand:

```text
source
source_id
dataset_version
imported_at
valid_from
valid_until
confidence
```

We should not blindly overwrite everything whenever a new dataset appears.

Ideally we can determine:

> What source produced this stop?

> When was it imported?

> When was it last verified?

This becomes especially important if users report wrong stops.

---

# 19. DATA MODEL CONCEPT

A conceptual model is:

```text
STOP
----
id
name
latitude
longitude
source
source_id
confidence
last_verified


ROUTE
-----
id
route_number
name
source
source_id


TRIP
----
id
route_id
direction
headsign


ROUTE_STOP
----------
route_id
stop_id
sequence


DATA_VERSION
------------
source
version
imported_at
valid_from
valid_until
```

This is conceptual.

Do not blindly implement this exact schema before examining the actual data.

The real schema should emerge from the actual datasets.

---

# 20. CURRENT PRODUCT DIFFERENTIATION

Existing products already solve generic transit navigation.

Therefore:

### BAD PRODUCT

```text
Enter destination
→ Here are 17 buses
→ Here are 9 stops
→ Good luck, citizen
```

### BETTER PRODUCT

```text
You are here.

Walk 280 m to:

Corporation Circle Bus Stop

Board:

365-A

Towards:

Bommasandra

```

The second experience is what we are building.

---

# 21. COMPETITORS

The relevant competitors we identified are:

## Google Maps

Extremely strong.

This is the biggest threat.

We cannot pretend Google Maps does not exist.

If Google Maps already solves the exact problem sufficiently well, our product has no reason to exist.

---

## Namma BMTC

Official BMTC application.

Provides transit information, routes, schedules, live tracking/ETA-related functionality, etc.

This is the official ecosystem and therefore an important competitor/data reference.

---

## Tummoc

Provides Bengaluru transit planning, nearby stops, routes, walking information, schedules, fare information, etc.

Another significant competitor.

---

## Moovit

Provides public transport planning and step-by-step transit navigation in Bengaluru.

---

## BMTC Routes

There are existing web tools specifically focused on BMTC route and stop discovery, including nearest-stop functionality.

---

# 22. WHAT WE MUST NOT CLAIM

Never claim:

> "No existing app does this."

We have already established that several products provide overlapping functionality.

Instead, the question is:

> **Can we make the boarding-point decision significantly simpler or better?**

That must be tested.

---

# 23. VALIDATION PLAN

Before building a huge system, test real journeys.

Create approximately 50 Bengaluru journey scenarios.

Examples should include:

### Case 1: Multiple nearby stops

Several stops are within walking distance.

### Case 2: Nearest stop is wrong

The closest stop serves the wrong direction.

### Case 3: Correct stop is slightly farther

The best stop requires a longer walk but gives a direct bus.

### Case 4: Opposite road side

Potential physical boarding-side problem.

### Case 5: Unfamiliar area

User has no knowledge of local stops.

### Case 6: Multiple possible routes

Several BMTC routes can reach the destination.

### Case 7: Transfers

Compare direct vs transfer journeys.

### Case 8: Ambiguous destination

Destination name can refer to multiple places.

---

# 24. COMPARISON

For each journey compare:

```text
Google Maps
Tummoc
Our algorithm
Human judgement
```

Measure:

* correct boarding stop
* walking distance
* directness
* correct direction
* number of transfers
* clarity
* time to understand the instruction
* whether a normal person can actually execute it

The goal is not to make our algorithm mathematically beautiful.

The goal is:

> **Does a human actually get to the correct bus more easily?**

---

# 25. V1 SHOULD BE SMALL

Despite the eventual functionality, the first implementation should remain small.

Potential V1:

```text
Location
   ↓
Destination
   ↓
Nearby BMTC stops
   ↓
Route matching
   ↓
Destination-aware ranking
   ↓
Best boarding point
```

That is enough to prove the central idea.

---

# 26. FEATURES EXPLICITLY OUTSIDE INITIAL V1

Do NOT automatically add:

* login
* user accounts
* payments
* ticket booking
* social features
* reviews
* AI chatbot
* live vehicle tracking
* push notifications
* fare calculation
* metro integration
* auto-rickshaw integration
* analytics dashboards
* admin portal
* recommendation history
* Kubernetes
* microservices
* Kafka
* Redis
* GraphQL
* unnecessary cloud infrastructure

These are distractions until the core recommendation works.

---

# 27. POSSIBLE FUTURE FEATURES

Only after V1 works:

### Live bus information

```text
Bus expected in 7 minutes
```

### Physical boarding side

```text
Board from the opposite side of the road
```

### Landmark instructions

```text
Walk toward the Corporation Circle signal.
The stop is beside the post office.
```

### Kannada support

Support Kannada stop names and user-facing instructions.

### Crowdsourced corrections

Users could report:

* stop moved
* stop closed
* wrong location
* route missing
* boarding side incorrect

### Confidence score

Internally:

```text
Recommendation confidence: 94%
```

Possibly not shown to users initially.

---

# 28. UX DESIGN PRINCIPLE

The UI should be simple because the user is often standing on a road looking at a phone.

Do not make the user read a transit thesis.

The interface should prioritize:

1. Where am I?
2. Where am I going?
3. Where do I walk?
4. What bus do I take?
5. Which direction?
6. Where do I get down?

Everything else is secondary.

---

# 29. TECHNICAL PHILOSOPHY

This is a small product.

Do not overengineer it.

The fact that a system *could* use:

```text
React
Next.js
FastAPI
PostgreSQL
PostGIS
Redis
Kafka
Kubernetes
GraphQL
multiple microservices
event buses
service meshes
```

does not mean it should.

Architecture must follow actual requirements.

Start with the smallest architecture that can:

* ingest transit data
* query stops
* calculate candidate routes
* rank boarding points
* provide a web response

---

# 30. LIKELY INITIAL STACK

A reasonable starting point is:

```text
Frontend
---------
HTML
CSS
JavaScript

Backend
-------
Python
FastAPI

Data
----
GTFS/validated BMTC data
OSM where appropriate

Database
--------
Possibly PostgreSQL/PostGIS
```

But this is NOT sacred.

If a simpler architecture can prove the product faster, use it.

Do not introduce a database before we know we need one.

Do not introduce an external routing engine before testing whether it is actually necessary.

---

# 31. GEOSPATIAL ROUTING WARNING

One earlier proposal was:

> Use OSRM for pedestrian routing.

That must NOT be accepted blindly.

Standard OSRM is primarily associated with road-network routing and requires appropriate profiles/customization for different modes.

Do not assume:

> "OSM has sidewalks"

therefore:

> "OSRM automatically gives accurate walking routes."

Investigate the actual routing engine and pedestrian network before depending on it.

Alternatives may include:

* Valhalla
* GraphHopper
* OpenRouteService
* other suitable routing engines
* simple geographic distance for early prototypes

For the first experiment, even straight-line distance may be sufficient to validate the **boarding-point ranking logic** before implementing real walking navigation.

---

# 32. IMPORTANT ENGINEERING STRATEGY

Separate the problem into layers.

## Layer 1: Transit data

Question:

> What BMTC stops/routes exist?

## Layer 2: Transit graph

Question:

> Which routes connect which stops?

## Layer 3: Destination reasoning

Question:

> Which stops/routes get the user meaningfully toward the destination?

## Layer 4: Walking

Question:

> How difficult is it to reach the boarding point?

## Layer 5: Ranking

Question:

> Which boarding point is best?

## Layer 6: UX

Question:

> How do we explain that recommendation to a human?

This separation will make debugging much easier.

---

# 33. FIRST DEBUGGING PRINCIPLE

If the application recommends the wrong bus:

Do NOT immediately change the UI.

Determine which layer failed.

For example:

```text
Correct stop data?
        ↓ YES

Correct route data?
        ↓ YES

Correct direction?
        ↓ NO
```

Then the problem is routing/direction logic.

Not CSS.

Human beings have an impressive ability to fix backend bugs by changing button colors. Do not participate in this tradition.

---

# 34. PRODUCT SUCCESS CRITERION

The first version is successful if a user can enter:

```text
Current location
+
Destination
```

and reliably receive:

```text
BEST BOARDING POINT
+
WALKING INSTRUCTION
+
BUS
+
DIRECTION
```

with enough accuracy that they would genuinely use it instead of opening Google Maps.

That last condition matters.

A technically functioning application that nobody prefers is not a successful product.

---

# 35. PRODUCT FAILURE CRITERION

The project should be reconsidered if testing shows:

> Google Maps already gives equally good or better boarding instructions in nearly every realistic case.

We should not build a worse clone simply because we have already written some code.

Likewise, if legally usable and sufficiently fresh BMTC data cannot be obtained, that is a major blocker.

---

# 36. MONETIZATION

Do not optimize V1 around monetization.

The first objective is proving usefulness.

Possible future models:

* ads
* sponsored local businesses
* premium advanced transit features
* API access
* B2B transit intelligence
* partnerships

But none of these should distort V1.

No forced account.

No subscription wall around basic directions.

No monetization before product validation.

---

# 37. COST PHILOSOPHY

The founder has almost no budget.

Therefore:

> Free/open-source infrastructure wherever practical.

Avoid services that create unpredictable per-request bills.

Prefer:

* static hosting
* free tiers
* open-source routing
* open data
* low-cost/free databases
* minimal backend infrastructure

But do NOT compromise legal/data correctness merely to save money.

---

# 38. DEPLOYMENT PHILOSOPHY

The application should eventually be deployable cheaply.

The frontend could potentially use a static hosting platform.

The backend can use a small container/server.

But deployment architecture should be decided after the application works locally.

Do not design cloud infrastructure before the product exists.

---

# 39. DEVELOPMENT APPROACH

IMPORTANT:

We are NOT using autonomous vibe coding for this project.

The founder wants to understand and control what is being built.

Therefore:

### Do NOT:

* autonomously generate the entire project
* modify dozens of files without explanation
* build huge architecture in the background
* make major design decisions silently
* install unnecessary dependencies
* generate thousands of lines of code

### DO:

Build incrementally.

Explain what each component does.

Provide the actual code.

Let the founder run it.

When something fails:

1. inspect the error
2. identify the root cause
3. make the smallest appropriate fix
4. explain why
5. continue

---

# 40. EXPECTED DEVELOPMENT STYLE

The founder will ask for code.

When providing code:

* give complete files where practical
* clearly state the filename
* explain where the file belongs
* avoid unexplained abstractions
* avoid unnecessary frameworks
* keep dependencies minimal
* make the code readable
* don't hide important logic behind magic helpers

Example:

```text
project/
├── backend/
│   ├── main.py
│   ├── routing.py
│   └── data.py
│
└── frontend/
    ├── index.html
    ├── style.css
    └── app.js
```

This is illustrative only.

Do not assume this exact structure until we decide the architecture.

---

# 41. DEVELOPMENT PHASES

## PHASE 0 — Product/Data Validation

Before substantial coding:

* finalize exact V1
* verify data sources
* understand licensing
* obtain sample data
* inspect actual schemas
* test whether route/stop relationships are usable

---

## PHASE 1 — Transit Data Prototype

Build a tiny program that can answer:

> Given a coordinate, what BMTC stops are nearby?

Then:

> What routes serve those stops?

Then:

> Which of those routes move toward a destination?

No UI required yet.

---

## PHASE 2 — Boarding-Point Ranking

Implement:

```text
location
+
destination
+
BMTC data
→
ranked boarding points
```

Test it with real journeys.

This is the most important phase.

---

## PHASE 3 — Minimal Web UI

Build the simple interface:

```text
Current location
Destination
Find my bus
```

Then display the recommendation.

---

## PHASE 4 — Real-World Testing

Use real Bengaluru locations.

Test:

* unfamiliar areas
* multiple stops
* multiple routes
* opposite directions
* direct vs transfer journeys

Compare against Google Maps and other existing services.

---

## PHASE 5 — Improve

Only after testing:

* walking routes
* better geocoding
* landmarks
* confidence
* Kannada
* live data
* boarding side
* etc.

---

# 42. WHAT I EXPECT FROM YOU AS THE AI BUILD PARTNER

Do not behave like a code autocomplete machine.

Act as an engineering/product collaborator.

Before implementing something significant, consider:

### Product

Does this actually improve the user experience?

### Data

Do we have the required data?

### Legal

Are we allowed to use it?

### Technical

Can we reliably compute it?

### Performance

Will it work at realistic scale?

### Cost

Can we afford it?

### Maintenance

What happens when BMTC changes routes?

### Failure

What happens when the recommendation is wrong?

### Competition

Does Google/Tummoc/Namma BMTC already do this?

---

# 43. DO NOT HALLUCINATE

This is especially important.

If you don't know something:

> Say that you don't know.

If a dataset's license is unclear:

> Say "license unclear."

If a BMTC API might exist but cannot be verified:

> Say "unverified."

If a route is uncertain:

> Say "uncertain."

If the product idea appears weak:

> Say so.

Never fabricate:

* APIs
* BMTC endpoints
* licenses
* route numbers
* bus schedules
* stop locations
* commercial permissions
* infrastructure costs
* competitor capabilities

Use evidence whenever the claim depends on current external information.

---

# 44. DO NOT TRUST PREVIOUS AI OUTPUT BLINDLY

Previous AI reconnaissance suggested:

* OpenCity was clearly licensed
* OSRM could be used for pedestrian routing
* several datasets were production-ready

Some of these claims were insufficiently supported.

Therefore:

> Previous AI output is a research lead, not a source of truth.

Verify important claims independently.

---

# 45. THE BIGGEST RISKS

Current known project risks:

## RISK 1 — Google Maps already solves it

Potentially fatal.

Must be tested.

## RISK 2 — BMTC data quality

Routes and schedules can change.

Some community data may be incomplete.

## RISK 3 — Licensing

A technically perfect dataset is useless for a commercial product if we don't have the necessary rights.

## RISK 4 — Direction ambiguity

Route direction is not the same as physical boarding side.

## RISK 5 — Walking data

Pedestrian routing may be incomplete or inaccurate.

## RISK 6 — Wrong recommendations

A wrong bus recommendation is much worse than a slightly ugly interface.

## RISK 7 — Maintenance

BMTC changes routes, stops, and schedules.

The system must eventually account for changing data.

---

# 46. THE ACTUAL TECHNICAL CHALLENGE

At first glance this looks like:

> "Make a webpage."

It is not.

The webpage is trivial.

The real system is:

```text
Geolocation
      +
Geocoding
      +
Transit graph
      +
Geospatial search
      +
Destination matching
      +
Direction reasoning
      +
Walking estimation
      +
Ranking
      +
Human-readable recommendation
```

The frontend is simply the surface.

---

# 47. WHAT WE ARE NOT TRYING TO SOLVE YET

We do NOT need perfect:

* traffic prediction
* live bus arrival
* travel-time prediction
* passenger density
* ticket pricing
* multimodal routing
* every BMTC operational edge case

The first question is much simpler:

> **Can we consistently choose the correct BMTC boarding point for a user travelling from A to B?**

If yes, we have something worth improving.

If no, more features won't save it.

---

# 48. THE NORTH STAR

Everything should ultimately support this sentence:

> **"I don't know Bengaluru's bus stops. I only know where I am and where I want to go. Tell me where to walk and what BMTC bus to take."**

If a feature does not help answer that question, it probably doesn't belong in V1.

---

# 49. FIRST THING TO DO

Do NOT start by generating the entire application.

Start by confirming:

1. exact V1 requirements
2. actual available BMTC data
3. actual data schema
4. legal/licensing situation
5. smallest algorithm capable of testing the hypothesis

Then build the smallest working prototype.

The objective is not:

> "Build a sophisticated transit platform."

The objective is:

> **"Prove that we can reliably solve the boarding-point problem."**

Once that is proven, we can turn the prototype into a proper production application.

---

# 50. FINAL PRODUCT DEFINITION

### Name

Working title:

**BMTC Boarding Point Recommender**

The final brand name can be decided later.

### Location

Bengaluru only for V1.

### Transit

BMTC only for V1.

### Input

Current location + destination.

### Output

Best BMTC boarding point + walking instruction + bus/service + direction + destination/exit information where reliable.

### Authentication

None.

### Primary interface

Simple mobile-first web page.

### Initial goal

Fast, accurate, actionable boarding-point recommendation.

### Long-term vision

Become the easiest way for a person unfamiliar with Bengaluru's BMTC network to answer:

> **"Where exactly do I go to catch my bus?"**

---

# MOST IMPORTANT INSTRUCTION

Do not build a generic BMTC route planner.

Do not build a Google Maps clone.

Do not start with a giant architecture.

Do not assume datasets are legally usable.

Do not assume AI-generated research is correct.

Do not add features because they sound impressive.

Build around the one difficult problem:

> **Given where the user is and where they want to go, determine the best BMTC boarding point and explain it clearly enough that a human standing on a Bengaluru street can actually follow the instruction.**

That is what we are cooking.
