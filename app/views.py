import json
from functools import wraps
from urllib.parse import urlencode

from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Genealogy, GenealogyUser, Member, User
from .services import (
    build_descendant_tree,
    fetch_ancestors,
    fetch_descendants,
    shortest_relationship_path,
)


def _json_payload(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("invalid_json") from exc


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _accessible_genealogy_ids(user):
    return list(
        GenealogyUser.objects.filter(user=user).values_list("genealogy_id", flat=True)
    )


def _genealogy_role(user, genealogy_id):
    return (
        GenealogyUser.objects.filter(user=user, genealogy_id=genealogy_id)
        .values_list("role", flat=True)
        .first()
    )


def _can_write_genealogy(user, genealogy_id):
    role = _genealogy_role(user, genealogy_id)
    return role in {GenealogyUser.ROLE_OWNER, GenealogyUser.ROLE_EDITOR}


def _is_member_accessible(user, member):
    return GenealogyUser.objects.filter(
        user=user, genealogy_id=member.genealogy_id
    ).exists()


def _build_dashboard_stats(genealogy_id):
    total = Member.objects.filter(genealogy_id=genealogy_id).count()
    male = Member.objects.filter(genealogy_id=genealogy_id, gender="M").count()
    female = Member.objects.filter(genealogy_id=genealogy_id, gender="F").count()
    male_ratio = round((male / total) * 100, 2) if total else 0.0
    female_ratio = round((female / total) * 100, 2) if total else 0.0
    return {
        "total_members": total,
        "male_members": male,
        "female_members": female,
        "male_ratio": male_ratio,
        "female_ratio": female_ratio,
    }


def api_login_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "authentication_required"}, status=401)
        return view_func(request, *args, **kwargs)

    return wrapped


@csrf_exempt
@require_http_methods(["POST"])
def register_view(request):
    try:
        payload = _json_payload(request)
    except ValueError:
        return JsonResponse({"error": "invalid_json"}, status=400)

    username = payload.get("username", "").strip()
    password = payload.get("password", "").strip()
    email = payload.get("email", "").strip()
    if not username or not password or not email:
        return JsonResponse(
            {"error": "username, password, email are required"}, status=400
        )

    try:
        user = User.objects.create_user(
            username=username, password=password, email=email
        )
    except IntegrityError:
        return JsonResponse({"error": "username_or_email_already_exists"}, status=409)

    return JsonResponse(
        {"message": "register_success", "user": {"user_id": user.user_id, "username": user.username}},
        status=201,
    )


@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    try:
        payload = _json_payload(request)
    except ValueError:
        return JsonResponse({"error": "invalid_json"}, status=400)

    username = payload.get("username", "").strip()
    password = payload.get("password", "").strip()
    user = authenticate(request, username=username, password=password)
    if not user:
        return JsonResponse({"error": "invalid_credentials"}, status=401)

    login(request, user)
    return JsonResponse(
        {
            "message": "login_success",
            "user": {"user_id": user.user_id, "username": user.username},
        }
    )


@csrf_exempt
@api_login_required
@require_http_methods(["GET", "POST"])
def genealogies_view(request):
    if request.method == "GET":
        links = (
            GenealogyUser.objects.filter(user=request.user)
            .select_related("genealogy")
            .order_by("genealogy_id")
        )
        items = [
            {
                "genealogy_id": link.genealogy.genealogy_id,
                "title": link.genealogy.title,
                "surname": link.genealogy.surname,
                "created_at": link.genealogy.created_at,
                "role": link.role,
            }
            for link in links
        ]
        return JsonResponse({"items": items})

    try:
        payload = _json_payload(request)
    except ValueError:
        return JsonResponse({"error": "invalid_json"}, status=400)

    title = payload.get("title", "").strip()
    surname = payload.get("surname", "").strip()
    if not title or not surname:
        return JsonResponse({"error": "title and surname are required"}, status=400)

    genealogy = Genealogy.objects.create(
        title=title, surname=surname, created_by=request.user
    )
    GenealogyUser.objects.create(
        user=request.user, genealogy=genealogy, role=GenealogyUser.ROLE_OWNER
    )
    return JsonResponse(
        {
            "message": "create_success",
            "genealogy": {
                "genealogy_id": genealogy.genealogy_id,
                "title": genealogy.title,
                "surname": genealogy.surname,
            },
        },
        status=201,
    )


@csrf_exempt
@api_login_required
@require_http_methods(["POST"])
def invite_user_view(request, genealogy_id):
    can_invite = GenealogyUser.objects.filter(
        user=request.user, genealogy_id=genealogy_id, role=GenealogyUser.ROLE_OWNER
    ).exists()
    if not can_invite:
        return JsonResponse({"error": "permission_denied"}, status=403)

    try:
        payload = _json_payload(request)
    except ValueError:
        return JsonResponse({"error": "invalid_json"}, status=400)

    username = payload.get("username", "").strip()
    role = payload.get("role", GenealogyUser.ROLE_EDITOR).strip()
    if role not in {
        GenealogyUser.ROLE_OWNER,
        GenealogyUser.ROLE_EDITOR,
        GenealogyUser.ROLE_VIEWER,
    }:
        return JsonResponse({"error": "invalid_role"}, status=400)

    target_user = User.objects.filter(username=username).first()
    if not target_user:
        return JsonResponse({"error": "user_not_found"}, status=404)

    link, _ = GenealogyUser.objects.update_or_create(
        user=target_user,
        genealogy_id=genealogy_id,
        defaults={"role": role},
    )
    return JsonResponse(
        {
            "message": "invite_success",
            "genealogy_id": link.genealogy_id,
            "user_id": link.user_id,
            "role": link.role,
        }
    )


@csrf_exempt
@api_login_required
@require_http_methods(["GET", "POST"])
def members_view(request):
    accessible_ids = _accessible_genealogy_ids(request.user)
    if not accessible_ids:
        return JsonResponse({"error": "no_accessible_genealogy"}, status=403)

    if request.method == "GET":
        genealogy_id = _to_int(request.GET.get("genealogy_id"))
        if genealogy_id is None:
            genealogy_id = accessible_ids[0]
        if genealogy_id not in accessible_ids:
            return JsonResponse({"error": "permission_denied"}, status=403)

        name_prefix = request.GET.get("name", "").strip()
        queryset = Member.objects.filter(genealogy_id=genealogy_id)
        if name_prefix:
            queryset = queryset.filter(name__startswith=name_prefix)

        members = list(
            queryset.values(
                "member_id",
                "genealogy_id",
                "name",
                "gender",
                "birth_year",
                "death_year",
                "biography",
            ).order_by("member_id")
        )
        return JsonResponse({"items": members})

    try:
        payload = _json_payload(request)
    except ValueError:
        return JsonResponse({"error": "invalid_json"}, status=400)

    genealogy_id = _to_int(payload.get("genealogy_id"))
    if genealogy_id is None or genealogy_id not in accessible_ids:
        return JsonResponse({"error": "permission_denied"}, status=403)
    if not _can_write_genealogy(request.user, genealogy_id):
        return JsonResponse({"error": "write_permission_denied"}, status=403)

    name = payload.get("name", "").strip()
    gender = payload.get("gender", "").strip()
    if not name or gender not in {"M", "F"}:
        return JsonResponse({"error": "name and valid gender are required"}, status=400)

    member = Member.objects.create(
        genealogy_id=genealogy_id,
        name=name,
        gender=gender,
        birth_year=_to_int(payload.get("birth_year")),
        death_year=_to_int(payload.get("death_year")),
        biography=payload.get("biography", ""),
    )
    return JsonResponse(
        {
            "message": "create_success",
            "member": {
                "member_id": member.member_id,
                "genealogy_id": member.genealogy_id,
                "name": member.name,
                "gender": member.gender,
            },
        },
        status=201,
    )


@csrf_exempt
@api_login_required
@require_http_methods(["GET", "PUT", "DELETE"])
def member_detail_view(request, member_id):
    member = Member.objects.filter(member_id=member_id).first()
    if not member:
        return JsonResponse({"error": "member_not_found"}, status=404)
    if not _is_member_accessible(request.user, member):
        return JsonResponse({"error": "permission_denied"}, status=403)

    if request.method == "GET":
        return JsonResponse(
            {
                "member_id": member.member_id,
                "genealogy_id": member.genealogy_id,
                "name": member.name,
                "gender": member.gender,
                "birth_year": member.birth_year,
                "death_year": member.death_year,
                "biography": member.biography,
            }
        )

    if request.method == "DELETE":
        if not _can_write_genealogy(request.user, member.genealogy_id):
            return JsonResponse({"error": "write_permission_denied"}, status=403)
        member.delete()
        return JsonResponse({"message": "delete_success"})

    if not _can_write_genealogy(request.user, member.genealogy_id):
        return JsonResponse({"error": "write_permission_denied"}, status=403)

    try:
        payload = _json_payload(request)
    except ValueError:
        return JsonResponse({"error": "invalid_json"}, status=400)

    if "name" in payload:
        member.name = str(payload.get("name")).strip()
    if "gender" in payload and payload["gender"] in {"M", "F"}:
        member.gender = payload["gender"]
    if "birth_year" in payload:
        member.birth_year = _to_int(payload.get("birth_year"))
    if "death_year" in payload:
        member.death_year = _to_int(payload.get("death_year"))
    if "biography" in payload:
        member.biography = str(payload.get("biography"))
    member.save()

    return JsonResponse({"message": "update_success"})


@api_login_required
@require_http_methods(["GET"])
def ancestors_view(request, member_id):
    member = Member.objects.filter(member_id=member_id).first()
    if not member:
        return JsonResponse({"error": "member_not_found"}, status=404)
    if not _is_member_accessible(request.user, member):
        return JsonResponse({"error": "permission_denied"}, status=403)

    return JsonResponse({"items": fetch_ancestors(member_id)})


@api_login_required
@require_http_methods(["GET"])
def descendants_view(request, member_id):
    member = Member.objects.filter(member_id=member_id).first()
    if not member:
        return JsonResponse({"error": "member_not_found"}, status=404)
    if not _is_member_accessible(request.user, member):
        return JsonResponse({"error": "permission_denied"}, status=403)

    return JsonResponse({"items": fetch_descendants(member_id)})


@api_login_required
@require_http_methods(["GET"])
def relationship_view(request):
    member_id_1 = _to_int(request.GET.get("id1"))
    member_id_2 = _to_int(request.GET.get("id2"))
    if not member_id_1 or not member_id_2:
        return JsonResponse({"error": "id1 and id2 are required"}, status=400)

    member1 = Member.objects.filter(member_id=member_id_1).first()
    member2 = Member.objects.filter(member_id=member_id_2).first()
    if not member1 or not member2:
        return JsonResponse({"error": "member_not_found"}, status=404)
    if not _is_member_accessible(request.user, member1) or not _is_member_accessible(
        request.user, member2
    ):
        return JsonResponse({"error": "permission_denied"}, status=403)

    path = shortest_relationship_path(member_id_1, member_id_2)
    return JsonResponse({"items": path})


@api_login_required
@require_http_methods(["GET"])
def tree_data_view(request, member_id):
    member = Member.objects.filter(member_id=member_id).first()
    if not member:
        return JsonResponse({"error": "member_not_found"}, status=404)
    if not _is_member_accessible(request.user, member):
        return JsonResponse({"error": "permission_denied"}, status=403)

    tree = build_descendant_tree(root_member_id=member_id)
    return JsonResponse(tree)


@api_login_required
@require_http_methods(["GET"])
def dashboard_view(request):
    accessible_ids = _accessible_genealogy_ids(request.user)
    if not accessible_ids:
        return JsonResponse({"error": "no_accessible_genealogy"}, status=403)

    genealogy_id = _to_int(request.GET.get("genealogy_id"))
    if genealogy_id is None:
        genealogy_id = accessible_ids[0]
    if genealogy_id not in accessible_ids:
        return JsonResponse({"error": "permission_denied"}, status=403)

    genealogy = Genealogy.objects.filter(genealogy_id=genealogy_id).first()
    if not genealogy:
        return JsonResponse({"error": "genealogy_not_found"}, status=404)

    data = _build_dashboard_stats(genealogy_id)
    return JsonResponse(
        {
            "genealogy_id": genealogy.genealogy_id,
            "title": genealogy.title,
            "surname": genealogy.surname,
            **data,
        }
    )


@require_http_methods(["GET", "POST"])
def login_page_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("/members-page")
        return render(request, "login.html", {"error": "用户名或密码错误"})
    return render(request, "login.html")


@login_required
@require_http_methods(["GET", "POST"])
def members_page_view(request):
    links = GenealogyUser.objects.filter(user=request.user).select_related("genealogy")
    link_by_genealogy = {link.genealogy_id: link for link in links}
    genealogies = [link.genealogy for link in links]
    accessible_ids = list(link_by_genealogy.keys())
    selected_genealogy_id = _to_int(request.GET.get("genealogy_id"))
    if selected_genealogy_id is None and accessible_ids:
        selected_genealogy_id = accessible_ids[0]
    if selected_genealogy_id is not None and selected_genealogy_id not in accessible_ids:
        return HttpResponseForbidden("无权限访问该族谱")

    status_message = ""
    error = ""

    if request.method == "POST":
        action = request.POST.get("action", "create_member").strip()
        posted_genealogy_id = _to_int(request.POST.get("genealogy_id"))
        if posted_genealogy_id is not None:
            selected_genealogy_id = posted_genealogy_id

        if action == "create_genealogy":
            title = request.POST.get("title", "").strip()
            surname = request.POST.get("surname", "").strip()
            if not title or not surname:
                error = "创建族谱失败：title 和 surname 不能为空。"
            else:
                genealogy = Genealogy.objects.create(
                    title=title, surname=surname, created_by=request.user
                )
                GenealogyUser.objects.create(
                    user=request.user,
                    genealogy=genealogy,
                    role=GenealogyUser.ROLE_OWNER,
                )
                selected_genealogy_id = genealogy.genealogy_id
                status_message = "族谱创建成功。"

        elif action == "invite_user":
            if selected_genealogy_id not in accessible_ids:
                error = "邀请失败：无权限访问该族谱。"
            else:
                role = _genealogy_role(request.user, selected_genealogy_id)
                if role != GenealogyUser.ROLE_OWNER:
                    error = "邀请失败：只有 owner 可以邀请协作者。"
                else:
                    username = request.POST.get("username", "").strip()
                    invite_role = request.POST.get(
                        "role", GenealogyUser.ROLE_EDITOR
                    ).strip()
                    if invite_role not in {
                        GenealogyUser.ROLE_OWNER,
                        GenealogyUser.ROLE_EDITOR,
                        GenealogyUser.ROLE_VIEWER,
                    }:
                        error = "邀请失败：角色不合法。"
                    else:
                        target_user = User.objects.filter(username=username).first()
                        if not target_user:
                            error = "邀请失败：用户不存在。"
                        else:
                            GenealogyUser.objects.update_or_create(
                                user=target_user,
                                genealogy_id=selected_genealogy_id,
                                defaults={"role": invite_role},
                            )
                            status_message = "邀请成功。"

        elif action in {"create_member", "update_member", "delete_member"}:
            if selected_genealogy_id not in accessible_ids:
                error = "操作失败：无权限访问该族谱。"
            elif not _can_write_genealogy(request.user, selected_genealogy_id):
                error = "操作失败：当前角色仅支持只读访问。"
            elif action == "create_member":
                name = request.POST.get("name", "").strip()
                gender = request.POST.get("gender", "").strip()
                if name and gender in {"M", "F"}:
                    Member.objects.create(
                        genealogy_id=selected_genealogy_id,
                        name=name,
                        gender=gender,
                        birth_year=_to_int(request.POST.get("birth_year")),
                        death_year=_to_int(request.POST.get("death_year")),
                        biography=request.POST.get("biography", "").strip(),
                    )
                    status_message = "成员创建成功。"
                else:
                    error = "创建成员失败：请填写姓名并选择性别。"
            elif action == "update_member":
                member_id = _to_int(request.POST.get("member_id"))
                member = Member.objects.filter(
                    member_id=member_id, genealogy_id=selected_genealogy_id
                ).first()
                if not member:
                    error = "更新失败：成员不存在。"
                else:
                    name = request.POST.get("name", "").strip()
                    gender = request.POST.get("gender", "").strip()
                    if not name or gender not in {"M", "F"}:
                        error = "更新失败：姓名和性别必填。"
                    else:
                        member.name = name
                        member.gender = gender
                        member.birth_year = _to_int(request.POST.get("birth_year"))
                        member.death_year = _to_int(request.POST.get("death_year"))
                        member.biography = request.POST.get("biography", "").strip()
                        member.save()
                        status_message = "成员更新成功。"
            else:
                member_id = _to_int(request.POST.get("member_id"))
                deleted, _ = Member.objects.filter(
                    member_id=member_id, genealogy_id=selected_genealogy_id
                ).delete()
                if deleted:
                    status_message = "成员删除成功。"
                else:
                    error = "删除失败：成员不存在。"
        else:
            error = "未知操作。"

        query_params = {}
        if selected_genealogy_id is not None:
            query_params["genealogy_id"] = selected_genealogy_id
        if status_message:
            query_params["status"] = status_message
        if error:
            query_params["error"] = error
        redirect_url = "/members-page"
        if query_params:
            redirect_url = f"{redirect_url}?{urlencode(query_params)}"
        return redirect(redirect_url)

    status_message = request.GET.get("status", "").strip()
    error = request.GET.get("error", "").strip()
    search_name = request.GET.get("name", "").strip()
    member_qs = Member.objects.none()
    if selected_genealogy_id in accessible_ids:
        member_qs = Member.objects.filter(genealogy_id=selected_genealogy_id).order_by(
            "member_id"
        )
        if search_name:
            member_qs = member_qs.filter(name__startswith=search_name)

    selected_link = link_by_genealogy.get(selected_genealogy_id)
    selected_role = selected_link.role if selected_link else ""
    can_write_selected = selected_role in {
        GenealogyUser.ROLE_OWNER,
        GenealogyUser.ROLE_EDITOR,
    }
    can_invite_selected = selected_role == GenealogyUser.ROLE_OWNER

    return render(
        request,
        "members.html",
        {
            "genealogies": genealogies,
            "selected_genealogy_id": selected_genealogy_id,
            "members": member_qs,
            "search_name": search_name,
            "selected_role": selected_role,
            "can_write_selected": can_write_selected,
            "can_invite_selected": can_invite_selected,
            "status_message": status_message,
            "error": error,
        },
    )


@login_required
@require_http_methods(["GET"])
def tree_page_view(request):
    links = GenealogyUser.objects.filter(user=request.user).values_list(
        "genealogy_id", flat=True
    )
    members = Member.objects.filter(genealogy_id__in=links).order_by("member_id")
    selected_member_id = _to_int(request.GET.get("member_id"))
    if selected_member_id is None and members:
        selected_member_id = members[0].member_id

    selected_member = members.filter(member_id=selected_member_id).first()
    tree = build_descendant_tree(selected_member.member_id) if selected_member else {}

    return render(
        request,
        "tree.html",
        {
            "members": members,
            "selected_member_id": selected_member_id,
            "tree_json": json.dumps(tree, ensure_ascii=False),
        },
    )


@login_required
@require_http_methods(["GET"])
def dashboard_page_view(request):
    links = GenealogyUser.objects.filter(user=request.user).select_related("genealogy")
    genealogies = [link.genealogy for link in links]
    if not genealogies:
        return render(request, "dashboard.html", {"error": "当前用户还没有可访问的族谱"})

    accessible_ids = [g.genealogy_id for g in genealogies]
    selected_genealogy_id = _to_int(request.GET.get("genealogy_id")) or accessible_ids[0]
    if selected_genealogy_id not in accessible_ids:
        return HttpResponseForbidden("无权限访问该族谱")

    selected_genealogy = next(
        (g for g in genealogies if g.genealogy_id == selected_genealogy_id), None
    )
    stats = _build_dashboard_stats(selected_genealogy_id)

    return render(
        request,
        "dashboard.html",
        {
            "genealogies": genealogies,
            "selected_genealogy_id": selected_genealogy_id,
            "selected_genealogy": selected_genealogy,
            "stats": stats,
        },
    )
