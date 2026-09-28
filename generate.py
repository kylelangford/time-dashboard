#!/usr/bin/env python3
"""
Time Dashboard Generator
Queries time_entries DB and generates HTML dashboards for each person.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "time-report.db"
OUTPUT_DIR = Path(__file__).parent

# Category detection patterns - expanded with 5-10+ keywords per category
CATEGORY_PATTERNS = {
    # Communication
    "Client Calls": ["call w/", "call with", "phone call", "intro call", "kickoff call",
                    "kick-off call", "biweekly call", "call prep", "questions for call"],
    "Status/Weekly Calls": ["status call", "weekly call", "weekly checkin", "weekly check-in",
                           "weekly product", "weekly status", "weekly tech call", "biweekly huddle",
                           "weekly huddle", "weekly design"],
    "Scrum/Standups": ["scrum", "huddle", "standup", "stand-up", "daily standup", "sync",
                       "retro", "sprint planning", "bi-weekly huddle"],
    "Email Processing": ["process email", "respond to email", "email to-do", "correspondence",
                        "email correspondence", "inbox", "email response"],

    # QA & Support
    "QA/Testing": ["qa", " test", "testing", "bug fix", "round 1 qa", "round 2 qa",
                   "qa list", "qa feedback", "qa items", "debug", "troubleshoot"],
    "Troubleshooting": ["troubleshoot", "debug", "issue", "problem", "fix", "hotfix",
                       "bug", "resolve", "broken", "error"],

    # Site Work
    "Site Updates": ["site update", "misc update", "updates to", "content update",
                    "copy update", "minor update", "quick update"],
    "Content Updates": ["content", "copy update", "adding content", "page content",
                       "text update", "copy change"],
    "Templates": ["template", "twig", "theme", "theming", "layout"],
    "Page Building": ["page build", "build page", "landing page", "homepage", "create page",
                     "new page", "services page", "about page"],
    "Blog Work": ["blog", "article", "post", "news", "magazine"],

    # Design
    "Design/Visual": ["design review", "design audit", "visual", "ui design", "redesign",
                     "design with", "review design", "design and dev"],
    "Images/Graphics": ["image", "graphic", "banner", "photo", "logo", "icon", "artwork",
                       "illustration", "visual asset", "photo gallery"],
    "Wireframes/UX": ["wireframe", "mockup", "prototype", "ux", "figma", "sketch", "xd",
                     "user flow", "wireframing"],
    "Video Production": ["video", "youtube", "vimeo", "embed video", "video player",
                        "video component", "video walkthru"],

    # Admin
    "PM/Basecamp Admin": ["basecamp", "trello", "asana", "jira", "clickup", "project management",
                         "pm:", "trello cleanup", "trello board", "review trello", "sprint"],
    "Billing/Finance": ["billing", "invoice", "qb", "quickbooks", "banking", "payment",
                       "pricing", "budget", "cost"],
    "Estimates/Proposals": ["estimate", "proposal", "scope", "quote", "pricing", "roadmap",
                           "timeline", "sow"],
    "Day Planning": ["plan day", "plan my day", "organize todo", "review projects", "priorities",
                    "planning", "2026 planning", "daily planning", "week planning"],

    # Technical
    "Navigation/Menu": ["nav", "menu", "header", "footer", "subnav", "mobile menu",
                       "dropdown", "mega menu", "sticky footer", "mobile nav"],
    "Forms": ["form", "webform", "form validation", "form submit", "contact form",
              "form handler", "form field", "submission"],
    "Server/Hosting": ["server", "hosting", "dns", "ssl", "pantheon", "acquia", "wpengine",
                      "deployment", "deploy", "devops", "lando", "docker", "env setup"],
    "Launch/Go-live": ["launch", "go live", "go-live", "golive", "pre-launch", "post launch",
                      "soft launch", "launch prep", "launch support"],
    "Email Marketing": ["email template", "code email", "email build", "newsletter",
                       "email campaign", "braze", "mailchimp"],
    "Migration/Import": ["migrat", "import", "export", "upgrade", "d7", "d9", "d10",
                        "importer", "data migration", "sync"],
    "Analytics/SEO": ["analytics", "seo", "gtm", "ga4", "google tag", "tracking",
                     "tag manager", "conversion", "metrics"],
    "CSS/Styling": ["css", "styling", "sass", "scss", "tailwind", "responsive",
                   "mobile styling", "typography", "spacing", "colors"],
    "Components/Modules": ["component", "module", "block", "widget", "plugin",
                          "custom module", "acf block", "gutenberg"],

    # Meetings (catch-all)
    "Meetings": ["meeting", "call", "conference", "zoom", "teams"],

    # Research & Documentation
    "Research/Documentation": ["research", "documentation", "document", "spec",
                              "requirements", "review code", "code review", "audit"],

    # AI/Automation - precise patterns to avoid false positives
    "AI/Automation": [" ai ", " ai,", "ai workflow", "ai agent", "ai project", "ai prompts",
                      "claude", "mcp server", "mcp ", "gpt", "chatgpt", "copilot", "llm",
                      "openai", "automation", "automated", "prompt engineering"],
}

CATEGORY_GROUPS = {
    "Communication": ["Client Calls", "Status/Weekly Calls", "Scrum/Standups", "Email Processing", "Meetings"],
    "QA & Support": ["QA/Testing", "Troubleshooting"],
    "Site Work": ["Site Updates", "Content Updates", "Templates", "Page Building", "Blog Work"],
    "Design": ["Design/Visual", "Images/Graphics", "Wireframes/UX", "Video Production"],
    "Admin": ["PM/Basecamp Admin", "Billing/Finance", "Estimates/Proposals", "Day Planning", "Research/Documentation"],
    "Technical": ["Navigation/Menu", "Forms", "Server/Hosting", "Launch/Go-live", "Email Marketing", "Migration/Import", "Analytics/SEO", "CSS/Styling", "Components/Modules"],
    "AI/Automation": ["AI/Automation"],
}

GROUP_COLORS = {
    "Communication": "#fb7185",
    "QA & Support": "#4ade80",
    "Site Work": "#38bdf8",
    "Design": "#818cf8",
    "Admin": "#fbbf24",
    "Technical": "#2dd4bf",
    "AI/Automation": "#c084fc",
}

# Todo normalization - maps variations to canonical names
TODO_NORMALIZATION = {
    # Meetings variations
    "meetings and phone calls": "Meetings & Calls",
    "meetings & phone calls": "Meetings & Calls",
    "meetings & calls": "Meetings & Calls",
    "meetings & conference calls": "Meetings & Calls",
    "phone calls/meetings": "Meetings & Calls",
    "phone calls": "Meetings & Calls",
    # PM variations
    "pm": "Project Management",
    "project management": "Project Management",
    # Support variations
    "misc. support": "Misc Support",
    "misc support": "Misc Support",
    # Billing variations
    "billing/qb/banking": "Billing & Finance",
    "billing": "Billing & Finance",
    "qb": "Billing & Finance",
    # Business management
    "misc. business management": "Business Management",
    "misc business management": "Business Management",
    # Site work
    "misc site requests": "Site Requests",
    "misc. site requests": "Site Requests",
    # Time tracking
    "hours/time entry": "Time Entry",
    "hours": "Time Entry",
    "time entry": "Time Entry",
}


def normalize_todo(todo):
    """Normalize a todo name to canonical form."""
    if not todo:
        return todo
    return TODO_NORMALIZATION.get(todo.lower().strip(), todo)


def get_connection():
    return sqlite3.connect(DB_PATH)


def get_people(conn):
    """Get list of people in the database."""
    cur = conn.execute("SELECT DISTINCT person FROM time_entries ORDER BY person")
    return [row[0] for row in cur.fetchall()]


def get_basic_stats(conn, person):
    """Get basic stats for a person."""
    cur = conn.execute("""
        SELECT
            ROUND(SUM(hours), 1) as total_hours,
            COUNT(*) as entries,
            MIN(date) as earliest,
            MAX(date) as latest,
            ROUND(AVG(hours), 2) as avg_entry
        FROM time_entries WHERE person = ?
    """, (person,))
    row = cur.fetchone()
    return {
        "total_hours": row[0],
        "entries": row[1],
        "earliest": row[2],
        "latest": row[3],
        "avg_entry": row[4],
    }


def get_yearly_data(conn, person):
    """Get yearly hours breakdown."""
    cur = conn.execute("""
        SELECT strftime('%Y', date) as year,
               ROUND(SUM(hours), 1) as hours,
               COUNT(*) as entries
        FROM time_entries WHERE person = ?
        GROUP BY year ORDER BY year
    """, (person,))
    return [{"year": r[0], "hours": r[1], "entries": r[2]} for r in cur.fetchall()]


def get_monthly_aggregate(conn, person):
    """Get monthly data by year for seasonal comparison."""
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Get all years
    years_cur = conn.execute("""
        SELECT DISTINCT strftime('%Y', date) as year
        FROM time_entries WHERE person = ? ORDER BY year
    """, (person,))
    years = [r[0] for r in years_cur.fetchall()]

    # Get monthly data for each year
    cur = conn.execute("""
        SELECT strftime('%Y', date) as year, strftime('%m', date) as month,
               ROUND(SUM(hours), 1) as hours
        FROM time_entries WHERE person = ?
        GROUP BY year, month ORDER BY year, month
    """, (person,))

    # Build data structure: {year: {month: hours}}
    data = {}
    for row in cur.fetchall():
        year, month, hours = row
        if year not in data:
            data[year] = {}
        data[year][month] = hours

    # Return structure for chart: {months: [...], years: {year: [hours per month]}}
    # Use None instead of 0 for missing data so lines don't drop to zero
    return {
        "months": months,
        "years": years,
        "data": {
            year: [data.get(year, {}).get(f"{i+1:02d}") or None for i in range(12)]
            for year in years
        }
    }


def get_day_of_week(conn, person):
    """Get day of week breakdown."""
    days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    cur = conn.execute("""
        SELECT strftime('%w', date) as dow, ROUND(SUM(hours), 1) as hours
        FROM time_entries WHERE person = ?
        GROUP BY dow ORDER BY dow
    """, (person,))
    data = {r[0]: r[1] for r in cur.fetchall()}
    return [{"day": days[i], "hours": data.get(str(i), 0)} for i in range(7)]


def get_entry_size_distribution(conn, person):
    """Get entry size distribution."""
    cur = conn.execute("""
        SELECT
            CASE
                WHEN hours <= 0.25 THEN '<30min'
                WHEN hours <= 1 THEN '30min-1h'
                WHEN hours <= 2 THEN '1-2h'
                WHEN hours <= 4 THEN '2-4h'
                ELSE '4h+'
            END as bucket,
            COUNT(*) as count,
            ROUND(SUM(hours), 1) as hours
        FROM time_entries WHERE person = ?
        GROUP BY bucket
    """, (person,))
    order = ['<30min', '30min-1h', '1-2h', '2-4h', '4h+']
    data = {r[0]: {"count": r[1], "hours": r[2]} for r in cur.fetchall()}
    return [{"size": b, "count": data.get(b, {}).get("count", 0), "hours": data.get(b, {}).get("hours", 0)} for b in order]


def get_top_companies(conn, person, limit=15):
    """Get top companies by hours."""
    cur = conn.execute("""
        SELECT company, ROUND(SUM(hours), 1) as hours, COUNT(*) as entries
        FROM time_entries WHERE person = ?
        GROUP BY company ORDER BY hours DESC LIMIT ?
    """, (person, limit))
    return [{"name": r[0], "hours": r[1], "entries": r[2]} for r in cur.fetchall()]


def get_top_projects(conn, person, limit=10):
    """Get top projects by hours."""
    cur = conn.execute("""
        SELECT company, project, ROUND(SUM(hours), 1) as hours
        FROM time_entries WHERE person = ?
        GROUP BY company, project ORDER BY hours DESC LIMIT ?
    """, (person, limit))
    return [{"company": r[0][:15], "name": r[1], "hours": r[2]} for r in cur.fetchall()]


def get_top_client_by_year(conn, person):
    """Get top client for each year."""
    cur = conn.execute("""
        WITH ranked AS (
            SELECT strftime('%Y', date) as year, company, ROUND(SUM(hours), 1) as hours,
                   ROW_NUMBER() OVER (PARTITION BY strftime('%Y', date) ORDER BY SUM(hours) DESC) as rn
            FROM time_entries WHERE person = ?
            GROUP BY year, company
        )
        SELECT year, company, hours FROM ranked WHERE rn = 1 ORDER BY year
    """, (person,))
    return [{"year": r[0], "client": r[1], "hours": r[2]} for r in cur.fetchall()]


def get_client_diversity(conn, person):
    """Get client diversity by year."""
    cur = conn.execute("""
        SELECT strftime('%Y', date) as year,
               COUNT(DISTINCT company) as clients,
               ROUND(SUM(hours), 1) as hours
        FROM time_entries WHERE person = ?
        GROUP BY year ORDER BY year
    """, (person,))
    return [{"year": r[0], "clients": r[1], "hours": r[2]} for r in cur.fetchall()]


def get_top_keywords(conn, person):
    """Get top keywords from descriptions."""
    keywords = [
        ("updates", ["update", "updates to"]),
        ("calls", ["call", "meeting", "huddle"]),
        ("review", ["review", "audit"]),
        ("testing", ["test", "qa", "bug"]),
        ("design", ["design", "mockup", "wireframe"]),
        ("content", ["content", "copy"]),
        ("dev", ["dev", "development", "build"]),
        ("fix", ["fix", "hotfix", "resolve"]),
        ("styling", ["styl", "css", "sass", "tailwind"]),
        ("mobile", ["mobile", "responsive"]),
        ("deploy", ["deploy", "deployment", "launch"]),
        ("forms", ["form", "webform", "submission"]),
        ("migration", ["migrat", "import", "upgrade"]),
        ("components", ["component", "module", "block"]),
    ]
    results = []
    for word, patterns in keywords:
        conditions = " OR ".join([f"lower(description) LIKE '%{p}%'" for p in patterns])
        cur = conn.execute(f"""
            SELECT COUNT(*) as count, ROUND(SUM(hours), 1) as hours
            FROM time_entries WHERE person = ? AND ({conditions})
        """, (person,))
        row = cur.fetchone()
        if row[0] > 0:
            results.append({"word": word, "count": row[0], "hours": row[1]})
    return sorted(results, key=lambda x: x["hours"], reverse=True)[:10]


def get_top_tasks(conn, person, limit=10):
    """Get most frequent tasks with normalization."""
    cur = conn.execute("""
        SELECT todo, SUM(hours) as hours, COUNT(*) as count
        FROM time_entries
        WHERE person = ? AND todo IS NOT NULL AND length(todo) > 0
        GROUP BY todo
    """, (person,))

    # Normalize and aggregate
    normalized = {}
    for row in cur.fetchall():
        norm_name = normalize_todo(row[0])
        if norm_name not in normalized:
            normalized[norm_name] = {"hours": 0, "count": 0}
        normalized[norm_name]["hours"] += row[1]
        normalized[norm_name]["count"] += row[2]

    # Sort and return top results
    results = [
        {"task": name, "hours": round(data["hours"], 1), "count": data["count"]}
        for name, data in normalized.items()
    ]
    results.sort(key=lambda x: x["hours"], reverse=True)
    return results[:limit]


def get_category_hours(conn, person):
    """Get hours by category using pattern matching."""
    results = {}

    for category, patterns in CATEGORY_PATTERNS.items():
        conditions = []
        for p in patterns:
            conditions.append(f"lower(description) LIKE '%{p}%'")
            conditions.append(f"lower(todo) LIKE '%{p}%'")

        where_clause = " OR ".join(conditions)
        cur = conn.execute(f"""
            SELECT ROUND(SUM(hours), 1) as hours, COUNT(*) as entries
            FROM time_entries WHERE person = ? AND ({where_clause})
        """, (person,))
        row = cur.fetchone()
        if row[0] and row[0] > 0:
            results[category] = {"hours": row[0], "entries": row[1]}

    return results


def get_category_trends(conn, person):
    """Get category trends by year."""
    years_cur = conn.execute("""
        SELECT DISTINCT strftime('%Y', date) as year
        FROM time_entries WHERE person = ? ORDER BY year
    """, (person,))
    years = [r[0] for r in years_cur.fetchall()]

    trends = {"years": years}

    # Key categories to track over time
    track_categories = {
        "meetings": ["meeting", "call", "huddle", "standup"],
        "dev": ["development", "dev ", "coding", "build", "implement", "feature"],
        "qa": ["qa", "test", "bug", "debug"],
        "design": ["design", "wireframe", "mockup", "figma", "sketch"],
        "deploy": ["deploy", "deployment", "launch", "go live"],
        "ai": [" ai ", "ai workflow", "ai agent", "claude", "mcp ", "gpt", "chatgpt", "copilot", "llm", "prompt"],
    }

    for name, patterns in track_categories.items():
        conditions = " OR ".join([f"lower(description) LIKE '%{p}%'" for p in patterns])
        values = []
        for year in years:
            cur = conn.execute(f"""
                SELECT ROUND(SUM(hours), 1)
                FROM time_entries
                WHERE person = ? AND strftime('%Y', date) = ? AND ({conditions})
            """, (person, year))
            row = cur.fetchone()
            values.append(row[0] or 0)
        trends[name] = values

    return trends


def get_tech_stack(conn, person):
    """Get technology stack hours."""
    tech_patterns = {
        "Drupal": ["drupal", "d7", "d9", "d10", "twig"],
        "WordPress": ["wordpress", "wp ", "wpengine", "elementor", "gutenberg", "acf"],
        "Adobe AEM": ["aem", "adobe"],
        "React": ["react", "vue", "angular", "astro"],
        "CSS/Tailwind": ["css", "sass", "scss", "tailwind", "styling"],
        "JavaScript": ["javascript", "js ", "typescript", "node"],
        "Pantheon": ["pantheon", "terminus"],
        "Acquia": ["acquia", "blt"],
        "Git/DevOps": ["git", "github", "deploy", "ci/cd", "lando", "docker"],
        "Salesforce": ["salesforce", "pardot"],
    }

    results = []
    for tech, patterns in tech_patterns.items():
        conditions = " OR ".join([f"lower(description) LIKE '%{p}%' OR lower(project) LIKE '%{p}%'" for p in patterns])
        cur = conn.execute(f"""
            SELECT ROUND(SUM(hours), 1) as hours, COUNT(*) as entries
            FROM time_entries WHERE person = ? AND ({conditions})
        """, (person,))
        row = cur.fetchone()
        if row[0] and row[0] > 0:
            results.append({"name": tech, "hours": row[0], "entries": row[1]})

    return sorted(results, key=lambda x: x["hours"], reverse=True)


def generate_html(person, data):
    """Generate HTML dashboard for a person."""

    # Calculate derived values
    stats = data["stats"]
    years_count = len(data["yearly"])
    avg_per_year = round(stats["total_hours"] / years_count, 0) if years_count else 0
    avg_per_month = round(avg_per_year / 12, 0)

    # Format dates
    earliest = stats["earliest"]
    latest = stats["latest"]
    date_range = f"{earliest[:7].replace('-', ' ')} - {latest[:7].replace('-', ' ')}"

    # Build category groups
    category_hours = data["category_hours"]
    group_totals = {}
    for group, cats in CATEGORY_GROUPS.items():
        total = sum(category_hours.get(c, {}).get("hours", 0) for c in cats)
        if total > 0:
            group_totals[group] = total

    total_hours = stats["total_hours"]
    category_groups_data = [
        {"name": g, "hours": h, "pct": round(h / total_hours * 100, 1), "color": GROUP_COLORS[g]}
        for g, h in sorted(group_totals.items(), key=lambda x: x[1], reverse=True)
    ]

    # Build detailed categories
    categories_data = []
    for group, cats in CATEGORY_GROUPS.items():
        for cat in cats:
            if cat in category_hours:
                h = category_hours[cat]["hours"]
                categories_data.append({
                    "name": cat,
                    "hours": h,
                    "pct": round(h / total_hours * 100, 1),
                    "group": group
                })
    categories_data.sort(key=lambda x: x["hours"], reverse=True)

    # Work types
    strategy_hours = sum(category_hours.get(c, {}).get("hours", 0) for c in
                        ["Client Calls", "Status/Weekly Calls", "Meetings", "PM/Basecamp Admin", "Day Planning", "Estimates/Proposals"])
    maintain_hours = sum(category_hours.get(c, {}).get("hours", 0) for c in
                        ["Site Updates", "Troubleshooting", "Content Updates"])
    implement_hours = sum(category_hours.get(c, {}).get("hours", 0) for c in
                         ["QA/Testing", "Design/Visual", "Templates", "Page Building", "Forms", "CSS/Styling"])

    work_types = [
        {"name": "Strategy/Coordination", "hours": strategy_hours, "desc": "calls, meetings, PM, planning", "color": "#818cf8"},
        {"name": "Maintenance", "hours": maintain_hours, "desc": "updates, support, troubleshooting", "color": "#fbbf24"},
        {"name": "Implementation", "hours": implement_hours, "desc": "build, test, design, create", "color": "#4ade80"},
    ]

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Time Report Dashboard - {person}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            padding: 2rem;
            line-height: 1.6;
        }}
        h1 {{ font-size: 2rem; margin-bottom: 0.5rem; color: #f8fafc; }}
        h2 {{ font-size: 1.25rem; margin-bottom: 1rem; color: #94a3b8; font-weight: 500; }}
        h3 {{ font-size: 1rem; margin-bottom: 0.75rem; color: #cbd5e1; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .stat-card {{
            background: #1e293b;
            padding: 1.25rem;
            border-radius: 0.75rem;
            border: 1px solid #334155;
        }}
        .stat-value {{
            font-size: 1.75rem;
            font-weight: 700;
            color: #38bdf8;
        }}
        .stat-label {{
            color: #94a3b8;
            font-size: 0.875rem;
            margin-top: 0.25rem;
        }}
        .section {{ margin-bottom: 2rem; }}
        .section-title {{
            font-size: 1.5rem;
            color: #f8fafc;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #334155;
        }}
        .grid-2 {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 1.5rem;
        }}
        .grid-3 {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
        }}
        .card {{
            background: #1e293b;
            padding: 1.5rem;
            border-radius: 0.75rem;
            border: 1px solid #334155;
        }}
        .chart-container {{ height: 300px; }}
        .chart-tall {{ height: 400px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; }}
        th, td {{ padding: 0.6rem; text-align: left; border-bottom: 1px solid #334155; }}
        th {{ color: #94a3b8; font-weight: 500; }}
        .text-right {{ text-align: right; }}
        tr:hover {{ background: #334155; }}
        .bar {{ background: #334155; border-radius: 4px; height: 6px; margin-top: 4px; }}
        .bar-fill {{ background: linear-gradient(90deg, #38bdf8, #818cf8); height: 100%; border-radius: 4px; }}
        .generated {{ color: #64748b; font-size: 0.75rem; text-align: center; margin-top: 2rem; }}
    </style>
</head>
<body>
    <h1>Time Report Dashboard</h1>
    <h2>{person} | {date_range}</h2>

    <div class="stats">
        <div class="stat-card">
            <div class="stat-value">{stats["total_hours"]:,.0f}</div>
            <div class="stat-label">Total Hours</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{stats["entries"]:,}</div>
            <div class="stat-label">Time Entries</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{years_count}</div>
            <div class="stat-label">Years of Data</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{stats["avg_entry"]}</div>
            <div class="stat-label">Avg Entry Size (hrs)</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{avg_per_year:,.0f}</div>
            <div class="stat-label">Avg Hours/Year</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{avg_per_month:,.0f}</div>
            <div class="stat-label">Avg Hours/Month</div>
        </div>
    </div>

    <div class="section">
        <div class="section-title">Hours Over Time</div>
        <div class="grid-2">
            <div class="card">
                <h3>Yearly Hours</h3>
                <div class="chart-container">
                    <canvas id="yearlyChart"></canvas>
                </div>
            </div>
            <div class="card">
                <h3>Seasonal Pattern (All Years)</h3>
                <div class="chart-container">
                    <canvas id="monthlyChart"></canvas>
                </div>
            </div>
        </div>
    </div>

    <div class="section">
        <div class="section-title">Work Breakdown</div>
        <div class="grid-2">
            <div class="card">
                <h3>Work Categories</h3>
                <div class="chart-container chart-tall">
                    <canvas id="categoriesChart"></canvas>
                </div>
            </div>
            <div class="card">
                <h3>Category Details</h3>
                <table id="categoryTable"></table>
            </div>
        </div>
    </div>

    <div class="section">
        <div class="section-title">Work Patterns</div>
        <div class="grid-3">
            <div class="card">
                <h3>Day of Week</h3>
                <div class="chart-container">
                    <canvas id="dayChart"></canvas>
                </div>
            </div>
            <div class="card">
                <h3>Entry Size Distribution</h3>
                <div class="chart-container">
                    <canvas id="entrySizeChart"></canvas>
                </div>
            </div>
            <div class="card">
                <h3>Work Types</h3>
                <div id="workTypesChart"></div>
            </div>
        </div>
    </div>

    <div class="section">
        <div class="section-title">Trends Over Time</div>
        <div class="grid-2">
            <div class="card">
                <h3>Category Evolution by Year</h3>
                <div class="chart-container">
                    <canvas id="trendChart"></canvas>
                </div>
            </div>
            <div class="card">
                <h3>Tech Stack</h3>
                <table id="techTable"></table>
            </div>
        </div>
    </div>

    <div class="section">
        <div class="section-title">Keywords & Tasks</div>
        <div class="grid-2">
            <div class="card">
                <h3>Top Keywords</h3>
                <div id="keywordBubbles" style="display: flex; flex-wrap: wrap; gap: 0.75rem; justify-content: center; align-items: center; padding: 1rem;"></div>
            </div>
            <div class="card">
                <h3>Frequent Tasks</h3>
                <table id="tasksTable"></table>
            </div>
        </div>
    </div>

    <div class="section">
        <div class="section-title">Clients & Projects</div>
        <div class="grid-2">
            <div class="card">
                <h3>Top Companies</h3>
                <table id="companiesTable"></table>
            </div>
            <div class="card">
                <h3>Top Projects</h3>
                <table id="projectsTable"></table>
            </div>
        </div>
    </div>

    <div class="section">
        <div class="grid-2">
            <div class="card">
                <h3>Top Client by Year</h3>
                <table id="topClientTable"></table>
            </div>
            <div class="card">
                <h3>Client Diversity by Year</h3>
                <div class="chart-container"><canvas id="clientDiversityChart"></canvas></div>
            </div>
        </div>
    </div>

    <div class="generated">Generated {datetime.now().strftime("%Y-%m-%d %H:%M")} from time-report.db</div>

    <script>
        const chartColors = {{ text: '#94a3b8', grid: '#334155' }};
        const groupColors = {json.dumps(GROUP_COLORS)};

        const data = {{
            yearly: {json.dumps(data["yearly"])},
            monthly: {json.dumps(data["monthly"])},
            dayOfWeek: {json.dumps(data["day_of_week"])},
            entrySize: {json.dumps(data["entry_size"])},
            categoryGroups: {json.dumps(category_groups_data)},
            categories: {json.dumps(categories_data[:15])},
            trends: {json.dumps(data["trends"])},
            keywords: {json.dumps(data["keywords"])},
            tasks: {json.dumps(data["tasks"])},
            tech: {json.dumps(data["tech"])},
            workTypes: {json.dumps(work_types)},
            companies: {json.dumps(data["companies"])},
            projects: {json.dumps(data["projects"])},
            topClientByYear: {json.dumps(data["top_client_by_year"])},
            clientDiversity: {json.dumps(data["client_diversity"])}
        }};

        // Yearly Chart
        new Chart(document.getElementById('yearlyChart'), {{
            type: 'bar',
            data: {{
                labels: data.yearly.map(y => y.year),
                datasets: [{{ label: 'Hours', data: data.yearly.map(y => y.hours), backgroundColor: '#38bdf8', borderRadius: 4 }}]
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    y: {{ beginAtZero: true, grid: {{ color: chartColors.grid }}, ticks: {{ color: chartColors.text }} }},
                    x: {{ grid: {{ display: false }}, ticks: {{ color: chartColors.text }} }}
                }}
            }}
        }});

        // Monthly Chart - one line per year (last 3 years visible by default)
        const yearColors = [
            '#38bdf8', '#818cf8', '#a78bfa', '#c084fc', '#f472b6', '#fb7185',
            '#fbbf24', '#4ade80', '#2dd4bf', '#67e8f9', '#f97316', '#84cc16',
            '#06b6d4', '#8b5cf6', '#ec4899', '#ef4444', '#10b981', '#6366f1'
        ];
        const totalYears = data.monthly.years.length;
        const monthlyDatasets = data.monthly.years.map((year, i) => ({{
            label: year,
            data: data.monthly.data[year],
            borderColor: yearColors[i % yearColors.length],
            backgroundColor: 'transparent',
            tension: 0.3,
            pointRadius: 3,
            borderWidth: 2,
            hidden: i < totalYears - 3,
            spanGaps: false
        }}));
        new Chart(document.getElementById('monthlyChart'), {{
            type: 'line',
            data: {{
                labels: data.monthly.months,
                datasets: monthlyDatasets
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                plugins: {{ legend: {{ position: 'right', labels: {{ color: chartColors.text, boxWidth: 12, font: {{ size: 10 }} }} }} }},
                scales: {{
                    y: {{ beginAtZero: true, grid: {{ color: chartColors.grid }}, ticks: {{ color: chartColors.text }} }},
                    x: {{ grid: {{ display: false }}, ticks: {{ color: chartColors.text }} }}
                }}
            }}
        }});

        // Day Chart
        new Chart(document.getElementById('dayChart'), {{
            type: 'bar',
            data: {{
                labels: data.dayOfWeek.map(d => d.day),
                datasets: [{{ label: 'Hours', data: data.dayOfWeek.map(d => d.hours), backgroundColor: data.dayOfWeek.map(d => ['Sat','Sun'].includes(d.day) ? '#64748b' : '#4ade80'), borderRadius: 4 }}]
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    y: {{ beginAtZero: true, grid: {{ color: chartColors.grid }}, ticks: {{ color: chartColors.text }} }},
                    x: {{ grid: {{ display: false }}, ticks: {{ color: chartColors.text }} }}
                }}
            }}
        }});

        // Entry Size Chart
        new Chart(document.getElementById('entrySizeChart'), {{
            type: 'doughnut',
            data: {{
                labels: data.entrySize.map(e => e.size),
                datasets: [{{ data: data.entrySize.map(e => e.count), backgroundColor: ['#64748b','#94a3b8','#38bdf8','#818cf8','#a78bfa'] }}]
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                plugins: {{ legend: {{ position: 'right', labels: {{ color: chartColors.text, boxWidth: 12 }} }} }}
            }}
        }});

        // Categories Chart
        new Chart(document.getElementById('categoriesChart'), {{
            type: 'bar',
            data: {{
                labels: data.categoryGroups.map(c => c.name),
                datasets: [{{ label: 'Hours', data: data.categoryGroups.map(c => c.hours), backgroundColor: data.categoryGroups.map(c => c.color), borderRadius: 4 }}]
            }},
            options: {{
                indexAxis: 'y', responsive: true, maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    x: {{ beginAtZero: true, grid: {{ color: chartColors.grid }}, ticks: {{ color: chartColors.text }} }},
                    y: {{ grid: {{ display: false }}, ticks: {{ color: chartColors.text }} }}
                }}
            }}
        }});

        // Category Table
        document.getElementById('categoryTable').innerHTML = `
            <tr><th>Category</th><th class="text-right">Hours</th><th class="text-right">%</th></tr>
            ${{data.categories.map(c => `<tr><td><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${{groupColors[c.group]}};margin-right:6px;"></span>${{c.name}}</td><td class="text-right">${{c.hours.toLocaleString()}}</td><td class="text-right">${{c.pct}}%</td></tr>`).join('')}}
        `;

        // Trend Chart
        new Chart(document.getElementById('trendChart'), {{
            type: 'line',
            data: {{
                labels: data.trends.years,
                datasets: [
                    {{ label: 'Meetings', data: data.trends.meetings, borderColor: '#fb7185', tension: 0.3, pointRadius: 2 }},
                    {{ label: 'Dev', data: data.trends.dev, borderColor: '#38bdf8', tension: 0.3, pointRadius: 2 }},
                    {{ label: 'QA', data: data.trends.qa, borderColor: '#4ade80', tension: 0.3, pointRadius: 2 }},
                    {{ label: 'Design', data: data.trends.design, borderColor: '#818cf8', tension: 0.3, pointRadius: 2 }},
                    {{ label: 'Deploy', data: data.trends.deploy, borderColor: '#fbbf24', tension: 0.3, pointRadius: 2 }},
                    {{ label: 'AI', data: data.trends.ai, borderColor: '#c084fc', tension: 0.3, pointRadius: 2 }}
                ]
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                plugins: {{ legend: {{ labels: {{ color: chartColors.text }} }} }},
                scales: {{
                    y: {{ beginAtZero: true, grid: {{ color: chartColors.grid }}, ticks: {{ color: chartColors.text }} }},
                    x: {{ grid: {{ display: false }}, ticks: {{ color: chartColors.text }} }}
                }}
            }}
        }});

        // Tech Table
        document.getElementById('techTable').innerHTML = `
            <tr><th>Technology</th><th class="text-right">Hours</th><th class="text-right">Entries</th></tr>
            ${{data.tech.map(t => `<tr><td>${{t.name}}</td><td class="text-right">${{t.hours.toLocaleString()}}</td><td class="text-right">${{t.entries}}</td></tr>`).join('')}}
        `;

        // Keyword Bubbles
        const maxHours = Math.max(...data.keywords.map(k => k.hours));
        const colors = ['#38bdf8','#818cf8','#a78bfa','#4ade80','#fbbf24','#fb7185','#2dd4bf','#f472b6','#67e8f9','#c4b5fd'];
        document.getElementById('keywordBubbles').innerHTML = data.keywords.map((k, i) => {{
            const size = 50 + (k.hours / maxHours) * 70;
            const color = colors[i % colors.length];
            return `<div style="width:${{size}}px;height:${{size}}px;border-radius:50%;background:${{color}}22;border:2px solid ${{color}};display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:0.25rem;" title="${{k.word}}: ${{k.hours}} hrs"><span style="font-size:${{Math.max(10,size/8)}}px;font-weight:600;color:${{color}};">${{k.word}}</span><span style="font-size:${{Math.max(9,size/10)}}px;color:#94a3b8;">${{k.hours}}h</span></div>`;
        }}).join('');

        // Tasks Table
        document.getElementById('tasksTable').innerHTML = `
            <tr><th>Task</th><th class="text-right">Hours</th><th class="text-right">Count</th></tr>
            ${{data.tasks.map(t => `<tr><td>${{t.task}}</td><td class="text-right">${{t.hours}}</td><td class="text-right">${{t.count}}x</td></tr>`).join('')}}
        `;

        // Work Types
        const totalWT = data.workTypes.reduce((s,w) => s + w.hours, 0);
        document.getElementById('workTypesChart').innerHTML = data.workTypes.map(w => {{
            const pct = (w.hours / totalWT * 100).toFixed(1);
            return `<div style="margin-bottom:1.25rem;"><div style="display:flex;justify-content:space-between;margin-bottom:0.5rem;"><span style="font-weight:600;color:${{w.color}};">${{w.name}}</span><span style="color:#e2e8f0;">${{w.hours.toLocaleString()}} hrs (${{pct}}%)</span></div><div style="background:#1e293b;border-radius:0.5rem;height:1.5rem;overflow:hidden;"><div style="background:${{w.color}};height:100%;width:${{pct}}%;border-radius:0.5rem;"></div></div><div style="font-size:0.8rem;color:#94a3b8;margin-top:0.25rem;">${{w.desc}}</div></div>`;
        }}).join('');

        // Companies Table
        const maxCo = Math.max(...data.companies.map(c => c.hours));
        document.getElementById('companiesTable').innerHTML = `
            <tr><th>Company</th><th class="text-right">Hours</th></tr>
            ${{data.companies.map(c => `<tr><td>${{c.name}}<div class="bar"><div class="bar-fill" style="width:${{(c.hours/maxCo*100)}}%"></div></div></td><td class="text-right">${{c.hours.toLocaleString()}}</td></tr>`).join('')}}
        `;

        // Projects Table
        const maxPr = Math.max(...data.projects.map(p => p.hours));
        document.getElementById('projectsTable').innerHTML = `
            <tr><th>Project</th><th class="text-right">Hours</th></tr>
            ${{data.projects.map(p => `<tr><td><span style="color:#64748b;">${{p.company}} -</span> ${{p.name}}<div class="bar"><div class="bar-fill" style="width:${{(p.hours/maxPr*100)}}%"></div></div></td><td class="text-right">${{p.hours.toLocaleString()}}</td></tr>`).join('')}}
        `;

        // Top Client Table
        document.getElementById('topClientTable').innerHTML = `
            <tr><th>Year</th><th>Client</th><th class="text-right">Hours</th></tr>
            ${{data.topClientByYear.map(t => `<tr><td>${{t.year}}</td><td>${{t.client}}</td><td class="text-right">${{t.hours}}</td></tr>`).join('')}}
        `;

        // Client Diversity Chart
        new Chart(document.getElementById('clientDiversityChart'), {{
            type: 'bar',
            data: {{
                labels: data.clientDiversity.map(d => d.year),
                datasets: [{{ label: 'Clients', data: data.clientDiversity.map(d => d.clients), backgroundColor: '#38bdf8', borderRadius: 4 }}]
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    y: {{ beginAtZero: true, grid: {{ color: chartColors.grid }}, ticks: {{ color: chartColors.text }} }},
                    x: {{ grid: {{ display: false }}, ticks: {{ color: chartColors.text }} }}
                }}
            }}
        }});
    </script>
</body>
</html>'''

    return html


def generate_dashboard(person):
    """Generate a complete dashboard for a person."""
    conn = get_connection()

    data = {
        "stats": get_basic_stats(conn, person),
        "yearly": get_yearly_data(conn, person),
        "monthly": get_monthly_aggregate(conn, person),
        "day_of_week": get_day_of_week(conn, person),
        "entry_size": get_entry_size_distribution(conn, person),
        "companies": get_top_companies(conn, person),
        "projects": get_top_projects(conn, person),
        "top_client_by_year": get_top_client_by_year(conn, person),
        "client_diversity": get_client_diversity(conn, person),
        "keywords": get_top_keywords(conn, person),
        "tasks": get_top_tasks(conn, person),
        "category_hours": get_category_hours(conn, person),
        "trends": get_category_trends(conn, person),
        "tech": get_tech_stack(conn, person),
    }

    conn.close()

    html = generate_html(person, data)

    # Generate filename from first name only
    first_name = person.split()[0].lower()
    filename = first_name + ".html"
    output_path = OUTPUT_DIR / filename

    with open(output_path, "w") as f:
        f.write(html)

    print(f"Generated: {output_path}")
    return output_path


def main():
    """Generate dashboards for all people."""
    conn = get_connection()
    people = get_people(conn)
    conn.close()

    print(f"Found {len(people)} people in database")

    for person in people:
        generate_dashboard(person)

    print(f"\nDone! Generated {len(people)} dashboards.")


if __name__ == "__main__":
    main()
