from __future__ import annotations

import io
import re
from html import unescape
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader


LINK_KEYWORDS = (
    "fund",
    "factsheet",
    "monthly",
    "report",
    "document",
    "nav",
    "aum",
    "asset",
    "\u57fa\u91d1",
    "\u6708\u62a5",
    "\u6708\u5831",
    "\u8d44\u4ea7",
    "\u8cc7\u7522",
    "\u51c0\u503c",
    "\u6de8\u503c",
    "\u4e92\u8ba4",
    "\u4e92\u8a8d",
)

REPORT_KEYWORDS = (
    "annual report",
    "interim report",
    "semi-annual",
    "semi annual",
    "financial report",
    "financial statements",
    "audited report",
    "unaudited report",
    "\u5e74\u62a5",
    "\u5e74\u5831",
    "\u4e2d\u671f\u62a5\u544a",
    "\u4e2d\u671f\u5831\u544a",
    "\u534a\u5e74\u5ea6",
    "\u8d22\u52a1\u62a5\u8868",
    "\u8ca1\u52d9\u5831\u8868",
    "\u5ba1\u8ba1",
    "\u5be9\u8a08",
)


REQUEST_TIMEOUT_SECONDS = 15


def fetch_text(session: requests.Session, url: str) -> tuple[str, str]:
    response = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS, headers={"User-Agent": "northbound-aum-tracker/0.1"})
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    if "pdf" in content_type or url.lower().endswith(".pdf"):
        return extract_pdf_text(response.content), url
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return unescape(soup.get_text(" ", strip=True)), url


def discover_candidate_links(session: requests.Session, seed_url: str, limit: int) -> list[str]:
    response = session.get(seed_url, timeout=REQUEST_TIMEOUT_SECONDS, headers={"User-Agent": "northbound-aum-tracker/0.1"})
    response.raise_for_status()
    return candidate_links_from_html(response.text, seed_url, limit)


def candidate_links_from_html(html: str, seed_url: str, limit: int) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    seed_host = urlparse(seed_url).netloc
    candidates: list[tuple[int, str]] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a"):
        href = anchor.get("href")
        if not href:
            continue
        absolute = urljoin(seed_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"} or parsed.netloc != seed_host:
            continue
        haystack = f"{anchor.get_text(' ', strip=True)} {href}".lower()
        if not any(keyword.lower() in haystack for keyword in LINK_KEYWORDS):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        candidates.append((_link_score(haystack, absolute), absolute))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    return [url for _, url in candidates[:limit]]


def _link_score(haystack: str, url: str) -> int:
    score = 0
    lower_url = url.lower()
    if lower_url.endswith(".pdf"):
        score += 20
    if any(keyword.lower() in haystack for keyword in REPORT_KEYWORDS):
        score += 100
    elif "fund document" in haystack or "mrf" in haystack or "mutual recognition" in haystack:
        score += 80
    elif "fund explorer" in haystack or "retail fund" in haystack:
        score += 50
    elif "factsheet" in haystack or "monthly" in haystack or "\u6708\u62a5" in haystack or "\u6708\u5831" in haystack:
        score += 30
    if "about-us" in haystack or "leadership" in haystack:
        score -= 20
    for year in re.findall(r"20\d{2}", haystack):
        score += int(year) - 2000
    return score


def extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)
