from django.db import models


class Inspection(models.Model):
    aid_code = models.CharField("航标编号", max_length=40)
    measured_cd = models.FloatField("实测光强")
    required_cd = models.FloatField("要求光强")
    bearing_error_deg = models.FloatField("方位偏差")
    verdict = models.CharField("结论", max_length=20)
    note = models.CharField("说明", max_length=200)
    created_by = models.CharField("登记人", max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]


class Comparison(models.Model):
    """同一座灯标更换灯器前后的两次实测对读。

    两条引用必须编号相同；坎德拉差额与是否降级由服务端计算后落库，
    页面只渲染已存好的值，浏览器端不做减法。
    """

    aid_code = models.CharField("航标编号", max_length=40)
    before = models.ForeignKey(
        Inspection, on_delete=models.PROTECT, related_name="comparisons_before"
    )
    after = models.ForeignKey(
        Inspection, on_delete=models.PROTECT, related_name="comparisons_after"
    )
    cd_delta = models.FloatField("光强差额")
    downgraded = models.BooleanField("是否由合格降为不合格", default=False)
    created_by = models.CharField("建单人", max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
