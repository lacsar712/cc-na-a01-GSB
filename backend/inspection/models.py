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
    """同一座灯标更换灯器前后的两次实测对读单。

    before 是先测的一条，after 是后测的一条；坎德拉差额与是否由合格掉成
    不合格都在服务端算好落库，页面只读，不交给浏览器计算。
    """

    aid_code = models.CharField("航标编号", max_length=40)
    before = models.ForeignKey(
        Inspection, on_delete=models.PROTECT, related_name="comparisons_before"
    )
    after = models.ForeignKey(
        Inspection, on_delete=models.PROTECT, related_name="comparisons_after"
    )
    cd_diff = models.FloatField("坎德拉差额")
    dropped_to_failed = models.BooleanField("由合格掉为不合格", default=False)
    created_by = models.CharField("对读生成人", max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    @property
    def dimmed(self) -> bool:
        return self.cd_diff < 0

    @property
    def cd_diff_magnitude(self) -> float:
        return abs(self.cd_diff)
