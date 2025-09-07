#!/usr/bin/env python3
import os, sys, time, html, smtplib, json, textwrap
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
import requests

# -------- Helpers --------
def env(name, default=None, required=False):
    v = os.getenv(name, default)
    if required and (v is None or v.strip() == ""):
        print(f"Missing required env var: {name}", file=sys.stderr)
        sys.exit(1)
    return v

def ist_now_str():
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).strftime("%Y-%m-%d %H:%M IST")

def google_jobs_search(api_key, query, hl="en"):
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_jobs",
        "q": query,
        "hl": hl,
        "api_key": api_key,
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def gen_outreach(openai_key, job):
    # Minimal prompt to keep tokens low
    try:
        import openai
        from openai import OpenAI
    except Exception as e:
        return f"Install openai>=1.0.0 to generate messages. Error: {e}"
    client = OpenAI(api_key=openai_key)
    company = job.get("company_name", "the company")
    title = job.get("title", "Software Engineer")
    snippet = job.get("description", "")[:240]
    prompt = f"""You are a concise Gen-Z candidate. Write a 450-600 character LinkedIn DM to a recruiter for the role '{title}' at '{company}'. 
Reference one credible thing about the firm based on this snippet (if usable): {snippet!r}. 
Tone: confident, specific, not cringe. Include one short brag and one ask to connect or route my resume. No fluff, no emojis."""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=220,
    )
    return resp.choices[0].message.content.strip()

def send_email(gmail_user, app_password, to_email, subject, html_body):
    msg = MIMEMultipart('alternative')
    msg['From'] = gmail_user
    msg['To'] = to_email
    msg['Subject'] = subject
    part = MIMEText(html_body, 'html')
    msg.attach(part)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(gmail_user, app_password)
        server.sendmail(gmail_user, [to_email], msg.as_string())

# -------- Main --------
def main():
    SERPAPI_KEY = env("SERPAPI_KEY", required=True)
    OPENAI_API_KEY = env("OPENAI_API_KEY", required=False)  # optional; if absent outreach will be a placeholder
    GMAIL_USER = env("GMAIL_USER", required=True)
    GMAIL_APP_PASSWORD = env("GMAIL_APP_PASSWORD", required=True)
    TO_EMAIL = env("TO_EMAIL", required=True)
    MAX_RESULTS = int(env("MAX_RESULTS", "20"))
    COMPANIES = [c.strip() for c in env("COMPANIES", "Google, Meta, Amazon, Apple, Netflix, Microsoft, OpenAI, Stripe, Databricks, DoorDash, Airbnb, Uber").split(",") if c.strip()]
    ROLE_QUERY = env("ROLE_QUERY", "entry level OR new grad full stack OR software engineer")
    SITES_HINT = env("SITES_HINT", "site:boards.greenhouse.io OR site:jobs.lever.co OR site:careers.microsoft.com OR site:amazon.jobs OR site:meta.com/careers OR site:apple.com/careers OR site:google.com/about/careers OR site:netflixjobs.com OR site:about.google")
    DAYS = int(env("DAYS", "2"))  # search window via query only

    jobs = []
    for company in COMPANIES:
        q = f'{ROLE_QUERY} "{company}" ({SITES_HINT})'
        try:
            data = google_jobs_search(SERPAPI_KEY, q)
            for item in data.get("jobs_results", []):
                job = {
                    "title": item.get("title"),
                    "company_name": item.get("company_name", company),
                    "location": item.get("location"),
                    "via": item.get("detected_extensions", {}).get("via"),
                    "extensions": item.get("detected_extensions", {}),
                    "description": item.get("description", ""),
                    "apply_link": None,
                    "job_id": item.get("job_id"),
                }
                # Try to pick an apply link
                apply_options = item.get("apply_options") or []
                if apply_options:
                    job["apply_link"] = apply_options[0].get("link")
                else:
                    # fallback to job link
                    job["apply_link"] = (item.get("related_links") or [{}])[0].get("link") or item.get("share_link")
                jobs.append(job)
        except Exception as e:
            print(f"[warn] {company} query failed: {e}", file=sys.stderr)
        time.sleep(0.8)  # be polite to API
        if len(jobs) >= MAX_RESULTS:
            break

    # Dedup by title+company
    seen = set()
    deduped = []
    for j in jobs:
        key = (j.get("title"), j.get("company_name"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(j)
    jobs = deduped[:MAX_RESULTS]

    # Outreach messages
    for j in jobs:
        if OPENAI_API_KEY:
            try:
                j["outreach"] = gen_outreach(OPENAI_API_KEY, j)
            except Exception as e:
                j["outreach"] = f"(Generate later) Error using OpenAI API: {e}"
        else:
            j["outreach"] = "(Set OPENAI_API_KEY to auto-generate outreach messaging.)"

    # HTML email
    rows = []
    for idx, j in enumerate(jobs, 1):
        title = html.escape(j.get("title") or "")
        comp = html.escape(j.get("company_name") or "")
        loc = html.escape(j.get("location") or "")
        link = html.escape(j.get("apply_link") or "#")
        desc = html.escape((j.get("description") or "").strip()[:420]).replace("\n", " ")
        outreach = html.escape(j.get("outreach") or "").replace("\n", "<br>")
        rows.append(f"""
        <tr>
          <td style="padding:8px; border-bottom:1px solid #eee; vertical-align:top;">{idx}</td>
          <td style="padding:8px; border-bottom:1px solid #eee; vertical-align:top;">
            <div style="font-weight:600">{title}</div>
            <div style="color:#555">{comp} — {loc}</div>
            <div style="margin-top:6px; font-size:13px; color:#444">{desc}</div>
            <div style="margin-top:6px"><a href="{link}">Apply Link</a></div>
            <div style="margin-top:10px; font-size:13px;">
              <div style="font-weight:600; margin-bottom:4px;">DM draft:</div>
              <div>{outreach}</div>
            </div>
          </td>
        </tr>
        """)

    if not rows:
        rows_html = '<tr><td colspan="2" style="padding:12px;">No fresh roles found today. Try widening COMPANIES or ROLE_QUERY.</td></tr>'
    else:
        rows_html = "\n".join(rows)

    subject = f"[Daily SDE Digest] {len(jobs)} roles — {ist_now_str()}"
    html_body = f"""<div style="font-family:Inter,Arial,sans-serif; line-height:1.45;">
      <h2 style="margin:0 0 8px;">Entry-level SDE / Full-Stack Roles</h2>
      <div style="font-size:13px; color:#666; margin-bottom:12px;">Generated at {ist_now_str()}</div>
      <table cellpadding="0" cellspacing="0" width="100%" style="border-collapse:collapse;">
        <thead>
          <tr>
            <th style="text-align:left; padding:8px; border-bottom:2px solid #000;">#</th>
            <th style="text-align:left; padding:8px; border-bottom:2px solid #000;">Role</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
      <div style="margin-top:16px; font-size:12px; color:#666;">Tip: Tweak COMPANIES / ROLE_QUERY in env to refine.</div>
    </div>"""

    send_email(GMAIL_USER, GMAIL_APP_PASSWORD, TO_EMAIL, subject, html_body)
    print(f"Sent digest to {TO_EMAIL} with {len(jobs)} jobs.")

if __name__ == "__main__":
    main()
