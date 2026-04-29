from northbound_fund_aum_tracker.fetch import candidate_links_from_html


def test_candidate_links_prioritize_latest_financial_reports():
    html = """
    <a href="/funds/detail.html">Fund details</a>
    <a href="/docs/interim-report-2025.pdf">Interim Report 2025</a>
    <a href="/docs/annual-report-2024.pdf">Annual Report 2024</a>
    <a href="/docs/factsheet.pdf">Monthly Factsheet</a>
    """
    links = candidate_links_from_html(html, "https://manager.example.com/en/", limit=4)
    assert links[0] == "https://manager.example.com/docs/interim-report-2025.pdf"
    assert links[1] == "https://manager.example.com/docs/annual-report-2024.pdf"
    assert "https://manager.example.com/funds/detail.html" in links
