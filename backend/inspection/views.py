from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from inspection.models import Comparison, Inspection
from inspection.rules import judge


def _can_write(user) -> bool:
    return user.groups.filter(name="inspector").exists()


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
    rows = Inspection.objects.all()
    return render(request, "list.html", {"rows": rows, "can_write": _can_write(request.user)})


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
def comparison_list_view(request):
    rows = Comparison.objects.select_related("before", "after").all()
    return render(request, "comparison_list.html", {"rows": rows})


@login_required
def comparison_detail_view(request, pk):
    comparison = get_object_or_404(
        Comparison.objects.select_related("before", "after"), pk=pk
    )
    return render(request, "comparison_detail.html", {"comparison": comparison})


@login_required
@require_http_methods(["POST"])
def comparison_create_view(request):
    # 只有持灯账号能挑选两条记录生成对读；只读账号直接拒绝。
    if not _can_write(request.user):
        return HttpResponseForbidden("仅巡检员可生成灯质对读")
    raw_ids = request.POST.getlist("pick")
    try:
        ids = [int(v) for v in raw_ids]
    except ValueError:
        messages.error(request, "请勾选两条巡检记录")
        return redirect("list")
    if len(ids) != 2 or len(set(ids)) != 2:
        messages.error(request, "对读需要勾选同一座灯标的两条不同记录")
        return redirect("list")
    records = list(
        Inspection.objects.filter(id__in=ids).order_by("created_at", "id")
    )
    if len(records) != 2:
        messages.error(request, "所选巡检记录不存在")
        return redirect("list")
    before, after = records
    if before.aid_code != after.aid_code:
        messages.error(request, "两条记录必须属于同一座灯标（编号相同）")
        return redirect("list")

    # 差额与掉级结论一律由服务端计算并落库，模板只负责展示。
    cd_diff = after.measured_cd - before.measured_cd
    dropped_to_failed = before.verdict == "合格" and after.verdict == "不合格"
    comparison = Comparison.objects.create(
        aid_code=before.aid_code,
        before=before,
        after=after,
        cd_diff=cd_diff,
        dropped_to_failed=dropped_to_failed,
        created_by=request.user.username,
    )
    return redirect("comparison_detail", pk=comparison.pk)
