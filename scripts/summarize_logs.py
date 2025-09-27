#!/usr/bin/env python3
"""
Summarize WhatsApp message log files using OpenAI.

Usage:
  export OPENAI_API_KEY=your_key_here
  export SLACK_BOT_TOKEN=xoxb-...           # if you want to post to Slack
  # Optional SSL envs: OPENAI_CA_BUNDLE=/path/to/cacert.pem, OPENAI_INSECURE_SKIP_VERIFY=true
  python scripts/summarize_logs.py message-logs/retail-all-stars-messages-2025-09-26.txt
  python scripts/summarize_logs.py message-logs/*.txt
  # Optional flags: --ca-bundle /path/to/cacert.pem, --insecure
  # Slack options: --slack --slack-channel C09BK6AGAF7

Output:
  Creates a sibling file next to each input, with suffix ".summary.txt"
  If --slack is provided, also posts a Slack Block Kit message to the channel.
"""


from __future__ import annotations
import os
import sys
import json
import time
import argparse
# Target group names to monitor (should match server.js configuration)
TARGET_GROUP_NAMES = [
    'retail all-stars',
    'Seeds+Customer Support',
    'Winwise Agent Support',
    'Merchant Acquisition_Paybox'
]

def sanitize_group_name(group_name: str) -> str:
    """Sanitize group name for use in filenames (same logic as server.js)"""
    sanitized = group_name.lower()
    sanitized = re.sub(r'[^a-z0-9\s]', '', sanitized)  # Remove special characters except spaces
    sanitized = re.sub(r'\s+', '-', sanitized)         # Replace spaces with hyphens
    return sanitized.strip()

def find_most_recent_log_files(log_dir: str = "message-logs") -> dict:
    """
    Find the most recent log file for each target group.
    Returns dict: {group_name: file_path} for groups that have log files.
    """
    if not os.path.exists(log_dir):
        return {}

    # Group files by sanitized group name
    group_files = {}

    for filename in os.listdir(log_dir):
        if not filename.endswith('.txt') or 'summary' in filename:
            continue

        # Extract date from filename pattern: {group}-messages-YYYY-MM-DD.txt
        if '-messages-' not in filename:
            continue

        parts = filename.split('-messages-')
        if len(parts) != 2:
            continue

        group_part = parts[0]
        date_part = parts[1].replace('.txt', '')

        # Try to parse date
        try:
            date_obj = datetime.strptime(date_part, '%Y-%m-%d')
        except ValueError:
            continue

        # Find matching target group
        matching_group = None
        for target_group in TARGET_GROUP_NAMES:
            if sanitize_group_name(target_group) == group_part:
                matching_group = target_group
                break

        if matching_group:
            file_path = os.path.join(log_dir, filename)
            if matching_group not in group_files or date_obj > group_files[matching_group]['date']:
                group_files[matching_group] = {
                    'path': file_path,
                    'date': date_obj,
                    'filename': filename
                }

    # Return just the file paths
    return {group: info['path'] for group, info in group_files.items()}
from datetime import datetime
from typing import List
import urllib.request
import urllib.error
import ssl
try:
    import certifi  # optional, improves SSL trust store
except Exception:
    certifi = None

import re

# Configuration
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
TIMEOUT_SECONDS = 120
CHUNK_SIZE_CHARS = 15000  # ~3.5-4k tokens per chunk (approx)
INTERMEDIATE_SUMMARY_TARGET_WORDS = 200
FINAL_SUMMARY_TARGET_WORDS = 350

# CLI overrides (set in main)
CLI_INSECURE = False
CLI_CA_BUNDLE = None



def build_ssl_context():
    """Build an SSL context with best-effort CA resolution.
    Order of preference:
      1) CLI --insecure or env OPENAI_INSECURE_SKIP_VERIFY=true (skip verification; not recommended)
      2) CLI --ca-bundle or env OPENAI_CA_BUNDLE (custom CA bundle path)
      3) certifi bundle if available
      4) system default
    """
    # 1) Insecure (skip verification)
    env_insecure = os.getenv("OPENAI_INSECURE_SKIP_VERIFY", "").lower() in {"1", "true", "yes"}
    if CLI_INSECURE or env_insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    # 2) Explicit CA bundle
    ca_bundle = CLI_CA_BUNDLE or os.getenv("OPENAI_CA_BUNDLE")
    if ca_bundle and os.path.exists(ca_bundle):
        ctx = ssl.create_default_context()
        ctx.load_verify_locations(cafile=ca_bundle)
        return ctx

    # 3) certifi if available
    if 'certifi' in globals() and certifi is not None:
        try:
            cafile = certifi.where()
            ctx = ssl.create_default_context()
            ctx.load_verify_locations(cafile=cafile)
            return ctx
        except Exception:
            pass

    # 4) system default
    return ssl.create_default_context()


def die(msg: str, code: int = 1):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(code)


def load_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        die("OPENAI_API_KEY environment variable not set.\n"
            "Set it with: export OPENAI_API_KEY=your_key_here")
    return key


def http_post_json(url: str, payload: dict, headers: dict, timeout: int = TIMEOUT_SECONDS) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    # Build SSL context with best effort CA resolution
    ctx = build_ssl_context()

    # Simple retry loop for transient errors
    max_attempts = int(os.getenv("OPENAI_RETRIES", "3"))
    backoff = float(os.getenv("OPENAI_RETRY_BACKOFF", "0.8"))

    for attempt in range(1, max_attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            status = getattr(e, 'code', None)
            detail = e.read().decode("utf-8", errors="ignore")
            # Retry on 429 or 5xx
            if status in {429, 500, 502, 503, 504} and attempt < max_attempts:
                time.sleep(backoff * attempt)
                continue
            raise RuntimeError(f"HTTP {status} error from OpenAI API: {detail}")
        except urllib.error.URLError as e:
            if attempt < max_attempts:
                time.sleep(backoff * attempt)
                continue
            raise RuntimeError(f"Network error calling OpenAI API: {e}")


def chat_completion(api_key: str, model: str, system_prompt: str, user_content: str, temperature: float = 0.2) -> str:
    url = f"{OPENAI_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": temperature,
    }
    resp = http_post_json(url, payload, headers)
    try:
        return resp["choices"][0]["message"]["content"].strip()
    except Exception as e:
        raise RuntimeError(f"Unexpected response format from OpenAI: {e}; body={resp}")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_CHARS) -> List[str]:
    text = text.replace("\r\n", "\n")
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        # Try to break at a line boundary for cleaner chunks
        if end < len(text):
            nl = text.rfind("\n", start, end)
            if nl != -1 and nl > start + 1000:  # avoid tiny last fragment
                end = nl + 1
        chunks.append(text[start:end])
        start = end
    return chunks



CHUNK_ISSUES_SYSTEM_PROMPT = (
    "You are a precise support issue extractor. Input is a portion of a WhatsApp group log, "
    "where each line looks like: [ISO_TIMESTAMP] Sender: Message. "
    "Your job is to detect DISTINCT customer support issues mentioned in THIS CHUNK ONLY. "
    "Output requirements: "
    "- Categories must be SHORT, CANONICAL, and ACTION/OUTCOME-ORIENTED. "
    "- Use clear names like: 'Funds not reflected', 'Bill upload failure', 'Payment not processing', 'Loan disbursement delay', 'Refund request'. "
    "- Merge near-duplicates within the chunk into one category. "
    "- Avoid vague or emotional labels (e.g., 'customer angry', 'complaints', 'disturbance'). Always map to a concrete support issue. "
    "- For each category, return: category (string), occurrences (int), last_seen (ISO 8601 timestamp string), samples (array of 1-3 example messages from the log). "
    "- last_seen must be the exact ISO timestamp from the log (e.g., '2025-09-26T19:14:45.987000+00:00'). "
    "- samples should contain 1-3 representative message texts that demonstrate this issue category. Keep them brief but informative. "
    "- If no valid issues, return an empty array []. "
    "Respond with ONLY a JSON array. No prose, no code fences."
)


CONSOLIDATE_CATEGORIES_SYSTEM_PROMPT = (
    "You are a taxonomy expert. Input is a JSON array of issue categories with occurrences, last_seen timestamps, and sample messages. "
    "Your job: CONSOLIDATE them into a SMALL set of clean, canonical categories. "
    "Instructions: "
    "- Merge semantically similar or overly specific categories into one. "
    "- Choose the clearest, action/outcome-oriented label. "
    "- Sum occurrences across merged items. "
    "- For last_seen, keep the LATEST timestamp in ISO 8601 format. "
    "- For samples, combine and select the most representative 2-3 examples from all merged categories. "
    "- Exclude vague or non-actionable categories (e.g., 'general complaint', 'customer upset'). "
    "- Aim for clarity, minimal overlap, and no redundancy. "
    "Output ONLY a JSON array of objects with fields: category (string), occurrences (int), last_seen (ISO 8601 string), samples (array of strings). "
    "No prose, no code fences."
)




def consolidate_categories_via_openai(api_key: str, model: str, items: list) -> list:
    if not items:
        return []
    user = json.dumps(items, ensure_ascii=False)
    out = chat_completion(api_key, model, CONSOLIDATE_CATEGORIES_SYSTEM_PROMPT, user)
    arr = _extract_json_array(out)
    result = []
    for it in arr:
        try:
            cat = str(it.get('category','')).strip()
            if not cat:
                continue
            occ = int(it.get('occurrences', 0))
            last = it.get('last_seen') or ''
            samples = it.get('samples', [])
            if not isinstance(samples, list):
                samples = []
            result.append({'category': cat, 'occurrences': max(0, occ), 'last_seen': last, 'samples': samples})
        except Exception:
            continue
    return result or items

def _extract_json_array(text: str) -> list:
    """Try to parse a JSON array from model output, tolerating code fences."""
    s = text.strip()
    # Strip common code fences
    if s.startswith("```"):
        s = s.strip('`')
        # remove potential language hint
        if "\n" in s:
            s = s.split("\n", 1)[1]
    # Find first '[' and last ']'
    start = s.find('[')
    end = s.rfind(']')
    if start != -1 and end != -1 and end > start:
        s = s[start:end+1]
    try:
        arr = json.loads(s)
        if isinstance(arr, list):
            return arr
    except Exception:
        pass
    return []


def _parse_ts(ts: str):
    try:
        t = ts.strip().replace('Z', '+00:00')
        return datetime.fromisoformat(t)
    except Exception:
        return None


def summarize_file(path: str, api_key: str, model: str = DEFAULT_MODEL) -> str:
    if not os.path.isfile(path):
        die(f"Input is not a file: {path}")

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    if not content.strip():
        return "No content found in the log file."

    # Aggregate issues across chunks
    chunks = chunk_text(content)
    issues_agg = {}  # key -> {category, occurrences, last_seen}

    for i, chunk in enumerate(chunks, 1):
        print(f"- Extracting issues from chunk {i}/{len(chunks)} (chars={len(chunk)})...")
        user_prompt = (
            "Extract distinct issues from this log chunk. Return ONLY JSON array as specified.\n\n"
            "CHUNK BEGIN\n" + chunk + "\nCHUNK END"
        )
        out = chat_completion(api_key, model, CHUNK_ISSUES_SYSTEM_PROMPT, user_prompt)
        arr = _extract_json_array(out)
        for item in arr:
            try:
                category = str(item.get('category') or item.get('issue') or '').strip()
                if not category:
                    continue
                key = category.lower()
                occ = int(item.get('occurrences', 0))
                last = item.get('last_seen')
                samples = item.get('samples', [])
                if not isinstance(samples, list):
                    samples = []
                last_dt = _parse_ts(last) if last else None
                if key not in issues_agg:
                    issues_agg[key] = {"category": category, "occurrences": 0, "last_seen": None, "samples": []}
                issues_agg[key]["occurrences"] += max(0, occ)
                # Add new samples, avoiding duplicates
                for sample in samples:
                    if sample and sample not in issues_agg[key]["samples"]:
                        issues_agg[key]["samples"].append(sample)
                # Keep only the most recent 3 samples
                issues_agg[key]["samples"] = issues_agg[key]["samples"][-3:]
                if last_dt:
                    cur_dt = _parse_ts(issues_agg[key]["last_seen"]) if issues_agg[key]["last_seen"] else None
                    if not cur_dt or last_dt > cur_dt:
                        issues_agg[key]["last_seen"] = last_dt.isoformat()
            except Exception:
                continue
        time.sleep(0.3)  # be polite

    if not issues_agg:
        return "Unique Issues\n- No issues detected."

    # Initial list
    items = list(issues_agg.values())

    # Consolidate semantically similar categories via OpenAI for better taxonomy
    try:
        items = consolidate_categories_via_openai(api_key, model, items)
    except Exception:
        pass

    # Sort by occurrences desc, then last_seen desc
    def sort_key(it):
        return (-int(it.get("occurrences", 0)), it.get("last_seen", ""))
    items.sort(key=sort_key)

    # Format final summary text
    lines = ["Unique Issues"]
    for it in items:
        name = it.get('category') or it.get('issue') or ''
        last_seen = it.get('last_seen', '')
        samples = it.get('samples', [])

        # Format timestamp for display
        if last_seen:
            try:
                dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                formatted_time = dt.strftime('%b %d, %Y %I:%M %p')
            except Exception:
                formatted_time = last_seen
        else:
            formatted_time = 'Unknown'

        lines.append(f"- Category: {name}")
        lines.append(f"  - Occurrences: {it.get('occurrences', 0)}")
        lines.append(f"  - Last Occurrence: {formatted_time}")
        if samples:
            lines.append(f"  - Sample Messages:")
            for sample in samples[:3]:  # Limit to 3 samples
                lines.append(f"    • {sample}")
    return "\n".join(lines).strip()


def derive_output_path(input_path: str) -> str:
    """
    Derive output path for summary file.
    Input: message-logs/seedscustomer-support-messages-2025-09-26.txt
    Output: summaries/seedscustomer-support-summary.txt
    """
    # Create summaries directory if it doesn't exist
    summaries_dir = "summaries"
    os.makedirs(summaries_dir, exist_ok=True)

    # Extract group name from filename
    filename = os.path.basename(input_path)
    # Expected format: {group-name}-messages-{date}.txt
    if "-messages-" in filename:
        group_name = filename.split("-messages-")[0]
    else:
        # Fallback: use the base filename without extension
        group_name = os.path.splitext(filename)[0]

    # Create output filename: {group-name}-summary.txt
    output_filename = f"{group_name}-summary.txt"
    return os.path.join(summaries_dir, output_filename)


def write_summary(output_path: str, input_path: str, summary: str, model: str):
    """Write summary to output file, ensuring the directory exists."""
    # Ensure the output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    header = (
        f"Summary for: {os.path.basename(input_path)}\n"
        f"Generated at: {datetime.now().isoformat(timespec='seconds')}\n"
        f"Model: {model}\n"
        f"\n"
        f"=== Summary ===\n\n"
    )
    with open(output_path, "a+", encoding="utf-8") as f:
        f.write(header)
        f.write(summary.strip() + "\n")


def slackify_summary(text: str) -> str:
    """Convert generic Markdown-ish summary to Slack mrkdwn-friendly text.
    - Convert **bold** to *bold*
    - Normalize line breaks
    - Turn leading "- " bullets into "• "
    """
    if not text:
        return ""
    s = text.replace("\r\n", "\n").replace("\r", "\n")
    # **bold** -> *bold*
    s = re.sub(r"\*\*(.+?)\*\*", r"*\1*", s)
    # Leading dashes (with optional indent) to bullets at start of lines
    s = re.sub(r"(?m)^(\s*)-\s+", r"\1• ", s)
    # Collapse excessive blank lines
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def is_summary_file(path: str) -> bool:
    name = os.path.basename(path)
    # Check for both old format (.summary.txt) and new format (-summary.txt)
    return ((".summary" in name and name.endswith(".txt")) or
            (name.endswith("-summary.txt")))


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

# ---------------- Slack helpers ----------------


def _parse_unique_issues_from_text(text: str) -> list:
    """Parse the 'Unique Issues' plain text into structured items.
    Expected format lines like:
      - Category: ...
        - Occurrences: N
        - Last Occurrence: ISO
        - Sample Messages:
          • message 1
          • message 2
    Returns list of dicts: {category, occurrences, last_seen, samples}
    """
    items = []
    cur = None
    in_samples = False

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        if line.startswith("- Category:"):
            if cur:
                items.append(cur)
            category = line.split(":", 1)[1].strip()
            cur = {"category": category, "occurrences": 0, "last_seen": "", "samples": []}
            in_samples = False

        elif "Occurrences:" in line and cur is not None:
            m = re.search(r"Occurrences:\s*(\d+)", line)
            if m:
                try:
                    cur["occurrences"] = int(m.group(1))
                except Exception:
                    pass
            in_samples = False

        elif "Last Occurrence:" in line and cur is not None:
            ts = line.split(":", 1)[1].strip()
            cur["last_seen"] = ts
            in_samples = False

        elif "Sample Messages:" in line and cur is not None:
            in_samples = True

        elif in_samples and cur is not None and line.startswith("•"):
            # Sample message - handle both "• " and "    • " formats
            sample = line.lstrip("• ").strip()
            if sample:
                cur["samples"].append(sample)

    if cur:
        items.append(cur)
    return items


def _severity_emoji(occ: int) -> str:
    if occ >= 10:
        return ":red_circle:"
    if occ >= 3:
        return ":large_orange_circle:"
    return ":large_blue_circle:"

SLACK_DEFAULT_CHANNEL = os.getenv("SLACK_CHANNEL", "C09H94MKUP5")
SLACK_API_BASE = os.getenv("SLACK_API_BASE", "https://slack.com/api")


def build_slack_blocks_for_summary(filename: str, model: str, summary: str) -> dict:
    # Try to parse the unique-issues format; if it fails, fall back to plain text
    items = _parse_unique_issues_from_text(summary)

    blocks = []
    # Header
    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": "WhatsApp Log — Unique Issues", "emoji": True}
    })
    # Context with file and model
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"*File:* `{filename}`"},
            {"type": "mrkdwn", "text": f"*Model:* `{model}`"}
        ]
    })
    blocks.append({"type": "divider"})

    if items:
        # Sort by occurrences desc, then last_seen desc
        items = sorted(items, key=lambda it: (-int(it.get("occurrences", 0)), it.get("last_seen", "")))
        for idx, it in enumerate(items, start=1):
            occ = int(it.get("occurrences", 0))
            last = it.get("last_seen", "")
            name = it.get('category') or it.get('issue') or ''
            samples = it.get('samples', [])
            emoji = _severity_emoji(occ)

            # Format timestamp for Slack display
            if last:
                try:
                    dt = datetime.fromisoformat(last.replace('Z', '+00:00'))
                    formatted_time = dt.strftime('%b %d, %Y %I:%M %p')
                except Exception:
                    formatted_time = last
            else:
                formatted_time = 'Unknown'

            # Main category section
            blocks.append({
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*{emoji} Category {idx}:*\n{name}"},
                    {"type": "mrkdwn", "text": f"*Occurrences:*\n{occ}\n*Last:*\n{formatted_time}"}
                ]
            })

            # Add samples if available
            if samples:
                sample_text = "\n".join([f"• {sample}" for sample in samples[:3]])
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Sample Messages:*\n{sample_text}"}
                })
            if idx < len(items):
                blocks.append({"type": "divider"})
    else:
        # Fallback: show the text as-is (converted to Slack md)
        text = slackify_summary(summary)
        # Slack section text limit ~3000 chars; split
        while text:
            part = text[:2900]
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": part}})
            text = text[2900:]

    return {"blocks": blocks}


def slack_post_message(token: str, channel: str, payload: dict) -> dict:
    url = f"{SLACK_API_BASE}/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    # Ensure channel is included at top-level
    body = dict(payload)
    body["channel"] = channel
    return http_post_json(url, body, headers, timeout=TIMEOUT_SECONDS)


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Summarize WhatsApp log files using OpenAI.")
    parser.add_argument("files", nargs="*", help="Paths to .txt log files to summarize (optional - if not provided, auto-discovers most recent files)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"OpenAI model (default: {DEFAULT_MODEL})")
    parser.add_argument("--insecure", action="store_true", help="Skip TLS verification (NOT recommended; use only if necessary)")
    parser.add_argument("--ca-bundle", dest="ca_bundle", help="Path to a custom CA bundle (PEM)")
    parser.add_argument("--slack", action="store_true", help="Also post each summary to Slack")
    parser.add_argument("--slack-channel", dest="slack_channel", default=SLACK_DEFAULT_CHANNEL, help="Slack channel ID (default from env SLACK_CHANNEL or C09BK6AGAF7)")
    parser.add_argument("--log-dir", dest="log_dir", default="message-logs", help="Directory containing log files (default: message-logs)")
    args = parser.parse_args(argv)

    # Apply CLI SSL options globally for urlopen context builder
    global CLI_INSECURE, CLI_CA_BUNDLE
    CLI_INSECURE = args.insecure
    CLI_CA_BUNDLE = args.ca_bundle


    api_key = None  # Lazy-load only if we actually need to summarize

    slack_token = os.getenv("SLACK_TOKEN", "nill")
    print(slack_token)

    if args.slack and not slack_token:
        print("Warning: --slack provided but SLACK_BOT_TOKEN is not set; skipping Slack posting.", file=sys.stderr)

    # Determine files to process
    if args.files:
        # Use explicitly provided files
        files_to_process = args.files
        print(f"Processing {len(files_to_process)} explicitly provided files...")
    else:
        # Auto-discover most recent files for each target group
        print(f"Auto-discovering most recent log files in '{args.log_dir}'...")
        recent_files = find_most_recent_log_files(args.log_dir)

        if not recent_files:
            print(f"No log files found for target groups in '{args.log_dir}'")
            print(f"Target groups: {', '.join(TARGET_GROUP_NAMES)}")
            return 1

        files_to_process = list(recent_files.values())
        print(f"Found {len(recent_files)} target groups with recent log files:")
        for group, path in recent_files.items():
            print(f"  - {group}: {os.path.basename(path)}")

    exit_code = 0
    for path in files_to_process:
        print(f"Processing: {path}")
        try:
            # If a summary file is provided, don't re-summarize; just read and (optionally) post
            if is_summary_file(path):
                summary = read_text(path)
                out_path = path
            else:
                if api_key is None:
                    api_key = load_api_key()
                summary = summarize_file(path, api_key=api_key, model=args.model)
                out_path = derive_output_path(path)
                write_summary(out_path, path, summary, args.model)
                print(f"✓ Wrote summary: {out_path}")

            # Optionally post to Slack
            if args.slack and slack_token:
                filename = os.path.basename(path)
                payload = build_slack_blocks_for_summary(filename, args.model, summary)
                print(args.slack_channel)
                try:
                    resp = slack_post_message(slack_token, args.slack_channel, payload)
                    print(resp)
                    if not resp.get("ok"):
                        print(f"Warning: Slack API error: {resp}", file=sys.stderr)
                    else:
                        ts = resp.get("ts")
                        print(f"✓ Posted to Slack channel {args.slack_channel} (ts={ts})")
                except Exception as e:
                    print(f"Warning: failed to post to Slack: {e}", file=sys.stderr)

            print()
        except Exception as e:
            print(f"✗ Failed to process {path}: {e}", file=sys.stderr)
            exit_code = 2
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

