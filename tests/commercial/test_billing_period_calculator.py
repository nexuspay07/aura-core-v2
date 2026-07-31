from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
import pytest
from app.commercial.billing import *
def sub(cycle="monthly",start=datetime(2026,1,31,tzinfo=timezone.utc)):return SimpleNamespace(billing_cycle=cycle,starts_at=start)
def test_value_validation_and_immutable():
 p=BillingPeriod(datetime(2026,1,1,tzinfo=timezone.utc),datetime(2026,2,1,tzinfo=timezone.utc),"monthly",1);assert p==p
 with pytest.raises(Exception):p.anchor_day=2
 with pytest.raises(InvalidBillingPeriodError):BillingPeriod(datetime(2026,1,1),datetime(2026,2,1,tzinfo=timezone.utc),"monthly",1)
@pytest.mark.parametrize("month,day,end",[(2,15,28),(3,1,31),(2,15,29)])
def test_monthly_clamp(month,day,end):
 p=BillingPeriodCalculator.calculate_current_period(sub(start=datetime(2025 if end==28 else 2024,1,31,tzinfo=timezone.utc)),datetime(2025 if end==28 else 2024,month,day,tzinfo=timezone.utc));assert p.anchor_day==31 and p.period_end.tzinfo==timezone.utc
def test_annual_and_boundaries():
 p=BillingPeriodCalculator.calculate_current_period(sub("annual",datetime(2024,2,29,tzinfo=timezone.utc)),datetime(2025,3,1,tzinfo=timezone.utc));assert p.period_start.month==2
 n=BillingPeriodCalculator.calculate_next_period(sub(),datetime(2026,2,15,tzinfo=timezone.utc));assert n.period_start>=datetime(2026,2,28,tzinfo=timezone.utc)
def test_errors():
 with pytest.raises(MissingBillingAnchorError):BillingPeriodCalculator.calculate_current_period(SimpleNamespace(billing_cycle="monthly",starts_at=None),datetime.now(timezone.utc))
 with pytest.raises(UnsupportedBillingCycleError):BillingPeriodCalculator.calculate_current_period(sub("custom"),datetime.now(timezone.utc))
@pytest.mark.parametrize("anchor",[28,29,30,31])
def test_all_monthly_anchors_clamp_and_preserve(anchor):
 p=BillingPeriodCalculator.calculate_current_period(sub(start=datetime(2025,1,anchor,tzinfo=timezone.utc)),datetime(2025,2,15,tzinfo=timezone.utc));assert p.period_start==datetime(2025,1,anchor,tzinfo=timezone.utc) and p.period_end==datetime(2025,2,28,tzinfo=timezone.utc) and p.anchor_day==anchor
def test_monthly_boundaries_gap_overlap_and_return_to_31():
 s=sub(); feb=BillingPeriodCalculator.calculate_current_period(s,datetime(2025,2,15,tzinfo=timezone.utc));mar=BillingPeriodCalculator.calculate_next_period(s,datetime(2025,2,15,tzinfo=timezone.utc));assert feb.period_end==mar.period_start==datetime(2025,2,28,tzinfo=timezone.utc) and mar.period_end==datetime(2025,3,31,tzinfo=timezone.utc)
def test_value_object_boundaries_timezone_and_anchor_errors():
 with pytest.raises(InvalidBillingPeriodError):BillingPeriod(NOW:=datetime(2026,1,1,tzinfo=timezone.utc),NOW,"monthly",1)
 with pytest.raises(InvalidBillingPeriodError):BillingPeriod(NOW,datetime(2025,1,1,tzinfo=timezone.utc),"monthly",1)
 with pytest.raises(InvalidBillingPeriodError):BillingPeriod(NOW,datetime(2026,2,1,tzinfo=timezone.utc),"monthly",32)
 p=BillingPeriod(datetime(2026,1,1,tzinfo=__import__('datetime').timezone(timedelta(hours=2))),datetime(2026,2,1,tzinfo=timezone.utc),"monthly",1);assert p.period_start.tzinfo==timezone.utc
