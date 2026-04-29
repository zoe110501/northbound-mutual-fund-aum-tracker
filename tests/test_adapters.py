from northbound_fund_aum_tracker.adapters import adapter_urls_for_manager
from northbound_fund_aum_tracker.models import FundRecord


def test_jpmorgan_adapter_returns_known_factsheet_urls():
    targets = [
        FundRecord(
            fund_code="968000.OF",
            name="摩根亚洲总收益债券基金",
            english_name="JPMorgan Asian Total Return Bond Fund",
            management_company="摩根基金(亚洲)",
            source_kind="global_fund",
        )
    ]
    urls = adapter_urls_for_manager("摩根基金(亚洲)", targets)
    assert "https://am.jpmorgan.com/content/dam/jpm-am-aem/asiapacific/hk/en/literature/fact-sheet/jpmorgan_asian_total_return_bond_e.pdf" in urls


def test_adapter_urls_are_deduplicated():
    targets = [
        FundRecord("1", "a", "JPMorgan Asian Total Return Bond Fund", "摩根基金(亚洲)", "global_fund"),
        FundRecord("2", "b", "JPMorgan Asian Total Return Bond Fund", "摩根基金(亚洲)", "mainland_share_class"),
    ]
    urls = adapter_urls_for_manager("摩根基金(亚洲)", targets)
    assert len(urls) == len(set(urls))


def test_jpmorgan_adapter_returns_pacific_technology_factsheet_url():
    targets = [
        FundRecord("968041.OF", "摩根太平洋科技基金", "JPMorgan Pacific Technology Fund", "摩根基金(亚洲)", "global_fund")
    ]
    urls = adapter_urls_for_manager("摩根基金(亚洲)", targets)
    assert "jpmorgan_pacific_tech_e.pdf" in urls[0]
