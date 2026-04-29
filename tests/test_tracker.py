from northbound_fund_aum_tracker.models import FundRecord
from northbound_fund_aum_tracker.tracker import share_class_term_groups


def test_share_class_term_groups_from_chinese_share_name():
    record = FundRecord(
        fund_code="968003.OF",
        name="摩根亚洲总收益债券PRC-USD累积",
        english_name="JPMorgan Asian Total Return Bond Fund",
        management_company="摩根基金(亚洲)",
        source_kind="mainland_share_class",
    )
    groups = share_class_term_groups(record)
    assert ["PRC"] in groups
    assert ["USD"] in groups
    assert ["acc", "accumulation", "accumulative", "累积", "累計", "累计"] in groups

