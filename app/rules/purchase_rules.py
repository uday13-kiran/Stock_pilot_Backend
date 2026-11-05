
VALID_PURCHASE_STATUSES = {
    "DRAFT",
    "APPROVED",
    "ORDERED",
    "PARTIALLY_RECEIVED",
    "RECEIVED",
    "CANCELLED",
}


def validate_receive_quantity(
    ordered_quantity: int,
    already_received_quantity: int,
    receiving_quantity: int,
) -> None:
    if ordered_quantity <= 0:
        raise ValueError("Ordered quantity must be greater than zero.")

    if already_received_quantity < 0:
        raise ValueError("Received quantity cannot be negative.")

    if receiving_quantity <= 0:
        raise ValueError("Receiving quantity must be greater than zero.")

    remaining_quantity = (
        ordered_quantity - already_received_quantity
    )

    if receiving_quantity > remaining_quantity:
        raise ValueError(
            f"Cannot receive more than the remaining ordered quantity "
            f"({max(remaining_quantity, 0)})."
        )


def validate_purchase_status(status: str) -> None:
    normalized_status = status.strip().upper()

    if normalized_status not in VALID_PURCHASE_STATUSES:
        raise ValueError(
            f"Invalid purchase status: {status}. "
            f"Allowed statuses: {', '.join(sorted(VALID_PURCHASE_STATUSES))}."
        )