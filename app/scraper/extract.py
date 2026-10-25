"""Turn a fetched Page into program fields.

Plugging in your own model
--------------------------
Set the PROGRAM_EXTRACTOR environment variable to "package.module:name", where
`name` is one of:

  * a class with an `extract(page)` method (instantiated once, no arguments),
  * an object with an `extract(page)` method,
  * a plain function `extract(page)`.

`extract` receives an `app.scraper.fetch.Page` (url, title, headings, text,
meta, json_ld, html) and returns a dict with any of the keys in FIELDS. It may
be sync or async; sync extractors run in a worker thread so slow local models
don't block the app. Values can be loose strings - "Dec 1, 2026" and
"$45,000/yr" are normalized here - and missing keys are fine.

Without PROGRAM_EXTRACTOR set, the rules-based extractor below is used.
"""

import asyncio
import datetime
import importlib
import inspect
import logging
import os
import re
from typing import Any

from app import storage
from app.scraper.fetch import Page

FIELDS = (
    "university_name",
    "program_name",
    "department",
    "degree_type",
    "research_area",
    "application_deadline",
    "tuition_in_state",
    "tuition_out_of_state",
    "description",
)

# ---------------------------------------------------------------- normalizing

_MONTHS = {
    m: i
    for i, names in enumerate(
        [("jan", "january"), ("feb", "february"), ("mar", "march"), ("apr", "april"),
         ("may",), ("jun", "june"), ("jul", "july"), ("aug", "august"),
         ("sep", "sept", "september"), ("oct", "october"), ("nov", "november"),
         ("dec", "december")],
        start=1,
    )
    for m in names
}
_MONTH_RE = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_DATE_PATTERNS = [
    # 2026-12-01
    (re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b"), lambda m: (int(m[1]), int(m[2]), int(m[3]))),
    # December 1, 2026 / Dec. 1 / Dec 1st
    (re.compile(_MONTH_RE + r"\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?\b", re.I),
     lambda m: (int(m[3]) if m[3] else None, _MONTHS[m[1].lower()], int(m[2]))),
    # 1 December 2026
    (re.compile(r"\b(\d{1,2})\s+" + _MONTH_RE + r"\.?(?:,?\s+(\d{4}))?\b", re.I),
     lambda m: (int(m[3]) if m[3] else None, _MONTHS[m[2].lower()], int(m[1]))),
    # 12/01/2026 (US order)
    (re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"), lambda m: (int(m[3]), int(m[1]), int(m[2]))),
]


def find_dates(text: str, today: datetime.date | None = None) -> list[datetime.date]:
    """All dates in `text`, in order. Dates without a year get their next occurrence."""
    today = today or datetime.date.today()
    found: list[tuple[int, datetime.date]] = []
    for pattern, parts in _DATE_PATTERNS:
        for m in pattern.finditer(text):
            year, month, day = parts(m)
            try:
                d = datetime.date(year or today.year, month, day)
                if year is None and d < today:
                    d = d.replace(year=today.year + 1)
            except ValueError:
                continue
            found.append((m.start(), d))
    return [d for _, d in sorted(found, key=lambda x: x[0])]


def parse_date(value: Any) -> datetime.date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    dates = find_dates(str(value))
    return dates[0] if dates else None


_MONEY_RE = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{2})?(\s?[kK]\b)?")


def find_amounts(text: str) -> list[int]:
    out = []
    for m in _MONEY_RE.finditer(text):
        n = int(m[1].replace(",", ""))
        if m[2]:
            n *= 1000
        out.append(n)
    return out


def parse_money(value: Any) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value)
    amounts = find_amounts(s if "$" in s else "$" + s.strip())
    return amounts[0] if amounts else None


def normalize(raw: dict | None) -> dict:
    """Coerce an extractor's output into the types the Program model expects."""
    raw = raw or {}
    out: dict[str, Any] = {}
    for key in FIELDS:
        value = raw.get(key)
        if key == "application_deadline":
            out[key] = parse_date(value)
        elif key in ("tuition_in_state", "tuition_out_of_state"):
            out[key] = parse_money(value)
        else:
            out[key] = " ".join(str(value).split()) if value not in (None, "") else ""
    return out


# ------------------------------------------------------- rules-based fallback

_DEGREE_RE = re.compile(r"\b(Ph\.?\s?D|M\.?\s?S|M\.?\s?A|M\.?\s?Eng|M\.?\s?Phil|Ed\.?\s?D|D\.?\s?Phil)\b\.?")
_DEGREE_NAMES = {"phd": "PhD", "ms": "MS", "ma": "MA", "meng": "MEng", "mphil": "MPhil", "edd": "EdD", "dphil": "DPhil"}
_SCHOOL_RE = re.compile(r"\b(University|College|Institute|School)\b")
_DEPT_RE = re.compile(r"\bDepartment of ([A-Z][\w&,' -]{2,60}?)(?=[.,;:\n|]| at | - |$)")


def _lines_near(lines: list[str], keyword: re.Pattern, after: int = 2) -> list[str]:
    hits = []
    for i, line in enumerate(lines):
        if keyword.search(line):
            hits.append(" ".join(lines[i : i + 1 + after]))
    return hits


class RuleExtractor:
    """Heuristics over page metadata and text. A placeholder until a real model is plugged in."""

    def extract(self, page: Page) -> dict:
        lines = page.text.splitlines()
        title_parts = [p.strip() for p in re.split(r"\s+[|\-–—]\s+", page.title) if p.strip()]
        result: dict[str, Any] = {}

        result["university_name"] = page.meta.get("og:site_name") or next(
            (p for p in title_parts if _SCHOOL_RE.search(p)), ""
        )
        for item in page.json_ld:
            if isinstance(item, dict) and item.get("@type") in ("CollegeOrUniversity", "EducationalOrganization"):
                result["university_name"] = result["university_name"] or item.get("name", "")

        result["program_name"] = (page.headings[0] if page.headings else "") or (
            title_parts[0] if title_parts else ""
        )

        degrees = [_DEGREE_NAMES.get(re.sub(r"[^a-z]", "", d.lower()), d) for d in _DEGREE_RE.findall(
            " ".join([result["program_name"], page.title, page.text[:5000]])
        )]
        if degrees:
            result["degree_type"] = max(set(degrees), key=degrees.count)

        dept = _DEPT_RE.search(page.text)
        if dept:
            result["department"] = dept[1].strip()

        for chunk in _lines_near(lines, re.compile(r"deadline", re.I)):
            dates = find_dates(chunk)
            if dates:
                result["application_deadline"] = dates[0]
                break

        # Classify each tuition line on its own; an amount may sit on the next line (table cells).
        unlabelled = None
        for i, line in enumerate(lines):
            if not re.search(r"tuition|cost of attendance", line, re.I):
                continue
            amounts, label_text = find_amounts(line), line
            if not amounts and i + 1 < len(lines):
                amounts, label_text = find_amounts(lines[i + 1]), line + " " + lines[i + 1]
            if not amounts:
                continue
            if re.search(r"out[- ]of[- ]state|non[- ]?resident|international", label_text, re.I):
                result.setdefault("tuition_out_of_state", amounts[0])
            elif re.search(r"\bin[- ]state\b|\bresident\b", label_text, re.I):
                result.setdefault("tuition_in_state", amounts[0])
            elif unlabelled is None:
                unlabelled = amounts[0]
        if unlabelled is not None:
            result.setdefault("tuition_out_of_state", unlabelled)

        result["description"] = page.meta.get("description") or page.meta.get("og:description", "")
        return result


# ------------------------------------------------------------------- loading

_extractor = None
_extractor_name = "RuleExtractor"


def get_extractor():
    global _extractor, _extractor_name
    if _extractor is None:
        spec = os.getenv("PROGRAM_EXTRACTOR", "").strip()
        if spec:
            module_name, _, attr = spec.partition(":")
            obj = getattr(importlib.import_module(module_name), attr or "extract")
            _extractor = obj() if inspect.isclass(obj) else obj
            _extractor_name = spec
            logging.info("Using program extractor %s", spec)
        else:
            _extractor = RuleExtractor()
    return _extractor


async def extract_program(page: Page) -> dict:
    """Run the configured extractor on `page`, store the page in the data folder, and return normalized fields."""
    extractor = get_extractor()
    fn = extractor.extract if hasattr(extractor, "extract") else extractor
    if inspect.iscoroutinefunction(fn):
        raw = await fn(page)
    else:
        raw = await asyncio.to_thread(fn, page)
        if inspect.isawaitable(raw):
            raw = await raw
    fields = normalize(raw)
    storage.save_page(page, fields, _extractor_name)
    return fields
