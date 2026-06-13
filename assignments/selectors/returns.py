from assignments.models import ReturnRequest, ReturnRequestItem

def pending_return_request_items_queryset():
    """returns all returns requet items that are currently pending"""
    return ReturnRequestItem.objects.filter(
        status=ReturnRequestItem.Status.PENDING
    )


def stale_return_requests_queryset( *, older_than, ):

    return ReturnRequest.objects.filter(
        status=ReturnRequest.Status.PENDING,
        requested_at__lt=older_than,
    )

def created_return_requests_queryset(
    *,
    created_after=None,
    created_before=None,
):
    qs = ReturnRequest.objects.all()

    if created_after:
        qs = qs.filter(
            requested_at__gte=created_after
        )

    if created_before:
        qs = qs.filter(
            requested_at__lt=created_before
        )

    return qs




def return_requests_queryset(
    *,
    status=None,
    requested_after=None,
    requested_before=None,
    processed_after=None,
    processed_before=None,
):
    """
    Base ReturnRequest selector.

    Supports filtering by:
    - status
    - request window
    - processing window
    """

    qs = ReturnRequest.objects.all()

    if status is not None:
        qs = qs.filter(
            status=status
        )

    if requested_after is not None:
        qs = qs.filter(
            requested_at__gte=requested_after
        )

    if requested_before is not None:
        qs = qs.filter(
            requested_at__lt=requested_before
        )

    if processed_after is not None:
        qs = qs.filter(
            processed_at__gte=processed_after
        )

    if processed_before is not None:
        qs = qs.filter(
            processed_at__lt=processed_before
        )

    return qs




def department_return_items_queryset(department):
    """
    Return request items associated with rooms
    in a department.
    """
    return ReturnRequestItem.objects.filter(
        room__location__department=department
    )


def department_return_requests_queryset(department):
    """
    Return requests associated with a department.
    """
    request_ids = (
        department_return_items_queryset(
            department
        )
        .values_list(
            "return_request_id",
            flat=True,
        )
        .distinct()
    )

    return ReturnRequest.objects.filter(
        id__in=request_ids
    )