
def validate_sale_quantity(
    available_quantity: int,
    sale_quantity: int,
) -> None:
    if sale_quantity <= 0:
        raise ValueError("Sale quantity must be greater than zero.")

    if available_quantity < 0:
        raise ValueError("Available stock cannot be negative.")

    if sale_quantity > available_quantity:
        raise ValueError(
            f"Insufficient stock for sale. Available: "
            f"{available_quantity}, requested: {sale_quantity}."
        )


def validate_invoice_stock(
    available_quantity: int,
    invoice_quantity: int,
) -> None:
    if invoice_quantity <= 0:
        raise ValueError("Invoice quantity must be greater than zero.")

    if invoice_quantity > available_quantity:
        raise ValueError(
            "Invoice quantity cannot exceed available stock."
        )


def validate_return_quantity(
    sold_quantity: int,
    already_returned_quantity: int,
    return_quantity: int,
) -> None:
    if sold_quantity < 0 or already_returned_quantity < 0:
        raise ValueError("Sold and returned quantities cannot be negative.")

    if return_quantity <= 0:
        raise ValueError("Return quantity must be greater than zero.")

    remaining_quantity = sold_quantity - already_returned_quantity

    if return_quantity > remaining_quantity:
        raise ValueError(
            f"Return quantity exceeds the remaining returnable quantity "
            f"({max(remaining_quantity, 0)})."
        )