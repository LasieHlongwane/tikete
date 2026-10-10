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



def initiate_ticket_refund(
    *,
    order_id,
    entry_pass_ids,
    requested_by,
    db,
    TicketOrder,
    TicketRefund,
    TicketRefundItem,
    EntryPass,
    paystack_api_request,
    reason=None,
):
    """
    Initiate a KALXA ticket refund for selected unused passes.

    SECURITY:
        - Caller must authenticate the super-admin.
        - Lock the ticket order.
        - Lock selected entry passes.
        - Reject used, cancelled and refunded tickets.
        - Reject active or overlapping refunds.

    CONCURRENCY:
        Refund initiation and ticket check-in must lock
        the same EntryPass rows before changing state.

        Lock acquisition order:
            1. TicketOrder
            2. EntryPass rows, ascending ID

    PAYSTACK:
        - Persist the refund reservation first.
        - Commit before contacting Paystack.
        - Submit only one POST /refund attempt.
        - Never automatically retry uncertain requests.
        - Independently reconcile provider completion.

    ACCOUNTING:
        - Do not reverse KALXA commission here.
        - Do not increment refunded face value here.
        - Do not mark entry passes refunded here.

    Those operations belong to reconcile_ticket_refund()
    after Paystack confirms refund completion.

    IMPORTANT:
        A 'requested' refund may already have been
        accepted by Paystack even if this function raises
        an exception after sending the API request.
    """

    # ========================================================
    # 1. VALIDATE ADMINISTRATOR
    # ========================================================

    if (
        not isinstance(requested_by, str)
        or not requested_by.strip()
    ):
        raise TicketRefundError(
            "Authenticated administrator identity required."
        )

    requested_by = requested_by.strip()[:100]

    # ========================================================
    # 2. VALIDATE ORDER ID
    # ========================================================

    if (
        isinstance(order_id, bool)
        or not isinstance(order_id, int)
        or order_id <= 0
    ):
        raise TicketRefundError(
            "Invalid ticket order ID."
        )

    # ========================================================
    # 3. VALIDATE ENTRY-PASS SELECTION
    # ========================================================

    if (
        not isinstance(entry_pass_ids, (list, tuple))
        or not entry_pass_ids
    ):
        raise TicketRefundError(
            "Select at least one ticket to refund."
        )

    if len(entry_pass_ids) > 100:
        raise TicketRefundError(
            "A maximum of 100 tickets may be refunded "
            "in one request."
        )

    if any(
        isinstance(pass_id, bool)
        or not isinstance(pass_id, int)
        or pass_id <= 0
        for pass_id in entry_pass_ids
    ):
        raise TicketRefundError(
            "Invalid entry pass ID."
        )

    ids = sorted(entry_pass_ids)

    if len(ids) != len(set(ids)):
        raise TicketRefundError(
            "Duplicate entry pass selected."
        )

    # ========================================================
    # 4. VALIDATE REFUND REASON
    # ========================================================

    if reason is not None:

        if (
            not isinstance(reason, str)
            or len(reason) > 2000
        ):
            raise TicketRefundError(
                "Invalid refund reason."
            )

        reason = reason.strip() or None

    # ========================================================
    # 5. RESERVE REFUND IN DATABASE
    # ========================================================
    #
    # The reservation is committed before contacting
    # Paystack.
    #
    # This prevents another administrator from submitting
    # an overlapping refund while the provider request
    # is being processed.
    # ========================================================

    try:

        # ====================================================
        # LOCK TICKET ORDER
        # ====================================================

        order = (
            db.session.query(TicketOrder)
            .filter(
                TicketOrder.id == order_id
            )
            .populate_existing()
            .with_for_update()
            .one_or_none()
        )

        if order is None:
            raise TicketRefundError(
                "Ticket order does not exist."
            )

        if order.payment_status != "paid":
            raise TicketRefundError(
                "Only paid ticket orders can be refunded."
            )

        # ====================================================
        # VERIFY PAYMENT PROVIDER
        # ====================================================

        if order.payment_provider != "paystack":
            raise TicketRefundError(
                "This order was not paid through Paystack."
            )

        if not order.paystack_transaction_id:
            raise TicketRefundError(
                "Verified Paystack transaction ID is missing."
            )

        # ====================================================
        # VERIFY COMMISSION SNAPSHOT
        # ====================================================

        if (
            order.commission_amount is None
            or order.commission_rate is None
            or order.organizer_gross_share is None
            or order.commission_recorded_at is None
        ):
            raise TicketRefundError(
                "Ticket commission snapshot is incomplete. "
                "Reconcile the order before refunding."
            )

        # ====================================================
        # BLOCK OTHER ACTIVE REFUNDS
        # ========================================================
        #
        # Preserve the existing policy of allowing
        # only one unresolved refund per order.
        # ====================================================

        existing_active_refund = (
            db.session.query(TicketRefund.id)
            .filter(
                TicketRefund.order_id == order.id,
                TicketRefund.status.in_(
                    (
                        "requested",
                        "submitted",
                        "pending",
                        "processing",
                    )
                ),
            )
            .first()
        )

        if existing_active_refund is not None:
            raise TicketRefundError(
                "An unresolved refund already exists "
                "for this order."
            )

        # ====================================================
        # LOCK SELECTED ENTRY PASSES
        # ========================================================
        #
        # Lock rows in ascending order.
        #
        # The check-in service must acquire the same
        # EntryPass lock before checking refund state.
        # ====================================================

        passes = (
            db.session.query(EntryPass)
            .filter(
                EntryPass.order_id == order.id,
                EntryPass.id.in_(ids),
            )
            .order_by(
                EntryPass.id.asc()
            )
            .populate_existing()
            .with_for_update(
                of=EntryPass
            )
            .all()
        )

        if len(passes) != len(ids):
            raise TicketRefundError(
                "One or more selected tickets do not "
                "belong to this order."
            )

        # ====================================================
        # VERIFY ENTRY-PASS STATES
        # ====================================================

        for entry_pass in passes:

            if entry_pass.status != "valid":
                raise TicketRefundError(
                    "Used, cancelled or refunded tickets "
                    "cannot be refunded."
                )

            if entry_pass.checked_in_at is not None:
                raise TicketRefundError(
                    "A checked-in ticket cannot be refunded."
                )

            existing_checkin = (
                db.session.query(CheckIn.id)
                .filter(
                    CheckIn.entry_pass_id
                    == entry_pass.id
                )
                .first()
            )

            if existing_checkin is not None:
                raise TicketRefundError(
                    "A ticket already has check-in history "
                    "and cannot be refunded."
                )

        # ====================================================
        # BLOCK PREVIOUS REFUNDS
        # ========================================================
        #
        # A selected ticket must not appear in an active
        # or successfully completed refund.
        #
        # Failed and cancelled refunds are excluded,
        # provided their final provider status has been
        # independently verified.
        # ====================================================

        previous_refund = (
            db.session.query(
                TicketRefundItem.entry_pass_id
            )
            .join(
                TicketRefund,
                TicketRefund.id
                == TicketRefundItem.refund_id,
            )
            .filter(
                TicketRefund.order_id == order.id,
                TicketRefundItem.entry_pass_id.in_(ids),
                TicketRefund.status.in_(
                    (
                        "requested",
                        "submitted",
                        "pending",
                        "processing",
                        "succeeded",
                    )
                ),
            )
            .first()
        )

        if previous_refund is not None:
            raise TicketRefundError(
                "One or more selected tickets already "
                "have a refund request."
            )

        # ====================================================
        # DETERMINE TICKET PRICES
        # ========================================================

        order_items = list(
            order.order_items
        )

        legacy_order = not bool(order_items)

        items_by_id = {
            item.id: item
            for item in order_items
        }

        refund_lines = []

        for entry_pass in passes:

            if legacy_order:

                if entry_pass.order_item_id is not None:
                    raise TicketRefundError(
                        "Unexpected ticket line on "
                        "a legacy order."
                    )

                unit_price = order.ticket_price

            else:

                order_item = items_by_id.get(
                    entry_pass.order_item_id
                )

                if order_item is None:
                    raise TicketRefundError(
                        "Ticket line association is missing."
                    )

                unit_price = order_item.unit_price

            amount = _money(
                unit_price
            )

            if amount <= Decimal("0.00"):
                raise TicketRefundError(
                    "Zero-price tickets require a "
                    "separate cancellation workflow."
                )

            refund_lines.append(
                (
                    entry_pass.id,
                    entry_pass.order_item_id,
                    amount,
                )
            )

        # ====================================================
        # CALCULATE FACE-VALUE REFUND
        # ========================================================

        face_value = sum(
            (
                line[2]
                for line in refund_lines
            ),
            Decimal("0.00"),
        )

        face_value = _money(
            face_value
        )

        original_face_value = _money(
            order.total_amount
        )

        already_refunded = _money(
            order.refunded_face_value or 0
        )

        remaining_face_value = (
            original_face_value
            - already_refunded
        )

        if face_value > remaining_face_value:
            raise TicketRefundError(
                "Refund exceeds the remaining "
                "ticket face value."
            )

        checkout_value = _money(
            order.checkout_amount
            if order.checkout_amount is not None
            else original_face_value
        )

        if face_value > checkout_value:
            raise TicketRefundError(
                "Refund exceeds the original "
                "checkout amount."
            )

        # ====================================================
        # CAPTURE PAYSTACK DETAILS BEFORE COMMIT
        # ========================================================

        paystack_transaction_id = str(
            order.paystack_transaction_id
        ).strip()

        # ====================================================
        # CREATE REFUND RESERVATION
        # ========================================================

        refund_reference = (
            "KXRF-"
            + uuid4().hex.upper()
        )

        refund = TicketRefund(
            order_id=order.id,
            refund_reference=refund_reference,
            paystack_transaction_id=paystack_transaction_id,
            face_value_amount=face_value,
            provider_refund_amount=face_value,
            status="requested",
            requested_by=requested_by,
            reason=reason,
        )

        db.session.add(
            refund
        )

        db.session.flush()

        refund_id = refund.id

        # ====================================================
        # RESERVE SELECTED PASSES
        # ========================================================

        for (
            entry_pass_id,
            order_item_id,
            amount,
        ) in refund_lines:

            refund_item = TicketRefundItem(
                refund_id=refund_id,
                order_item_id=order_item_id,
                entry_pass_id=entry_pass_id,
                quantity=1,
                face_value_amount=amount,
            )

            db.session.add(
                refund_item
            )

        # ====================================================
        # MARK ORDER REFUND STATUS
        # ========================================================

        order.refund_status = "pending"

        # ====================================================
        # COMMIT RESERVATION
        # ========================================================

        db.session.commit()

    except Exception:

        db.session.rollback()

        raise

    # ========================================================
    # 6. SUBMIT REFUND TO PAYSTACK
    # ========================================================
    #
    # The database reservation is now durable.
    #
    # Do not hold PostgreSQL locks during the
    # external Paystack API request.
    #
    # Do not automatically retry this POST.
    # ========================================================

    try:

        refund_payload = {
            "transaction": paystack_transaction_id,
            "amount": _cents(face_value),
            "merchant_note": (
                "KALXA ticket refund "
                + refund_reference
            ),
        }

        response = paystack_api_request(
            "POST",
            "/refund",
            json=refund_payload,
        )

        # ====================================================
        # VERIFY PAYSTACK API RESPONSE
        # ========================================================

        if (
            not isinstance(response, dict)
            or response.get("status") is not True
        ):
            raise TicketRefundError(
                "Paystack did not confirm refund "
                "request acceptance."
            )

        data = response.get(
            "data"
        )

        if not isinstance(data, dict):
            raise TicketRefundError(
                "Paystack returned invalid refund data."
            )

        provider_id = _refund_provider_id(
            data
        )

        # ====================================================
        # VERIFY ORIGINAL TRANSACTION
        # ========================================================

        provider_transaction = data.get(
            "transaction"
        )

        if isinstance(provider_transaction, dict):

            provider_transaction = (
                provider_transaction.get("id")
            )

        if (
            provider_transaction is not None
            and str(provider_transaction)
            != paystack_transaction_id
        ):
            raise TicketRefundError(
                "Paystack refund transaction mismatch."
            )

        # ====================================================
        # VERIFY REFUND AMOUNT
        # ========================================================

        provider_amount = data.get(
            "amount"
        )

        if (
            isinstance(provider_amount, bool)
            or not isinstance(provider_amount, int)
            or provider_amount != _cents(face_value)
        ):
            raise TicketRefundError(
                "Paystack refund amount mismatch."
            )

    except Exception:

        # ====================================================
        # UNKNOWN PROVIDER STATE
        # ========================================================
        #
        # The request may already have reached Paystack.
        #
        # Keep the reservation in requested state.
        #
        # Never submit another refund automatically.
        # ========================================================

        current_app.logger.exception(
            (
                "[Ticket Refund] "
                "Paystack submission uncertain "
                "refund_id=%s order_id=%s "
                "reference=%s"
            ),
            refund_id,
            order_id,
            refund_reference,
        )

        raise

    # ========================================================
    # 7. RECORD PAYSTACK REFUND ACCEPTANCE
    # ========================================================

    try:

        refund = (
            db.session.query(TicketRefund)
            .filter(
                TicketRefund.id == refund_id
            )
            .populate_existing()
            .with_for_update()
            .one()
        )

        # ====================================================
        # HANDLE EARLY WEBHOOK RECONCILIATION
        # ========================================================
        #
        # A webhook may have already updated the refund
        # while this request was awaiting Paystack.
        #
        # Do not downgrade a terminal or more advanced
        # refund status.
        # ========================================================

        if (
            refund.paystack_refund_id is not None
            and str(refund.paystack_refund_id)
            != str(provider_id)
        ):
            raise TicketRefundError(
                "Refund is linked to a different "
                "Paystack refund ID."
            )

        if refund.paystack_refund_id is None:
            refund.paystack_refund_id = str(
                provider_id
            )

        if refund.submitted_at is None:
            refund.submitted_at = datetime.utcnow()

        if refund.status == "requested":
            refund.status = "pending"

        db.session.commit()

        current_app.logger.info(
            (
                "[Ticket Refund] "
                "Paystack refund request accepted "
                "refund_id=%s order_id=%s "
                "provider_id=%s status=%s"
            ),
            refund_id,
            order_id,
            provider_id,
            refund.status,
        )

        return refund

    except Exception:

        db.session.rollback()

        current_app.logger.exception(
            (
                "[Ticket Refund] "
                "Failed to record Paystack acceptance "
                "refund_id=%s order_id=%s"
            ),
            refund_id,
            order_id,
        )

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
