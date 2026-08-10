from rest_framework.permissions import SAFE_METHODS, BasePermission


class ChemicalPermission(BasePermission):
    """Mirrors the old RLS intent:
    - any authenticated user can view and create
    - the creator or an administrator can update
    - only an administrator can delete
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.method == "DELETE":
            return request.user.is_administrator
        return obj.created_by_id == request.user.id or request.user.is_administrator
