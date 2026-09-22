from collections import Counter

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from inspection.models import Comparison, Inspection
from inspection.rules import judge


def _can_write(user) -> bool:
    return user.groups.filter(name="inspector").exists()


def _chronological_pair(first: Inspection, second: Inspection) -> tuple[Inspection, Inspection]:
    """按登记先后排：id 小的是换灯器前（before），id 大的是换灯器后（after）。"""
    if first.id <= second.id:
        return first, second
    return second, first


def health(_request):
    from django.http import JsonResponse

    return JsonResponse({"status": "ok", "service": "nav-aid-inspection"})


@require_http_methods(["GET", "POST"])
def login_view(request):
    from django.contrib.auth import authenticate, login

    error = ""
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username", "").strip(),
            password=request.POST.get("password", ""),
        )
        if user is None:
            error = "用户名或密码错误"
        else:
            login(request, user)
            return redirect("list")
    return render(request, "login.html", {"error": error})


def logout_view(request):
    from django.contrib.auth import logout

    logout(request)
    return redirect("login")


@login_required
def list_view(request):
    rows = list(Inspection.objects.all())
    counts = Counter(row.aid_code for row in rows)
    pairable = {code for code, n in counts.items() if n >= 2}
    # 每个编号取最新一张已生成的对读单（Comparison 默认按 -id 排序）。
    latest_comparison: dict[str, int] = {}
    for comp in Comparison.objects.all():
        latest_comparison.setdefault(comp.aid_code, comp.id)
    for row in rows:
        row.comparison_pk = latest_comparison.get(row.aid_code)
        row.pairable = row.aid_code in pairable
    return render(
        request,
        "list.html",
        {
            "rows": rows,
            "can_write": _can_write(request.user),
        },
    )


@login_required
def detail_view(request, pk):
    row = get_object_or_404(Inspection, pk=pk)
    return render(request, "detail.html", {"row": row})


@login_required
@require_http_methods(["GET", "POST"])
def create_view(request):
    if not _can_write(request.user):
        return HttpResponseForbidden("仅巡检员可登记灯光巡检")
    error = ""
    if request.method == "POST":
        try:
            measured = float(request.POST["measured_cd"])
            required = float(request.POST["required_cd"])
            bearing = float(request.POST["bearing_error_deg"])
            code = request.POST["aid_code"].strip()
            if not code:
                raise ValueError("empty")
        except (KeyError, ValueError):
            error = "请填编号和三项数值"
        else:
            verdict, note = judge(measured, required, bearing)
            row = Inspection.objects.create(
                aid_code=code,
                measured_cd=measured,
                required_cd=required,
                bearing_error_deg=bearing,
                verdict=verdict,
                note=note,
                created_by=request.user.username,
            )
            return redirect("detail", pk=row.pk)
    return render(request, "form.html", {"error": error})


@login_required
@require_http_methods(["GET", "POST"])
def comparison_create_view(request):
    # 只有持灯（巡检员）账号能挑选两条记录并生成对读；只读账号到此一律拒绝。
    if not _can_write(request.user):
        return HttpResponseForbidden("仅巡检员可生成灯质对读")

    error = ""
    if request.method == "POST":
        raw_ids = [i for i in request.POST.getlist("records") if i]
        if len(raw_ids) != 2:
            raw_ids = [request.POST.get("before_id"), request.POST.get("after_id")]
        try:
            ids = [int(i) for i in raw_ids if i]
            if len(ids) != 2:
                raise ValueError
        except (TypeError, ValueError):
            error = "请勾选同一编号下的两条记录"
        else:
            first = get_object_or_404(Inspection, pk=ids[0])
            second = get_object_or_404(Inspection, pk=ids[1])
            if first.aid_code != second.aid_code:
                error = "两条记录必须航标编号相同"
            else:
                before, after = _chronological_pair(first, second)
                # 差额与降级判定只在服务端算，浏览器拿到的是落库后的结果。
                cd_delta = after.measured_cd - before.measured_cd
                downgraded = before.verdict == "合格" and after.verdict != "合格"
                comp = Comparison.objects.create(
                    aid_code=before.aid_code,
                    before=before,
                    after=after,
                    cd_delta=cd_delta,
                    downgraded=downgraded,
                    created_by=request.user.username,
                )
                return redirect("comparison", pk=comp.pk)

    # GET 或校验失败：列出每个可配对编号最近的两条，供挑选。
    candidates = []
    for code in sorted(
        Inspection.objects.values_list("aid_code", flat=True).distinct()
    ):
        latest = list(Inspection.objects.filter(aid_code=code).order_by("-id")[:2])
        if len(latest) == 2:
            after, before = latest[0], latest[1]
            candidates.append({"code": code, "before": before, "after": after})
    return render(
        request,
        "comparison_form.html",
        {"candidates": candidates, "error": error},
    )


@login_required
def comparison_list_view(request):
    comparisons = Comparison.objects.select_related("before", "after").all()
    return render(
        request,
        "comparison_list.html",
        {"comparisons": comparisons, "can_write": _can_write(request.user)},
    )


@login_required
def comparison_view(request, pk):
    comp = get_object_or_404(
        Comparison.objects.select_related("before", "after"), pk=pk
    )
    return render(request, "comparison_detail.html", {"comp": comp})
