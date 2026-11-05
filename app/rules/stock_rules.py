
def validate_non_negative(quantity: int) -> None:
    if quantity < 0:
        raise ValueError("Quantity cannot be negative.")


def validate_stock_available(
    current_quantity: int,
    requested_quantity: int,
) -> None:
    validate_non_negative(current_quantity)
    validate_non_negative(requested_quantity)

    if requested_quantity > current_quantity:
        raise ValueError(
            f"Insufficient stock. Available: {current_quantity}, "
            f"requested: {requested_quantity}."
        )


def validate_transfer_quantity(
    source_quantity: int,
    transfer_quantity: int,
) -> None:
    validate_non_negative(source_quantity)

    if transfer_quantity <= 0:
        raise ValueError("Transfer quantity must be greater than zero.")

    validate_stock_available(source_quantity, transfer_quantity)