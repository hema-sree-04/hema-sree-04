import os
import json
import urllib.request
from datetime import datetime, timedelta


USERNAME = os.environ.get("GITHUB_USERNAME", "hema-sree-04")
TOKEN = os.environ.get("GITHUB_TOKEN")

OUTPUT_FILE = "assets/contribution-graph.svg"


def get_contributions():
    today = datetime.utcnow().date()
    from_date = today - timedelta(days=365)

    query = """
    query($user:String!, $from:DateTime!, $to:DateTime!) {
        user(login:$user) {
            contributionsCollection(
                from:$from
                to:$to
            ) {
                contributionCalendar {
                    totalContributions
                    weeks {
                        contributionDays {
                            date
                            contributionCount
                        }
                    }
                }
            }
        }
    }
    """

    variables = {
        "user": USERNAME,
        "from": f"{from_date}T00:00:00Z",
        "to": f"{today}T23:59:59Z"
    }

    data = json.dumps({
        "query": query,
        "variables": variables
    }).encode("utf-8")

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=data,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "github-contribution-graph"
        }
    )

    with urllib.request.urlopen(request) as response:
        result = json.loads(response.read().decode("utf-8"))

    if "errors" in result:
        raise Exception(result["errors"])

    calendar = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]

    days = []

    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            days.append({
                "date": day["date"],
                "count": day["contributionCount"]
            })

    return days, calendar["totalContributions"]


def create_svg(days, total):
    width = 1200
    height = 360

    graph_left = 80
    graph_right = 1160
    graph_top = 100
    graph_bottom = 270

    max_count = max([d["count"] for d in days], default=1)

    points = []

    for i, day in enumerate(days):
        x = graph_left + (
            i / max(len(days) - 1, 1)
        ) * (graph_right - graph_left)

        y = graph_bottom - (
            day["count"] / max_count
        ) * (graph_bottom - graph_top)

        points.append((x, y))

    line_points = " ".join(
        f"{x:.1f},{y:.1f}"
        for x, y in points
    )

    area_points = (
        f"{graph_left},{graph_bottom} "
        + line_points
        + f" {graph_right},{graph_bottom}"
    )

    peak = max(
        days,
        key=lambda x: x["count"],
        default={"date": "N/A", "count": 0}
    )

    peak_date = peak["date"]
    peak_count = peak["count"]

    months = []

    last_month = None

    for i, day in enumerate(days):
        month = day["date"][:7]

        if month != last_month:
            x = graph_left + (
                i / max(len(days) - 1, 1)
            ) * (graph_right - graph_left)

            months.append(
                (x, day["date"][:7])
            )

            last_month = month

    month_labels = ""

    for x, month in months:
        month_name = datetime.strptime(
            month,
            "%Y-%m"
        ).strftime("%b")

        month_labels += f"""
        <text
            x="{x:.1f}"
            y="325"
            class="month"
        >
            {month_name}
        </text>
        """

    grid_lines = ""

    for i in range(6):
        y = graph_top + i * (
            (graph_bottom - graph_top) / 5
        )

        grid_lines += f"""
        <line
            x1="{graph_left}"
            y1="{y:.1f}"
            x2="{graph_right}"
            y2="{y:.1f}"
            class="grid"
        />
        """

    svg = f"""<svg
    xmlns="http://www.w3.org/2000/svg"
    width="{width}"
    height="{height}"
    viewBox="0 0 {width} {height}"
>

<style>

.title {{
    font-family: Arial, sans-serif;
    font-size: 22px;
    font-weight: bold;
    fill: #ffffff;
}}

.subtitle {{
    font-family: Arial, sans-serif;
    font-size: 14px;
    fill: #8b949e;
}}

.month {{
    font-family: Arial, sans-serif;
    font-size: 12px;
    fill: #8b949e;
}}

.grid {{
    stroke: #30363d;
    stroke-width: 1;
    opacity: 0.6;
}}

.area {{
    fill: #238636;
    opacity: 0.25;
}}

.line {{
    fill: none;
    stroke: #39d353;
    stroke-width: 3;
}}

.peak {{
    fill: #00e5ff;
    stroke: #ffffff;
    stroke-width: 2;
}}

</style>

<rect
    width="100%"
    height="100%"
    rx="14"
    fill="#0d1117"
/>

<text
    x="40"
    y="42"
    class="title"
>
    Contribution Activity Graph
</text>

<text
    x="40"
    y="68"
    class="subtitle"
>
    {total} contributions in the last year
</text>

<text
    x="850"
    y="42"
    class="subtitle"
>
    Peak day: {peak_count} contributions
</text>

<text
    x="850"
    y="65"
    class="subtitle"
>
    {peak_date}
</text>

{grid_lines}

<polygon
    points="{area_points}"
    class="area"
/>

<polyline
    points="{line_points}"
    class="line"
/>

"""

    if points:
        peak_index = days.index(peak)
        peak_x, peak_y = points[peak_index]

        svg += f"""
        <circle
            cx="{peak_x:.1f}"
            cy="{peak_y:.1f}"
            r="6"
            class="peak"
        />
        """

    svg += month_labels

    svg += """
</svg>
"""

    return svg


def main():
    if not TOKEN:
        raise Exception(
            "GITHUB_TOKEN is not set."
        )

    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True
    )

    days, total = get_contributions()

    svg = create_svg(
        days,
        total
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        file.write(svg)

    print(
        f"Contribution graph generated: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
