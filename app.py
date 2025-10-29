import io
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import altair as alt


def set_page_config() -> None:
	st.set_page_config(
		page_title="Ads + Analytics Dashboard",
		page_icon="📊",
		layout="wide",
		initial_sidebar_state="expanded",
	)


def coerce_numeric(series: pd.Series) -> pd.Series:
	cleaned = (
		series.astype(str)
		.str.replace(",", "", regex=False)
		.str.replace("$", "", regex=False)
		.str.replace("%", "", regex=False)
		.str.strip()
	)
	return pd.to_numeric(cleaned, errors="coerce")


def parse_hms_to_seconds(value: str) -> Optional[float]:
	if pd.isna(value):
		return None
	text = str(value).strip()
	# Accept formats like H:MM:SS or MM:SS
	parts = text.split(":")
	try:
		if len(parts) == 3:
			hours = int(parts[0])
			minutes = int(parts[1])
			seconds = int(parts[2])
			return float(hours * 3600 + minutes * 60 + seconds)
		if len(parts) == 2:
			minutes = int(parts[0])
			seconds = int(parts[1])
			return float(minutes * 60 + seconds)
		return coerce_numeric(pd.Series([text]))[0]
	except Exception:
		return None


def standardize_url_path(path: str) -> str:
	if pd.isna(path):
		return ""
	text = str(path).strip()
	# Ensure it starts with '/'
	if not text.startswith("/"):
		text = "/" + text
	# Remove trailing slashes except root
	if len(text) > 1 and text.endswith("/"):
		text = text[:-1]
	return text


def detect_and_clean_ga4(raw: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
	column_aliases = {
		"date": ["date"],
		"url": ["page path and query string", "page", "page path"],
		"views": ["views", "screen page views", "pageviews"],
		"users": ["users"],
		"engagement": ["avg. engagement time", "average engagement time"],
		"revenue": ["total ad revenue", "ad revenue", "revenue"],
	}

	def find_col(name_list: List[str]) -> Optional[str]:
		lower_map = {c.lower(): c for c in raw.columns}
		for alias in name_list:
			if alias.lower() in lower_map:
				return lower_map[alias.lower()]
		return None

	mapping: Dict[str, Optional[str]] = {
		"date": find_col(column_aliases["date"]),
		"url": find_col(column_aliases["url"]),
		"views": find_col(column_aliases["views"]),
		"users": find_col(column_aliases["users"]),
		"engagement": find_col(column_aliases["engagement"]),
		"revenue": find_col(column_aliases["revenue"]),
	}

	clean = pd.DataFrame()
	if mapping["date"] is not None:
		clean["date"] = pd.to_datetime(raw[mapping["date"]], errors="coerce")
	if mapping["url"] is not None:
		clean["url"] = raw[mapping["url"]].apply(standardize_url_path)
	if mapping["views"] is not None:
		clean["ga_views"] = coerce_numeric(raw[mapping["views"]])
	if mapping["users"] is not None:
		clean["ga_users"] = coerce_numeric(raw[mapping["users"]])
	if mapping["engagement"] is not None:
		clean["ga_engagement_seconds"] = raw[mapping["engagement"]].apply(parse_hms_to_seconds)
	if mapping["revenue"] is not None:
		clean["ga_revenue"] = coerce_numeric(raw[mapping["revenue"]])

	return clean, {k: (mapping[k] or "") for k in mapping}


def detect_and_clean_gam(raw: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
	column_aliases = {
		"date": ["date"],
		"url": ["custom targeting (url)", "url", "key-value url"],
		"impressions": ["total impressions", "impressions"],
		"revenue": ["total revenue", "revenue", "ad server revenue"],
		"ecpm": ["total ecpm", "ecpm"],
	}

	def find_col(name_list: List[str]) -> Optional[str]:
		lower_map = {c.lower(): c for c in raw.columns}
		for alias in name_list:
			if alias.lower() in lower_map:
				return lower_map[alias.lower()]
		return None

	mapping: Dict[str, Optional[str]] = {
		"date": find_col(column_aliases["date"]),
		"url": find_col(column_aliases["url"]),
		"impressions": find_col(column_aliases["impressions"]),
		"revenue": find_col(column_aliases["revenue"]),
		"ecpm": find_col(column_aliases["ecpm"]),
	}

	clean = pd.DataFrame()
	if mapping["date"] is not None:
		clean["date"] = pd.to_datetime(raw[mapping["date"]], errors="coerce")
	if mapping["url"] is not None:
		clean["url"] = raw[mapping["url"]].apply(standardize_url_path)
	if mapping["impressions"] is not None:
		clean["gam_impressions"] = coerce_numeric(raw[mapping["impressions"]])
	if mapping["revenue"] is not None:
		clean["gam_revenue"] = coerce_numeric(raw[mapping["revenue"]])
	if mapping["ecpm"] is not None:
		clean["gam_ecpm"] = coerce_numeric(raw[mapping["ecpm"]])

	return clean, {k: (mapping[k] or "") for k in mapping}


def ensure_minimal_columns(df: pd.DataFrame, required: List[str]) -> bool:
	return all(col in df.columns for col in df.columns)


def render_mapping_helpbox(title: str, mapping: Dict[str, str]) -> None:
	with st.expander(title, expanded=False):
		st.write("Detected columns:")
		st.json(mapping)
		st.caption("If any field is blank, check your CSV headers match expected names.")


def aggregate_for_charts(df: pd.DataFrame) -> pd.DataFrame:
	metrics = [
		"ga_views",
		"ga_users",
		"ga_engagement_seconds",
		"ga_revenue",
		"gam_impressions",
		"gam_revenue",
		"gam_ecpm",
	]
	present = [m for m in metrics if m in df.columns]
	if not present:
		return pd.DataFrame()
	grouped = (
		df.groupby("date", as_index=False)[present]
		.sum(numeric_only=True)
	)
	return grouped


def long_format(df: pd.DataFrame, value_cols: List[str], var_name: str = "metric", value_name: str = "value") -> pd.DataFrame:
	keep_cols = [c for c in ["date", "url"] if c in df.columns]
	return df.melt(id_vars=keep_cols, value_vars=[c for c in value_cols if c in df.columns], var_name=var_name, value_name=value_name)


def render_charts(filtered: pd.DataFrame) -> None:
	if filtered.empty:
		st.info("No data to chart. Add filters or upload data.")
		return

	agg = aggregate_for_charts(filtered)
	if not agg.empty:
		metrics_ts = long_format(agg, [c for c in agg.columns if c != "date" and c != "url"])
		base = alt.Chart(metrics_ts).encode(x="date:T", y="value:Q", color="metric:N")
		st.subheader("Time series (aggregated across selected URLs)")
		st.altair_chart(base.mark_line(point=True).properties(height=300), use_container_width=True)

	if {"ga_views", "gam_impressions"}.issubset(filtered.columns):
		st.subheader("Scatter: GA Views vs GAM Impressions")
		scatter = (
			alt.Chart(filtered)
			.mark_circle(size=80, opacity=0.6)
			.encode(
				x=alt.X("ga_views:Q", title="GA Views"),
				y=alt.Y("gam_impressions:Q", title="GAM Impressions"),
				color=alt.Color("url:N", legend=None),
				tooltip=["date:T", "url:N", "ga_views:Q", "gam_impressions:Q", "ga_revenue:Q", "gam_revenue:Q"],
			)
			.properties(height=320)
		)
		st.altair_chart(scatter, use_container_width=True)

	if {"ga_revenue", "gam_revenue"}.issubset(filtered.columns):
		st.subheader("Revenue comparison over time")
		rev_long = long_format(aggregate_for_charts(filtered), ["ga_revenue", "gam_revenue"])
		rev_chart = (
			alt.Chart(rev_long)
			.mark_line(point=True)
			.encode(x="date:T", y="value:Q", color=alt.Color("metric:N", title="Dataset"))
			.properties(height=300)
		)
		st.altair_chart(rev_chart, use_container_width=True)


def main() -> None:
	set_page_config()
	st.title("📊 Ads + Analytics Dashboard")
	st.caption("Upload Google Analytics 4 (GA4) and Google Ad Manager (GAM) CSVs to explore and compare metrics by URL and date.")

	with st.sidebar:
		st.header("Upload CSVs")
		ga_file = st.file_uploader("GA4 CSV", type=["csv"], key="ga_csv")
		gam_file = st.file_uploader("GAM CSV", type=["csv"], key="gam_csv")
		st.markdown("---")
		st.caption("Tip: Export with headers including Date and URL path.")

	ga_raw: Optional[pd.DataFrame] = None
	gam_raw: Optional[pd.DataFrame] = None

	if ga_file is not None:
		ga_raw = pd.read_csv(ga_file)
	if gam_file is not None:
		gam_raw = pd.read_csv(gam_file)

	# Demo: allow loading provided examples if nothing uploaded
	if ga_raw is None and gam_raw is None:
		with st.expander("Or load included samples", expanded=True):
			col_a, col_b = st.columns(2)
			with col_a:
				if st.button("Load sample GA4"):
					ga_raw = pd.read_csv("/Users/richcao/Desktop/Cursor_Projects/GA4_Sample_URLID.csv")
			with col_b:
				if st.button("Load sample GAM"):
					gam_raw = pd.read_csv("/Users/richcao/Desktop/Cursor_Projects/GAM_Sample Report_URLID.csv")

	ga_clean: Optional[pd.DataFrame] = None
	gam_clean: Optional[pd.DataFrame] = None
	ga_map: Dict[str, str] = {}
	gam_map: Dict[str, str] = {}

	if ga_raw is not None:
		st.subheader("GA4 preview")
		st.dataframe(ga_raw.head(50), use_container_width=True)
		ga_clean, ga_map = detect_and_clean_ga4(ga_raw)
		render_mapping_helpbox("GA4 column detection", ga_map)
		if not ga_clean.empty:
			st.caption("GA4 cleaned columns available: " + ", ".join(list(ga_clean.columns)))

	if gam_raw is not None:
		st.subheader("GAM preview")
		st.dataframe(gam_raw.head(50), use_container_width=True)
		gam_clean, gam_map = detect_and_clean_gam(gam_raw)
		render_mapping_helpbox("GAM column detection", gam_map)
		if not gam_clean.empty:
			st.caption("GAM cleaned columns available: " + ", ".join(list(gam_clean.columns)))

	# Merge and filter controls
	merged = None
	if ga_clean is not None and gam_clean is not None and not ga_clean.empty and not gam_clean.empty:
		merged = pd.merge(ga_clean, gam_clean, on=["date", "url"], how="outer")
		merged.sort_values(["date", "url"], inplace=True)

	st.markdown("---")
	st.subheader("Filters")
	active_df = None
	if merged is not None:
		active_df = merged.copy()
	elif ga_clean is not None and not (ga_clean is None or ga_clean.empty):
		active_df = ga_clean.copy()
	elif gam_clean is not None and not (gam_clean is None or gam_clean.empty):
		active_df = gam_clean.copy()

	if active_df is None or active_df.empty:
		st.info("Upload at least one CSV to begin.")
		st.stop()

	# Date range filter
	min_date = pd.to_datetime(active_df["date"].min()) if "date" in active_df.columns else None
	max_date = pd.to_datetime(active_df["date"].max()) if "date" in active_df.columns else None
	if min_date is not None and max_date is not None:
		start_date, end_date = st.slider(
			"Date range",
			min_value=min_date.to_pydatetime(),
			max_value=max_date.to_pydatetime(),
			value=(min_date.to_pydatetime(), max_date.to_pydatetime()),
			format="YYYY-MM-DD",
		)
		active_df = active_df[(active_df["date"] >= pd.to_datetime(start_date)) & (active_df["date"] <= pd.to_datetime(end_date))]

	# URL filter
	urls = sorted([u for u in active_df["url"].dropna().unique()]) if "url" in active_df.columns else []
	selected_urls = st.multiselect("URLs", urls, default=urls[: min(5, len(urls))]) if urls else []
	if selected_urls:
		active_df = active_df[active_df["url"].isin(selected_urls)]

	st.markdown("---")
	st.subheader("Data table")
	st.dataframe(active_df, use_container_width=True)

	st.markdown("---")
	render_charts(active_df)


if __name__ == "__main__":
	main()


