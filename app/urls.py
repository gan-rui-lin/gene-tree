from django.urls import path

from . import views

urlpatterns = [
    path("", views.login_page_view, name="root"),
    path("login-page", views.login_page_view, name="login-page"),
    path("dashboard-page", views.dashboard_page_view, name="dashboard-page"),
    path("analysis-page", views.analysis_page_view, name="analysis-page"),
    path("members-page", views.members_page_view, name="members-page"),
    path("tree-page", views.tree_page_view, name="tree-page"),
    path("ancestors-tree-page", views.ancestors_tree_page_view, name="ancestors-tree-page"),
    path("register", views.register_view, name="register"),
    path("login", views.login_view, name="login"),
    path("genealogies", views.genealogies_view, name="genealogies"),
    path(
        "genealogies/<int:genealogy_id>/invite",
        views.invite_user_view,
        name="invite-user",
    ),
    path("members", views.members_view, name="members"),
    path("members/<int:member_id>", views.member_detail_view, name="member-detail"),
    path("analysis/spouse-children/<int:member_id>", views.spouse_children_view, name="analysis-spouse-children"),
    path("analysis/longest-lifespan-generation", views.longest_lifespan_generation_view, name="analysis-longest-lifespan-generation"),
    path("analysis/unmarried-male-over-50", views.unmarried_male_over_50_view, name="analysis-unmarried-male-over-50"),
    path("analysis/early-born-members", views.early_born_members_view, name="analysis-early-born-members"),
    path("ancestors/<int:member_id>", views.ancestors_view, name="ancestors"),
    path("descendants/<int:member_id>", views.descendants_view, name="descendants"),
    path("relationship", views.relationship_view, name="relationship"),
    path("relationship-sql", views.relationship_sql_view, name="relationship-sql"),
    path("tree/<int:member_id>", views.tree_data_view, name="tree-data"),
    path("ancestors-tree/<int:member_id>", views.ancestors_tree_data_view, name="ancestors-tree-data"),
    path("dashboard", views.dashboard_view, name="dashboard"),
]
