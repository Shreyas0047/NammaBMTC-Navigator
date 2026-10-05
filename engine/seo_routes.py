"""
SEO Landing Page Generator for BMTC Routes.
Generates crawlable, fast-loading, Schema.org-enriched HTML pages
for individual BMTC bus routes to rank at the top of Google Search.
Aesthetic 4-color dark theme matching the NammaBMTC design system.
"""

import html
from typing import Dict, Any, List, Optional
from engine.route_details import get_route_details

POPULAR_ROUTES = [
    ("KIA-9", "Airport ⇔ Majestic"),
    ("500-D", "Silk Board ⇔ Hebbal (ORR)"),
    ("356-M", "Majestic ⇔ Electronic City"),
    ("V-335E", "Majestic ⇔ ITPL / Whitefield"),
    ("365", "Majestic ⇔ Bannerghatta"),
    ("KIA-8", "Airport ⇔ Electronic City"),
    ("500-A", "Banashankari ⇔ Hebbal"),
    ("V-500CA", "ITPL ⇔ Banashankari"),
    ("KIA-4", "Airport ⇔ Indiranagar / HAL"),
    ("KBS-3A", "Majestic ⇔ Attibele"),
    ("401-K", "Yelahanka ⇔ Kengeri"),
    ("378", "Kengeri ⇔ Electronic City"),
    ("258", "KR Market ⇔ Nelamangala"),
    ("305-D", "Majestic ⇔ Whitefield"),
    ("201", "Domlur ⇔ Srinagar"),
    ("KIA-5", "Airport ⇔ Banashankari"),
]

DARK_SEO_CSS = """
:root {
  --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  --primary: #00A3FF;
  --primary-dark: #008EE0;
  --bg: #090B10;
  --surface: #111522;
  --surface-elevated: #161B2B;
  --surface-input: #0D101A;
  --border: #1F263B;
  --text-main: #FFFFFF;
  --text-muted: #8E9CAE;
  --accent-green: #10B981;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: var(--font-sans);
  background: var(--bg);
  color: var(--text-main);
  line-height: 1.5;
  padding: 0 16px 60px 16px;
}
.seo-navbar {
  max-width: 820px;
  margin: 0 auto;
  padding: 16px 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border);
}
.brand-link {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: var(--text-main);
  font-weight: 800;
  font-size: 16px;
}
.home-btn {
  font-size: 13px;
  font-weight: 700;
  color: var(--primary);
  text-decoration: none;
  padding: 6px 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 9999px;
  transition: all 0.15s ease;
}
.home-btn:hover { background: var(--surface-elevated); border-color: var(--primary); }

.seo-content {
  max-width: 820px;
  margin: 24px auto 0 auto;
}
.breadcrumbs {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 16px;
}
.breadcrumbs a { color: var(--primary); text-decoration: none; }

.route-hero-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 28px 24px;
  position: relative;
  overflow: hidden;
  margin-bottom: 24px;
}
.route-hero-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; height: 3px;
  background: var(--primary);
}
.route-badge-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.route-pill-large {
  font-family: var(--font-mono);
  font-size: 20px;
  font-weight: 800;
  color: var(--primary);
  background: rgba(0, 163, 255, 0.12);
  border: 1px solid rgba(0, 163, 255, 0.3);
  padding: 4px 14px;
  border-radius: 8px;
  letter-spacing: -0.02em;
}
.service-tag {
  font-size: 11.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 4px 10px;
  border-radius: 9999px;
  background: var(--surface-elevated);
  color: var(--text-muted);
  border: 1px solid var(--border);
}
.route-hero-title {
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.02em;
  margin-bottom: 8px;
  color: var(--text-main);
}
.route-hero-sub {
  font-size: 14.5px;
  color: var(--text-muted);
  margin-bottom: 22px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}
.metric-card {
  background: var(--surface-input);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.metric-num {
  font-family: var(--font-mono);
  font-size: 18px;
  font-weight: 800;
  color: var(--text-main);
}
.metric-lbl {
  font-size: 10.5px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.cta-banner {
  background: var(--surface-elevated);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 20px 22px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 28px;
}
.cta-text h3 { font-size: 16px; font-weight: 800; margin-bottom: 4px; color: var(--text-main); }
.cta-text p { font-size: 13px; color: var(--text-muted); }
.cta-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--primary);
  color: #FFFFFF;
  font-size: 13.5px;
  font-weight: 800;
  padding: 10px 18px;
  border-radius: 9999px;
  text-decoration: none;
  transition: background 0.15s ease;
}
.cta-action-btn:hover { background: var(--primary-dark); }

.section-title {
  font-size: 18px;
  font-weight: 800;
  letter-spacing: -0.02em;
  margin-bottom: 14px;
  color: var(--text-main);
}

.stops-timeline {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 24px;
  margin-bottom: 32px;
}
.stops-list {
  list-style: none;
  display: flex;
  flex-direction: column;
}
.stop-item {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  position: relative;
}
.stop-marker-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 24px;
  flex-shrink: 0;
}
.stop-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #4E5970;
  border: 2px solid var(--surface);
  box-shadow: 0 0 0 2px var(--border);
  z-index: 2;
}
.stop-dot.terminus-node {
  width: 14px;
  height: 14px;
  background: var(--primary);
  box-shadow: 0 0 0 3px rgba(0, 163, 255, 0.2);
}
.stop-line {
  width: 2px;
  background: var(--border);
  height: 48px;
  margin: 4px 0;
}
.stop-info-col {
  padding-bottom: 22px;
  flex: 1;
}
.stop-tag-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 2px;
}
.stop-idx-badge {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  text-transform: uppercase;
}
.stop-name-title {
  font-size: 14.5px;
  font-weight: 700;
  color: var(--text-main);
}
.stop-desc-text {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

.related-section {
  margin-top: 40px;
}
.related-chips-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}
.related-chip {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 10px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: var(--text-main);
  transition: all 0.15s ease;
}
.related-chip:hover {
  border-color: var(--primary);
  background: var(--surface-elevated);
}
.chip-route-no {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 800;
  color: var(--primary);
}
.chip-route-corridor {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.seo-footer {
  margin-top: 50px;
  padding-top: 24px;
  border-top: 1px solid var(--border);
  text-align: center;
  font-size: 12px;
  color: var(--text-muted);
}
"""


def render_route_seo_html(route_name: str) -> Optional[str]:
    """
    Renders a high-ranking, mobile-responsive HTML page for a specific BMTC route.
    Includes Schema.org BusTrip JSON-LD, AdSense tags, interactive CTAs,
    and complete ordered stop lists.
    """
    data = get_route_details(route_name)
    if not data:
        return None

    sname = html.escape(data.get("route_short_name", route_name))
    lname = html.escape(data.get("route_long_name", ""))
    orig = html.escape(data.get("origin", "Bengaluru"))
    dest = html.escape(data.get("destination", "Bengaluru"))
    stype = html.escape(data.get("service_type_name", "Ordinary Non-AC"))
    total_stops = data.get("total_stops", 0)
    dist_km = data.get("distance_km", 0)
    est_mins = data.get("estimated_duration_min", 45)
    trips_per_day = data.get("trips_per_day", 24)
    headway = html.escape(data.get("headway_desc", "Every 10-15 mins"))
    operating_hours = html.escape(data.get("operating_hours", "05:00 AM – 11:15 PM"))
    fares = data.get("fares", {})
    shakti = fares.get("shakti_free", False)
    daily_pass = fares.get("daily_pass_accepted", True)
    schedule = data.get("schedule", {})
    first_bus = html.escape(schedule.get("first_bus", "05:15 AM"))
    last_bus = html.escape(schedule.get("last_bus", "11:00 PM"))

    is_ac = "AC" in stype.upper() or "VAJRA" in stype.upper() or sname.startswith("KIA")
    fare_display = f"₹{fares.get('ac_vajra', 60)}" if is_ac else f"₹{fares.get('non_ac', 25)}"

    # Deep link back to app
    app_deep_link = f"/?from={orig}&to={dest}"

    # Build Stop Items HTML
    stops_html_list = []
    stops = data.get("stops", [])
    for idx, s in enumerate(stops, 1):
        s_name = html.escape(s.get("stop_name", ""))
        s_desc = html.escape(s.get("stop_desc", "") or "")
        is_first = (idx == 1)
        is_last = (idx == len(stops))
        node_class = "terminus-node" if (is_first or is_last) else "regular-node"
        badge_text = "ORIGIN TERMINUS" if is_first else ("DESTINATION TERMINUS" if is_last else f"STOP #{idx}")

        stops_html_list.append(f"""
        <li class="stop-item">
          <div class="stop-marker-col">
            <span class="stop-dot {node_class}"></span>
            {'' if is_last else '<span class="stop-line"></span>'}
          </div>
          <div class="stop-info-col">
            <div class="stop-tag-row">
              <span class="stop-idx-badge">{badge_text}</span>
            </div>
            <h4 class="stop-name-title">{s_name}</h4>
            {f'<p class="stop-desc-text">{s_desc}</p>' if s_desc else ''}
          </div>
        </li>
        """)

    stops_rendered = "".join(stops_html_list)

    # Related routes HTML
    related_html_list = []
    for r_slug, r_label in POPULAR_ROUTES:
        if r_slug != sname:
            related_html_list.append(f"""
            <a href="/route/{r_slug}" class="related-chip">
              <span class="chip-route-no">{r_slug}</span>
              <span class="chip-route-corridor">{r_label}</span>
            </a>
            """)
    related_rendered = "".join(related_html_list[:12])

    page_title = f"BMTC Route {sname} Bus Timings, Stops & Fare ({orig} ⇔ {dest}) – NammaBMTC"
    meta_desc = f"Complete ordered stop list ({total_stops} stops), first bus ({first_bus}) & last bus ({last_bus}) timings, fare ({fare_display}), and live GPS tracking for BMTC Route {sname} ({orig} to {dest}) across Bengaluru."
    canonical_url = f"https://nammabmtc-navigator.onrender.com/route/{sname}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>{page_title}</title>
  
  <!-- SEO Meta Tags -->
  <meta name="description" content="{meta_desc}">
  <meta name="keywords" content="BMTC Route {sname}, {sname} bus timings, {sname} bus stops, {orig} to {dest} bus, Bangalore BMTC {sname}, Namma BMTC {sname} fare">
  <meta name="robots" content="index, follow">
  <meta name="theme-color" content="#090B10">
  <link rel="canonical" href="{canonical_url}">

  <!-- Google Search Console & AdSense -->
  <meta name="google-site-verification" content="iAQ7YYhDGLNzFsQOaI6wwPZ_o7yE1hbHPULsk40YLfU" />
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-3357683031374517" crossorigin="anonymous"></script>

  <!-- Open Graph -->
  <meta property="og:type" content="website">
  <meta property="og:url" content="{canonical_url}">
  <meta property="og:title" content="{page_title}">
  <meta property="og:description" content="{meta_desc}">
  <meta property="og:image" content="https://nammabmtc-navigator.onrender.com/assets/app-icon.jpg">
  <meta property="og:site_name" content="NammaBMTC Navigator">

  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="BMTC Route {sname} Timings & Stops – NammaBMTC">
  <meta name="twitter:description" content="{meta_desc}">
  <meta name="twitter:image" content="https://nammabmtc-navigator.onrender.com/assets/app-icon.jpg">

  <!-- Schema.org Structured Data: BusTrip & Breadcrumbs -->
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "BusTrip",
    "name": "BMTC Route {sname}",
    "busName": "BMTC {sname}",
    "busNumber": "{sname}",
    "description": "{meta_desc}",
    "departureBusStop": {{
      "@type": "BusStop",
      "name": "{orig}"
    }},
    "arrivalBusStop": {{
      "@type": "BusStop",
      "name": "{dest}"
    }},
    "provider": {{
      "@type": "Organization",
      "name": "Bangalore Metropolitan Transport Corporation (BMTC)"
    }}
  }}
  </script>
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      {{
        "@type": "ListItem",
        "position": 1,
        "name": "Home",
        "item": "https://nammabmtc-navigator.onrender.com/"
      }},
      {{
        "@type": "ListItem",
        "position": 2,
        "name": "BMTC Routes",
        "item": "https://nammabmtc-navigator.onrender.com/"
      }},
      {{
        "@type": "ListItem",
        "position": 3,
        "name": "Route {sname}",
        "item": "{canonical_url}"
      }}
    ]
  }}
  </script>

  <link rel="icon" type="image/svg+xml" href="/assets/logo.svg">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,300..900;1,14..32,300..900&family=JetBrains+Mono:wght@500;600;700;800&display=swap" rel="stylesheet">

  <style>
{DARK_SEO_CSS}
  </style>
</head>
<body>
  <!-- Minimalist Brand Header -->
  <header class="seo-navbar">
    <a href="/" class="brand-link">
      <img src="/assets/logo.svg" alt="NammaBMTC Logo" width="28" height="28">
      <span>NammaBMTC Navigator</span>
    </a>
    <a href="/" class="home-btn">← Bus Route Finder</a>
  </header>

  <main class="seo-content">
    <!-- Breadcrumb Hierarchy -->
    <nav class="breadcrumbs" aria-label="Breadcrumb">
      <a href="/">Home</a> &gt; <span>BMTC Bus Routes</span> &gt; <span>Route {sname}</span>
    </nav>

    <!-- Route Overview Hero Card -->
    <section class="route-hero-card">
      <div class="route-badge-row">
        <span class="route-pill-large">{sname}</span>
        <span class="service-tag">{stype}</span>
        {f'<span class="service-tag" style="background:rgba(16, 185, 129, 0.12); color:#A7F3D0; border-color:rgba(16, 185, 129, 0.3);">₹0 Shakti Scheme Eligible</span>' if shakti else ''}
      </div>
      <h1 class="route-hero-title">{orig} ⇔ {dest}</h1>
      <p class="route-hero-sub">Official BMTC Route {sname} ordered stop directory, schedule timetable, and passenger boarding guide for Bengaluru commuters.</p>

      <div class="metrics-grid">
        <div class="metric-card">
          <span class="metric-num">{dist_km} km</span>
          <span class="metric-lbl">Total Distance</span>
        </div>
        <div class="metric-card">
          <span class="metric-num">~{est_mins}m</span>
          <span class="metric-lbl">Typical Trip Time</span>
        </div>
        <div class="metric-card">
          <span class="metric-num">{total_stops}</span>
          <span class="metric-lbl">Total Stops</span>
        </div>
        <div class="metric-card">
          <span class="metric-num">{fare_display}</span>
          <span class="metric-lbl">Estimated Fare</span>
        </div>
        <div class="metric-card">
          <span class="metric-num">{first_bus}</span>
          <span class="metric-lbl">First Bus</span>
        </div>
        <div class="metric-card">
          <span class="metric-num">{last_bus}</span>
          <span class="metric-lbl">Last Bus</span>
        </div>
      </div>

      <!-- Interactive Deep Link CTA Banner -->
      <div class="cta-banner">
        <div class="cta-text">
          <h3>Boarding Route {sname} Today?</h3>
          <p>Find your nearest boarding stop, walking directions, and real-time approaching bus status.</p>
        </div>
        <a href="{app_deep_link}" class="cta-action-btn">
          <span>Find Nearest Boarding Stop</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
        </a>
      </div>
    </section>

    <!-- Ordered Stop Sequence Section -->
    <section class="stops-timeline">
      <h2 class="section-title">Complete Ordered Stop Sequence ({total_stops} Stops)</h2>
      <ol class="stops-list">
        {stops_rendered}
      </ol>
    </section>

    <!-- Popular Related Routes for Internal Link Architecture -->
    <section class="related-section">
      <h2 class="section-title">Other Popular Bengaluru Bus Routes</h2>
      <div class="related-chips-grid">
        {related_rendered}
      </div>
    </section>

    <!-- Civic Disclaimer Footer -->
    <footer class="seo-footer">
      <p>NammaBMTC Navigator • Powered by Official Bengaluru Urban & Rural GTFS Data • Open Database License (ODbL 1.0)</p>
    </footer>
  </main>
</body>
</html>
"""
