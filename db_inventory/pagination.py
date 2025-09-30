from rest_framework.pagination import PageNumberPagination

class OptionalPagination(PageNumberPagination):
    """
    Allows disabling pagination by passing ?paginate=false in the query params.
    """
    def paginate_queryset(self, queryset, request, view=None):
        paginate_param = request.query_params.get("paginate")
        if paginate_param and paginate_param.lower() == "false":
            return None  # disables pagination, returns full queryset
        return super().paginate_queryset(queryset, request, view)


class BasePagination(PageNumberPagination):
    page_size = 20  # default
    page_size_query_param = "page_size"  
    max_page_size = 200  