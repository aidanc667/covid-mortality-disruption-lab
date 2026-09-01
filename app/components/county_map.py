"""Interactive US county choropleth for the real diabetes/overdose county
disruption data, built with Altair/Vega-Lite (this project's preferred
charting library) against the public us-atlas county TopoJSON -- no
geopandas/shapely/folium dependency, so the app's requirements.txt stays
lean (research_protocol.md's deployment-prep decision, 2026-09-01).
"""
import altair as alt
import pandas as pd

COUNTIES_TOPOJSON_URL = "https://cdn.jsdelivr.net/npm/us-atlas@3/counties-10m.json"
STATES_TOPOJSON_URL = COUNTIES_TOPOJSON_URL  # same file also bundles a 'states' object


def render_county_choropleth(disruption_df: pd.DataFrame, cause: str, value_col: str = "disruption") -> alt.LayerChart:
    """disruption_df must have `county_fips` (5-digit zero-padded string,
    matching the topojson's county `id` field exactly -- verified against
    a real fetch of the topojson, not assumed) and `value_col`. Counties
    with no matching row (excluded upstream for insufficient non-suppressed
    years) render in a neutral gray rather than the color scale, so
    missing data is visually distinct from a real zero."""
    counties = alt.topo_feature(COUNTIES_TOPOJSON_URL, "counties")
    states = alt.topo_feature(STATES_TOPOJSON_URL, "states")

    vmax = float(disruption_df[value_col].abs().max())

    county_layer = (
        alt.Chart(counties)
        .mark_geoshape(stroke="white", strokeWidth=0.2)
        .transform_lookup(
            lookup="id",
            from_=alt.LookupData(disruption_df, "county_fips", [value_col, "crude_rate_pre", "crude_rate_post"]),
        )
        .encode(
            color=alt.condition(
                f"datum.{value_col} !== null",
                alt.Color(
                    f"{value_col}:Q",
                    scale=alt.Scale(scheme="redblue", domain=[vmax, -vmax]),
                    title="Disruption (post − pre, crude rate)",
                    legend=alt.Legend(orient="bottom", gradientLength=280),
                ),
                alt.value("#E5E7EB"),
            ),
            tooltip=[
                alt.Tooltip("county_fips:N", title="County FIPS"),
                alt.Tooltip(f"{value_col}:Q", title="Disruption", format="+.1f"),
                alt.Tooltip("crude_rate_pre:Q", title="Pre-period rate", format=".1f"),
                alt.Tooltip("crude_rate_post:Q", title="Post-period rate", format=".1f"),
            ],
        )
    )

    state_borders = alt.Chart(states).mark_geoshape(fill=None, stroke="#1E1B2E", strokeWidth=0.6)

    return (
        (county_layer + state_borders)
        .project(type="albersUsa")
        .properties(width="container", height=460, title=f"{cause}: county-level disruption (crude rate, post − pre)")
    )
