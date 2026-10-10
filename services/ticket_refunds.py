"""KALXA ticket refunds — explicit, admin-only service functions.

Integrate by importing these functions from an authenticated, CSRF-protected
super-admin route. Do not expose initiate_ticket_refund directly to customers.

Dependencies are passed in to avoid assuming your application's package layout:
    from services.ticket_refunds import initiate_ticket_refund, reconcile_ticket_refund
    initiate_ticket_refund(order_id=..., entry_pass_ids=[...], requested_by=...,
        db=db, TicketOrder=TicketOrder, TicketRefund=TicketRefund,
        TicketRefundItem=TicketRefundItem, EntryPass=EntryPass,
        paystack_api_request=paystack_api_request)

This service deliberately does not implement Paystack settlement transfers.
"""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4


CENT = Decimal("0.01")
ACTIVE_REFUNDS = {"requested", "submitted", "pending", "processing"}
CONFIRMED_REFUNDS = {"processed"}  # Paystack refund status; not 'pending'.


class TicketRefundError(RuntimeError):
    pass


def _money(value):
    result = Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
    if not result.is_finite():
        raise TicketRefundError("Invalid monetary amount.")
    return result


def _cents(value):
    amount = _money(value)
    if amount <= 0:
        raise TicketRefundError("Refund amount must be positive.")
    return int(amount * 100)


def _refund_provider_id(data):
    value = data.get("id")
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value).strip():
        raise TicketRefundError("Paystack refund ID missing.")
    return str(value).strip()


def _provider_transaction_matches(data, order):
    """Match Paystack's refund transaction object/ID to original payment."""
    txn = data.get("transaction")
    expected = str(order.paystack_transaction_id or "").strip()
    if not expected:
        raise TicketRefundError("Original Paystack transaction ID missing.")
    if isinstance(txn, dict):
        txn = txn.get("id")
    if isinstance(txn, bool) or txn is None or str(txn).strip() != expected:
        raise TicketRefundError("Refund transaction does not match the order.")


def _fetch_refund(refund, order, paystack_api_request):
    if not refund.paystack_refund_id:
        raise TicketRefundError("Refund has no provider ID; manual reconciliation required.")
    from urllib.parse import quote
    result = paystack_api_request(
        "GET", "/refund/" + quote(str(refund.paystack_refund_id), safe="")
    )
    if not isinstance(result, dict) or result.get("status") is not True:
        raise TicketRefundError("Paystack refund lookup failed.")
    data = result.get("data")
    if not isinstance(data, dict):
        raise TicketRefundError("Invalid Paystack refund response.")
    if _refund_provider_id(data) != str(refund.paystack_refund_id):
        raise TicketRefundError("Paystack refund ID mismatch.")
    _provider_transaction_matches(data, order)
    amount = data.get("amount")
    if isinstance(amount, bool) or not isinstance(amount, int) or amount != _cents(refund.provider_refund_amount):
        raise TicketRefundError("Paystack refund amount mismatch.")
    currency = data.get("currency")
    if currency is not None and currency != "ZAR":
        raise TicketRefundError("Unexpected Paystack refund currency.")
    return data


def initiate_ticket_refund(*, order_id, entry_pass_ids, requested_by, db,
                           TicketOrder, TicketRefund, TicketRefundItem, EntryPass,
                           paystack_api_request, reason=None):
    """Request a face-value refund for selected unused passes.

    No automatic retry of ambiguous POST /refund responses: a timeout might
    occur after Paystack accepted the request. Reconcile manually first.
    """
    if not requested_by or not str(requested_by).strip():
        raise TicketRefundError("Authenticated administrator identity required.")
    if not isinstance(entry_pass_ids, (list, tuple)) or not entry_pass_ids:
        raise TicketRefundError("Select at least one ticket to refund.")
    if any(isinstance(x, bool) or not isinstance(x, int) or x <= 0 for x in entry_pass_ids):
        raise TicketRefundError("Invalid entry pass ID.")
    ids = sorted(set(entry_pass_ids))
    if len(ids) != len(entry_pass_ids):
        raise TicketRefundError("Duplicate entry pass selected.")

    # Reserve the selected passes by creating a durable refund request under
    # the order lock. A single active refund per order is allowed.
    try:
        order = (db.session.query(TicketOrder).filter_by(id=order_id)
                 .with_for_update().one_or_none())
        if order is None or order.payment_status != "paid":
            raise TicketRefundError("Order is not paid or does not exist.")
        if order.payment_provider != "paystack" or not order.paystack_transaction_id:
            raise TicketRefundError("Order has no verified Paystack transaction.")
        if order.commission_amount is None or order.commission_rate is None:
            raise TicketRefundError("Order commission snapshot missing; reconcile first.")
        if db.session.query(TicketRefund.id).filter(
            TicketRefund.order_id == order.id,
            TicketRefund.status.in_(ACTIVE_REFUNDS)
        ).first():
            raise TicketRefundError("An unresolved refund already exists for this order.")

        passes = (db.session.query(EntryPass).filter(
            EntryPass.order_id == order.id, EntryPass.id.in_(ids)
        ).with_for_update().all())
        if len(passes) != len(ids):
            raise TicketRefundError("One or more passes do not belong to this order.")
        if any(p.status != "valid" or p.checked_in_at is not None or p.checkins for p in passes):
            raise TicketRefundError("Used, cancelled, or previously refunded tickets cannot be refunded.")

        items_by_id = {i.id: i for i in order.order_items}
        legacy = not bool(order.order_items)
        if not legacy and any(p.order_item_id not in items_by_id for p in passes):
            raise TicketRefundError("Ticket line association missing.")
        if legacy and any(p.order_item_id is not None for p in passes):
            raise TicketRefundError("Unexpected ticket line on legacy order.")

        lines = []
        for p in passes:
            unit = (order.ticket_price if legacy else items_by_id[p.order_item_id].unit_price)
            amount = _money(unit)
            if amount <= 0:
                raise TicketRefundError("Zero-price tickets require a separate cancellation workflow.")
            lines.append((p, amount))
        face_value = sum((a for _, a in lines), Decimal("0.00"))
        total = _money(order.total_amount)
        if face_value > total - _money(order.refunded_face_value or 0):
            raise TicketRefundError("Refund exceeds remaining ticket face value.")
        if _money(order.checkout_amount if order.checkout_amount is not None else total) < face_value:
            raise TicketRefundError("Refund exceeds original checkout amount.")

        # Block tickets that already have a succeeded refund, including a
        # previously reconciled request whose pass state is inconsistent.
        previous = (db.session.query(TicketRefundItem.entry_pass_id)
                    .join(TicketRefund, TicketRefund.id == TicketRefundItem.refund_id)
                    .filter(TicketRefund.order_id == order.id,
                            TicketRefund.status == "succeeded",
                            TicketRefundItem.entry_pass_id.in_(ids)).first())
        if previous:
            raise TicketRefundError("One of these tickets was already refunded.")

        refund = TicketRefund(
            order_id=order.id,
            refund_reference="KXRF-" + uuid4().hex.upper(),
            paystack_transaction_id=str(order.paystack_transaction_id),
            face_value_amount=face_value,
            provider_refund_amount=face_value,
            status="requested",
            requested_by=str(requested_by).strip()[:100],
            reason=reason,
        )
        db.session.add(refund)
        db.session.flush()
        for p, amount in lines:
            db.session.add(TicketRefundItem(
                refund_id=refund.id, order_item_id=p.order_item_id,
                entry_pass_id=p.id, quantity=1, face_value_amount=amount
            ))
        order.refund_status = "pending"
        refund_id = refund.id
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    # External network call must occur outside the order lock/DB transaction.
    # A transport error leaves 'requested' for investigation; never blindly
    # send a second POST because the first request may have succeeded.
    try:
        response = paystack_api_request("POST", "/refund", json={
            "transaction": str(order.paystack_transaction_id),
            "amount": _cents(face_value),
            "merchant_note": "KALXA ticket refund " + refund.refund_reference,
        })
        if not isinstance(response, dict) or response.get("status") is not True:
            raise TicketRefundError("Paystack did not confirm refund request acceptance.")
        data = response.get("data")
        if not isinstance(data, dict):
            raise TicketRefundError("Paystack returned invalid refund data.")
        provider_id = _refund_provider_id(data)
        _provider_transaction_matches(data, order)
        amount = data.get("amount")
        if isinstance(amount, bool) or not isinstance(amount, int) or amount != _cents(face_value):
            raise TicketRefundError("Paystack refund request amount mismatch.")
    except Exception:
        # Keep 'requested': external state unknown; investigate in Paystack.
        raise

    try:
        refund = (db.session.query(TicketRefund).filter_by(id=refund_id)
                  .with_for_update().one())
        refund.paystack_refund_id = provider_id
        refund.status = "pending"
        refund.submitted_at = datetime.utcnow()
        db.session.commit()
        return refund
    except Exception:
        db.session.rollback()
        raise


def reconcile_ticket_refund(*, refund_id, db, TicketOrder, TicketOrderItem,
                            TicketRefund, TicketRefundItem, EntryPass,
                            paystack_api_request):
    """Verify Paystack refund state and apply ticket/accounting changes once.

    IMPORTANT: The GET response is independently fetched from Paystack, not
    trusted from a webhook body. PostgreSQL row locks serialize accounting.
    """
    # Get ID before entering the DB lock; no refund state is modified here.
    refund = db.session.get(TicketRefund, refund_id)
    if refund is None:
        raise TicketRefundError("Refund not found.")
    order = db.session.get(TicketOrder, refund.order_id)
    if order is None:
        raise TicketRefundError("Refund order not found.")
    data = _fetch_refund(refund, order, paystack_api_request)
    provider_status = data.get("status")
    if not isinstance(provider_status, str):
        raise TicketRefundError("Paystack refund status missing.")

    try:
        # Lock order first, consistently with initiation.
        order = (db.session.query(TicketOrder).filter_by(id=order.id)
                 .populate_existing().with_for_update().one())
        refund = (db.session.query(TicketRefund).filter_by(id=refund_id)
                  .populate_existing().with_for_update().one())
        if refund.accounting_applied_at is not None:
            db.session.commit()
            return refund
        if refund.status in {"failed", "cancelled"}:
            raise TicketRefundError("Terminal refund state requires manual investigation.")
        if provider_status in {"failed", "cancelled", "rejected"}:
            refund.status = "failed" if provider_status != "cancelled" else "cancelled"
            # Previous partial refunds remain represented in the order summary.
            order.refresh_refund_status()
            db.session.commit()
            return refund
        if provider_status not in CONFIRMED_REFUNDS:
            refund.status = "processing" if provider_status == "processing" else "pending"
            db.session.commit()
            return refund

        if order.payment_status != "paid":
            raise TicketRefundError("Original order is no longer paid.")
        if order.commission_rate is None or order.commission_amount is None:
            raise TicketRefundError("Missing original commission snapshot.")
        items = (db.session.query(TicketRefundItem).filter_by(refund_id=refund.id)
                 .order_by(TicketRefundItem.id).all())
        if not items or any(i.entry_pass_id is None or i.quantity != 1 for i in items):
            raise TicketRefundError("Refund has unidentified ticket lines.")
        ids = [i.entry_pass_id for i in items]
        if len(set(ids)) != len(ids):
            raise TicketRefundError("Refund contains duplicate passes.")
        passes = (db.session.query(EntryPass).filter(EntryPass.id.in_(ids))
                  .with_for_update().all())
        passes_by_id = {p.id: p for p in passes}
        if len(passes_by_id) != len(ids):
            raise TicketRefundError("Refund ticket is missing.")
        line_totals = {}
        for item in items:
            p = passes_by_id[item.entry_pass_id]
            if p.order_id != order.id or p.order_item_id != item.order_item_id:
                raise TicketRefundError("Refund ticket ownership mismatch.")
            if p.status != "valid" or p.checked_in_at is not None or p.checkins:
                raise TicketRefundError("Refunded ticket was used or changed; manual review required.")
            if item.order_item_id is not None:
                line_totals[item.order_item_id] = line_totals.get(item.order_item_id, Decimal("0.00")) + _money(item.face_value_amount)
        face_value = sum((_money(i.face_value_amount) for i in items), Decimal("0.00"))
        if face_value != _money(refund.face_value_amount):
            raise TicketRefundError("Refund line totals do not match refund amount.")
        already_refunded = _money(order.refunded_face_value or 0)
        original_total = _money(order.total_amount)
        if already_refunded + face_value > original_total:
            raise TicketRefundError("Cumulative refunds exceed order total.")

        # Cumulative calculation prevents penny drift across partial refunds.
        original_commission = _money(order.commission_amount)
        new_refunded = already_refunded + face_value
        target_reversal = (original_commission if new_refunded == original_total
                           else _money(new_refunded * Decimal(str(order.commission_rate))))
        target_reversal = min(target_reversal, original_commission)
        old_reversal = _money(order.commission_reversed_amount or 0)
        delta = target_reversal - old_reversal
        if delta < 0:
            raise TicketRefundError("Commission reversal ledger is inconsistent.")

        for item_id, amount in line_totals.items():
            line = (db.session.query(TicketOrderItem).filter_by(id=item_id)
                    .with_for_update().one())
            count = sum(1 for i in items if i.order_item_id == item_id)
            if line.order_id != order.id or int(line.refunded_quantity or 0) + count > line.quantity:
                raise TicketRefundError("Ticket line refund quantity exceeded.")
            if _money(line.refunded_face_value or 0) + amount > _money(line.line_total):
                raise TicketRefundError("Ticket line refund amount exceeded.")
            line.refunded_quantity = int(line.refunded_quantity or 0) + count
            line.refunded_face_value = _money(line.refunded_face_value or 0) + amount

        for p in passes:
            p.status = "refunded"
        order.refunded_face_value = new_refunded
        order.commission_reversed_amount = target_reversal
        order.refunded_at = datetime.utcnow()
        refund.commission_reversal_amount = delta
        refund.status = "succeeded"
        refund.accounting_applied_at = datetime.utcnow()
        refund.completed_at = refund.accounting_applied_at
        order.refresh_refund_status()
        db.session.commit()
        return refund
    except Exception:
        db.session.rollback()
        raise
