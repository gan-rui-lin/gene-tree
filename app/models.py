from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q


class User(AbstractUser):
    id = None
    user_id = models.BigAutoField(primary_key=True)
    email = models.EmailField(unique=True)

    class Meta:
        db_table = "user"


class Genealogy(models.Model):
    genealogy_id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=255)
    surname = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="created_genealogies"
    )

    class Meta:
        db_table = "genealogy"


class GenealogyUser(models.Model):
    ROLE_OWNER = "owner"
    ROLE_EDITOR = "editor"
    ROLE_VIEWER = "viewer"
    ROLE_CHOICES = [
        (ROLE_OWNER, "Owner"),
        (ROLE_EDITOR, "Editor"),
        (ROLE_VIEWER, "Viewer"),
    ]

    genealogy_user_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="genealogy_links")
    genealogy = models.ForeignKey(
        Genealogy, on_delete=models.CASCADE, related_name="user_links"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_VIEWER)

    class Meta:
        db_table = "genealogy_user"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "genealogy"], name="uq_genealogy_user_user_genealogy"
            )
        ]


class Member(models.Model):
    GENDER_MALE = "M"
    GENDER_FEMALE = "F"
    GENDER_CHOICES = [(GENDER_MALE, "Male"), (GENDER_FEMALE, "Female")]

    member_id = models.BigAutoField(primary_key=True)
    genealogy = models.ForeignKey(
        Genealogy, on_delete=models.CASCADE, related_name="members"
    )
    name = models.CharField(max_length=100, db_index=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    birth_year = models.PositiveIntegerField(null=True, blank=True)
    death_year = models.PositiveIntegerField(null=True, blank=True)
    biography = models.TextField(blank=True, default="")

    class Meta:
        db_table = "member"
        indexes = [models.Index(fields=["name"], name="idx_member_name")]


class ParentChild(models.Model):
    RELATION_FATHER = "father"
    RELATION_MOTHER = "mother"
    RELATION_CHOICES = [
        (RELATION_FATHER, "Father"),
        (RELATION_MOTHER, "Mother"),
    ]

    pk = models.CompositePrimaryKey("parent_id", "child_id")
    parent = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name="children_links"
    )
    child = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name="parent_links"
    )
    relation_type = models.CharField(max_length=10, choices=RELATION_CHOICES)

    class Meta:
        db_table = "parent_child"
        constraints = [
            models.CheckConstraint(
                check=~Q(parent=models.F("child")), name="chk_parent_not_self"
            ),
        ]
        indexes = [
            models.Index(fields=["parent"], name="idx_parent"),
            models.Index(fields=["child"], name="idx_child"),
            models.Index(fields=["parent", "child"], name="idx_parent_child"),
        ]


class Marriage(models.Model):
    marriage_id = models.BigAutoField(primary_key=True)
    spouse1 = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name="marriages_as_spouse1"
    )
    spouse2 = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name="marriages_as_spouse2"
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, default="active")

    class Meta:
        db_table = "marriage"
        constraints = [
            models.CheckConstraint(
                check=~Q(spouse1=models.F("spouse2")), name="chk_spouse_not_same"
            )
        ]
