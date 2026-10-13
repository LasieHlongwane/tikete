"""KALXA ticket inventory reservations.

Integrate into the Flask application after importing db, TicketEvent,
TicketOrder, TicketOrderItem, TicketType and TicketSalePhase.

All reservation writers MUST use the same TicketEvent row lock.
No Paystack network requests may occur inside the lock transaction.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import and_, or_, func

RESERVATION_MINUTES = 15
ACTIVE_RESERVATION_STATUSES = ("pending", "processing")

class InventoryUnavailable(ValueError):
    pass

class InventoryConfigurationError(ValueError):
    pass


def _inventory_locked_event(event_id):
    """Acquire the shared event lock inside an active DB transaction."""
    event = (db.session.query(TicketEvent)
             .filter(TicketEvent.id == event_id)
             .with_for_update()
             .one_or_none())
    if event is None:
        raise InventoryUnavailable("Event no longer exists.")
    return event


def _inventory_order_filter(event_id, now):
    return (
        TicketOrder.event_id == event_id,
        or_(
            TicketOrder.payment_status == "paid",
            and_(
                TicketOrder.payment_status.in_(ACTIVE_RESERVATION_STATUSES),
                TicketOrder.inventory_reserved_at.isnot(None),
                TicketOrder.inventory_released_at.is_(None),
                TicketOrder.reservation_expires_at > now,
            ),
        ),
    )


def _committed_item_quantity(event_id, now, *, ticket_type_id=None, sale_phase_id=None):
    q = (db.session.query(func.coalesce(func.sum(TicketOrderItem.quantity), 0))
         .join(TicketOrder, TicketOrder.id == TicketOrderItem.order_id)
         .filter(*_inventory_order_filter(event_id, now)))
    if ticket_type_id is not None:
        q = q.filter(TicketOrderItem.ticket_type_id == ticket_type_id)
    if sale_phase_id is not None:
        q = q.filter(TicketOrderItem.sale_phase_id == sale_phase_id)
    return int(q.scalar() or 0)


def _committed_general_quantity(event_id, now):
    """Include legacy general orders without order items and modern general items.

    An order with ANY order items counts only its general items, never its
    order-level quantity, avoiding double counting mixed historical records.
    """
    general_items = (db.session.query(func.coalesce(func.sum(TicketOrderItem.quantity), 0))
                     .join(TicketOrder, TicketOrder.id == TicketOrderItem.order_id)
                     .filter(*_inventory_order_filter(event_id, now))
                     .filter(TicketOrderItem.ticket_type_id.is_(None))
                     .scalar() or 0)
    item_exists = (db.session.query(TicketOrderItem.id)
                   .filter(TicketOrderItem.order_id == TicketOrder.id)
                   .exists())
    legacy = (db.session.query(func.coalesce(func.sum(TicketOrder.quantity), 0))
              .filter(*_inventory_order_filter(event_id, now))
              .filter(~item_exists)
              .scalar() or 0)
    return int(general_items) + int(legacy)


def _strict_quantity(value):
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 10:
        raise InventoryUnavailable("Each requested quantity must be an integer from 1 to 10.")
    return value


def validate_inventory_basket_locked(event, basket, now=None):
    """Call only after locking the event row in this same transaction.

    basket entries: {ticket_type_id: int|None, sale_phase_id: int|None,
                     quantity: int}. Returns total quantity.
    """
    now = now or datetime.utcnow()
    if not event.active or event.status != "published" or not event.sales_open or event.organizer_deleted:
        raise InventoryUnavailable("Ticket sales are not available for this event.")
    if not basket:
        raise InventoryUnavailable("Select at least one ticket.")
    total = sum(_strict_quantity(line.get("quantity")) for line in basket)
    if total > 10:
        raise InventoryUnavailable("Maximum 10 tickets per order.")

    active_types = (db.session.query(TicketType)
                    .filter(TicketType.event_id == event.id, TicketType.active.is_(True))
                    .all())
    types_by_id = {t.id: t for t in active_types}
    if active_types and any(line.get("ticket_type_id") is None for line in basket):
        raise InventoryUnavailable("General tickets are not available for this event.")
    if not active_types and any(line.get("ticket_type_id") is not None for line in basket):
        raise InventoryUnavailable("This event only offers General tickets.")

    quantities_by_type = {}
    quantities_by_phase = {}
    general_qty = 0
    for line in basket:
        qty = line["quantity"]
        type_id = line.get("ticket_type_id")
        phase_id = line.get("sale_phase_id")
        if type_id is None:
            if phase_id is not None:
                raise InventoryUnavailable("General tickets cannot have a sale phase.")
            general_qty += qty
            continue
        ticket_type = types_by_id.get(type_id)
        if ticket_type is None:
            raise InventoryUnavailable("Selected ticket type is unavailable.")
        quantities_by_type[type_id] = quantities_by_type.get(type_id, 0) + qty
        phases = [p for p in ticket_type.sale_phases if p.active]
        if phases:
            matching = [p for p in phases if p.id == phase_id]
            if len(matching) != 1 or not matching[0].is_available_at(now):
                raise InventoryUnavailable("Selected ticket sale phase is unavailable.")
            quantities_by_phase[phase_id] = quantities_by_phase.get(phase_id, 0) + qty
        elif phase_id is not None:
            raise InventoryUnavailable("Selected ticket type has no active sale phase.")

    if general_qty and event.ticket_capacity is not None:
        remaining = event.ticket_capacity - _committed_general_quantity(event.id, now)
        if general_qty > remaining:
            raise InventoryUnavailable("Not enough General tickets remain.")

    for type_id, qty in quantities_by_type.items():
        ticket_type = types_by_id[type_id]
        if ticket_type.capacity is not None:
            remaining = ticket_type.capacity - _committed_item_quantity(
                event.id, now, ticket_type_id=type_id)
            if qty > remaining:
                raise InventoryUnavailable(f"Not enough {ticket_type.name} tickets remain.")

    for phase_id, qty in quantities_by_phase.items():
        phase = db.session.get(TicketSalePhase, phase_id)
        if phase.quantity_limit is not None:
            remaining = phase.quantity_limit - _committed_item_quantity(
                event.id, now, sale_phase_id=phase_id)
            if qty > remaining:
                raise InventoryUnavailable(f"Not enough {phase.name} phase tickets remain.")
    return total


def reserve_inventory_for_order_locked(event, order, basket, *, now=None, minutes=RESERVATION_MINUTES):
    """Validate and stamp a NEW pending order, under an event row lock.

    The caller must add the order and ALL its TicketOrderItem rows in the same
    transaction and commit only once. No Paystack call inside the transaction.
    """
    if order.id is not None or order.payment_status != "pending":
        raise InventoryConfigurationError("Reservation requires a new pending order.")
    if not isinstance(minutes, int) or not 1 <= minutes <= 60:
        raise InventoryConfigurationError("Invalid reservation duration.")
    now = now or datetime.utcnow()
    total = validate_inventory_basket_locked(event, basket, now)
    if order.event_id != event.id or order.quantity != total:
        raise InventoryConfigurationError("Order does not match reserved event and quantity.")
    order.inventory_reserved_at = now
    order.reservation_expires_at = now + timedelta(minutes=minutes)
    order.inventory_released_at = None
    return order


def release_unpaid_reservation(order_id, *, verified_unpaid=False):
    """Release only after trusted payment-state reconciliation.

    verified_unpaid=True is an explicit assertion by the calling payment
    service that Paystack cannot subsequently complete this checkout.
    Do NOT pass True merely because a local timer expired or a browser
    returned from checkout. This function does not call Paystack.
    """
    if not verified_unpaid:
        raise InventoryConfigurationError("Payment must be conclusively resolved before release.")
    order_event_id = (db.session.query(TicketOrder.event_id)
                      .filter(TicketOrder.id == order_id).scalar())
    if order_event_id is None:
        raise InventoryUnavailable("Order not found.")
    _inventory_locked_event(order_event_id)
    order = (db.session.query(TicketOrder)
             .filter(TicketOrder.id == order_id)
             .with_for_update().one())
    if order.payment_status not in ACTIVE_RESERVATION_STATUSES:
        raise InventoryUnavailable("Only unpaid reservations may be released.")
    if order.inventory_released_at is None:
        order.inventory_released_at = datetime.utcnow()
    # Caller owns transaction and must commit with its payment-state update.
    return order
