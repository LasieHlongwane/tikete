"""
KALXA Stage 6A — Paystack Settlement Reconciliation.

Read-only against Paystack.

Writes:
    PaystackSettlement
    TicketSettlementAllocation
    TicketOrder settlement reconciliation fields

Does NOT:
    - Pay organisers
    - Initiate transfers
    - Issue refunds
    - Change ticket commission
    - Modify ticket payment status

TEST MODE ONLY.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import quote


CENT = Decimal("0.01")


class SettlementReconciliationError(RuntimeError):
    pass


# ============================================================
# MONEY HELPERS
# ============================================================

def _cents(value, label):

    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
    ):
        raise SettlementReconciliationError(
            f"Invalid {label}: expected non-negative integer cents."
        )

    return value


def _money(cents):

    return (
        Decimal(cents) / Decimal("100")
    ).quantize(CENT)


def _db_cents(value, label):

    if value is None:
        raise SettlementReconciliationError(
            f"Missing {label}."
        )

    try:
        decimal = Decimal(str(value))
    except Exception as error:
        raise SettlementReconciliationError(
            f"Invalid {label}."
        ) from error

    if (
        not decimal.is_finite()
        or decimal < 0
        or decimal * 100 != (decimal * 100).to_integral_value()
    ):
        raise SettlementReconciliationError(
            f"Invalid {label}."
        )

    return int(decimal * 100)


def _utc_naive(value):

    if not isinstance(value, str) or not value.strip():
        return None

    try:
        parsed = datetime.fromisoformat(
            value.strip().replace("Z", "+00:00")
        )

        if parsed.tzinfo is None:
            return None

        return (
            parsed.astimezone(timezone.utc)
            .replace(tzinfo=None)
        )

    except ValueError:
        return None


# ============================================================
# PAYSTACK PAGINATION
# ============================================================

def _pages(
    api_request,
    path,
    *,
    per_page=50,
    max_pages=20,
):

    if not 1 <= per_page <= 100:
        raise ValueError("Invalid per_page.")

    if not 1 <= max_pages <= 100:
        raise ValueError("Invalid max_pages.")

    all_rows = []
    expected_total = None

    for page in range(1, max_pages + 1):

        separator = "&" if "?" in path else "?"

        response = api_request(
            "GET",
            (
                f"{path}{separator}"
                f"page={page}&perPage={per_page}"
            ),
        )

        if (
            not isinstance(response, dict)
            or response.get("status") is not True
        ):
            raise SettlementReconciliationError(
                "Paystack listing request failed."
            )

        rows = response.get("data")
        meta = response.get("meta")

        if not isinstance(rows, list):
            raise SettlementReconciliationError(
                "Invalid Paystack listing data."
            )

        if not isinstance(meta, dict):
            raise SettlementReconciliationError(
                "Missing pagination metadata."
            )

        if any(not isinstance(row, dict) for row in rows):
            raise SettlementReconciliationError(
                "Malformed Paystack listing entry."
            )

        page_count = meta.get("pageCount")
        current_page = meta.get("page")
        total = meta.get("total")

        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            for value in (
                page_count,
                current_page,
                total,
            )
        ):
            raise SettlementReconciliationError(
                "Invalid pagination metadata."
            )

        if (
            current_page != page
            or page_count < 1
            or total < 0
        ):
            raise SettlementReconciliationError(
                "Inconsistent pagination metadata."
            )

        if expected_total is None:
            expected_total = total

        elif total != expected_total:
            raise SettlementReconciliationError(
                "Paystack listing changed during pagination."
            )

        all_rows.extend(rows)

        if page >= page_count:

            if len(all_rows) != expected_total:
                raise SettlementReconciliationError(
                    "Incomplete Paystack listing."
                )

            return all_rows

    raise SettlementReconciliationError(
        "Pagination limit reached."
    )


# ============================================================
# VALIDATE SETTLEMENT HEADER
# ============================================================

def _settlement_header(raw):

    settlement_id = raw.get("id")

    if (
        isinstance(settlement_id, bool)
        or not isinstance(settlement_id, (int, str))
        or not str(settlement_id).strip()
    ):
        raise SettlementReconciliationError(
            "Settlement ID missing."
        )

    if raw.get("currency") != "ZAR":
        raise SettlementReconciliationError(
            "Settlement currency is not ZAR."
        )

    gross = _cents(
        raw.get("total_processed"),
        "settlement total_processed",
    )

    fees = _cents(
        raw.get("total_fees"),
        "settlement total_fees",
    )

    net = _cents(
        raw.get("total_amount"),
        "settlement total_amount",
    )

    effective = _cents(
        raw.get("effective_amount"),
        "settlement effective_amount",
    )

    if (
        gross - fees != net
        or effective != net
        or raw.get("deductions") not in (
            None,
            [],
            {},
            0,
        )
    ):
        raise SettlementReconciliationError(
            "Settlement contains adjustments or deductions "
            "requiring manual review."
        )

    return (
        str(settlement_id).strip(),
        gross,
        fees,
        net,
    )


# ============================================================
# VALIDATE SETTLEMENT TRANSACTION
# ============================================================

def _transaction_row(raw):

    reference = raw.get("reference")
    transaction_id = raw.get("id")

    if (
        not isinstance(reference, str)
        or not reference.strip()
    ):
        raise SettlementReconciliationError(
            "Transaction reference missing."
        )

    if (
        isinstance(transaction_id, bool)
        or not isinstance(transaction_id, (int, str))
        or not str(transaction_id).strip()
    ):
        raise SettlementReconciliationError(
            "Transaction ID missing."
        )

    if (
        raw.get("status") != "success"
        or raw.get("currency") != "ZAR"
    ):
        raise SettlementReconciliationError(
            "Transaction status or currency mismatch."
        )

    amount = _cents(
        raw.get("amount"),
        "transaction amount",
    )

    fee = _cents(
        raw.get("fees"),
        "transaction Paystack fee",
    )

    if fee > amount:
        raise SettlementReconciliationError(
            "Transaction fee exceeds payment amount."
        )

    return (
        reference.strip(),
        str(transaction_id).strip(),
        amount,
        fee,
    )


# ============================================================
# MAIN RECONCILIATION SERVICE
# ============================================================

def reconcile_paystack_settlements(
    *,
    api_request,
    db,
    TicketOrder,
    PaystackSettlement,
    TicketSettlementAllocation,
    per_page=50,
    max_pages=20,
    max_settlements=20,
    allow_live=False,
):

    if allow_live:
        raise SettlementReconciliationError(
            "Live reconciliation is disabled."
        )

    if not 1 <= max_settlements <= 100:
        raise ValueError(
            "max_settlements must be between 1 and 100."
        )

    summaries = _pages(
        api_request,
        "/settlement?subaccount=none",
        per_page=per_page,
        max_pages=max_pages,
    )

    report = {
        "discovered": 0,
        "reconciled": 0,
        "pending": 0,
        "exceptions": 0,
        "details": [],
    }

    for raw in summaries[:max_settlements]:

        sid = raw.get("id")

        sid_text = (
            str(sid)
            if isinstance(sid, (int, str))
            and not isinstance(sid, bool)
            else "invalid"
        )

        try:

            # =================================================
            # TEST MODE CHECK
            # =================================================

            if raw.get("domain") != "test":
                raise SettlementReconciliationError(
                    "Only test-mode settlements are supported."
                )

            settlement_id, gross, fees, net = (
                _settlement_header(raw)
            )

            state = raw.get("status")

            if state not in {
                "success",
                "processing",
                "pending",
                "failed",
            }:
                raise SettlementReconciliationError(
                    "Unknown settlement status."
                )

            # =================================================
            # GET OR CREATE LOCAL SETTLEMENT
            # =================================================

            record = (
                db.session.query(PaystackSettlement)
                .filter_by(
                    paystack_settlement_id=settlement_id
                )
                .with_for_update()
                .one_or_none()
            )

            if record is None:

                record = PaystackSettlement(
                    paystack_settlement_id=settlement_id
                )

                db.session.add(record)
                db.session.flush()

                report["discovered"] += 1

            # A previously reconciled record is immutable
            # except through a separately reviewed correction.
            if record.status == "reconciled":
               # raise SettlementReconciliationError(
                #    "Settlement was already reconciled; "
               #     "existing records are not modified."
               # )
                continue

            record.currency = "ZAR"
            record.gross_amount = _money(gross)
            record.processing_fees = _money(fees)
            record.net_amount = _money(net)

            record.destination_type = "platform"

            # Do not infer the actual bank destination.
            record.destination_reference = None

            record.settlement_date = _utc_naive(
                raw.get("settlement_date")
            )

            # =================================================
            # INCOMPLETE SETTLEMENT
            # =================================================

            if state != "success":

                record.status = (
                    "exception"
                    if state == "failed"
                    else "pending"
                )

                db.session.commit()

                if state == "failed":
                    report["exceptions"] += 1

                    report["details"].append({
                        "settlement_id": settlement_id,
                        "reason": "Paystack settlement failed.",
                    })

                else:
                    report["pending"] += 1

                continue

            # =================================================
            # FETCH SETTLEMENT TRANSACTIONS
            # =================================================

            transactions = _pages(
                api_request,
                (
                    "/settlement/"
                    + quote(settlement_id, safe="")
                    + "/transactions"
                ),
                per_page=per_page,
                max_pages=max_pages,
            )

            if not transactions:
                raise SettlementReconciliationError(
                    "Successful settlement has no transactions."
                )

            seen_refs = set()
            seen_ids = set()
            allocations = []

            sum_amount = 0
            sum_fees = 0

            # =================================================
            # MATCH TRANSACTIONS TO TICKET ORDERS
            # =================================================

            for transaction in transactions:

                reference, txn_id, amount, fee = (
                    _transaction_row(transaction)
                )

                if (
                    reference in seen_refs
                    or txn_id in seen_ids
                ):
                    raise SettlementReconciliationError(
                        "Duplicate transaction in settlement."
                    )

                seen_refs.add(reference)
                seen_ids.add(txn_id)

                order = (
                    db.session.query(TicketOrder)
                    .filter_by(
                        payment_reference=reference
                    )
                    .one_or_none()
                )

                if order is None:
                    raise SettlementReconciliationError(
                        "Settlement contains unknown or "
                        "non-ticket transactions."
                    )

                if (
                    order.payment_status != "paid"
                    or order.payment_provider != "paystack"
                ):
                    raise SettlementReconciliationError(
                        "Matched order is not a paid Paystack order."
                    )

                if (
                    str(
                        order.paystack_transaction_id or ""
                    ).strip()
                    != txn_id
                ):
                    raise SettlementReconciliationError(
                        "Paystack transaction ID mismatch."
                    )

                expected = (
                    order.checkout_amount
                    if order.checkout_amount is not None
                    else order.total_amount
                )

                if (
                    _db_cents(
                        expected,
                        "order checkout amount",
                    )
                    != amount
                ):
                    raise SettlementReconciliationError(
                        "Transaction amount mismatch."
                    )

                if (
                    order.commission_recorded_at is None
                    or order.commission_amount is None
                    or order.organizer_gross_share is None
                ):
                    raise SettlementReconciliationError(
                        "Order commission accounting is incomplete."
                    )

                # Reject duplicate settlement attribution.
                other = (
                    db.session.query(
                        TicketSettlementAllocation
                    )
                    .filter(
                        TicketSettlementAllocation.order_id
                        == order.id,

                        TicketSettlementAllocation.settlement_id
                        != record.id,
                    )
                    .first()
                )

                if other is not None:
                    raise SettlementReconciliationError(
                        "Order is allocated to another settlement."
                    )

                sum_amount += amount
                sum_fees += fee

                allocations.append(
                    (order, amount, fee)
                )

            # =================================================
            # VALIDATE SETTLEMENT TOTALS
            # =================================================

            if (
                sum_amount != gross
                or sum_fees != fees
                or sum_amount - sum_fees != net
            ):
                raise SettlementReconciliationError(
                    "Settlement totals do not match transactions."
                )

            # =================================================
            # VALIDATE EXISTING ALLOCATIONS
            # =================================================

            existing = (
                db.session.query(TicketSettlementAllocation)
                .filter_by(settlement_id=record.id)
                .all()
            )

            expected_by_order = {
                order.id: (amount, fee)
                for order, amount, fee in allocations
            }

            for allocation in existing:

                pair = expected_by_order.get(
                    allocation.order_id
                )

                if pair is None:
                    raise SettlementReconciliationError(
                        "Unexpected existing allocation."
                    )

                if (
                    _db_cents(
                        allocation.transaction_amount,
                        "allocation amount",
                    ) != pair[0]

                    or _db_cents(
                        allocation.processing_fee,
                        "allocation fee",
                    ) != pair[1]

                    or _db_cents(
                        allocation.net_settlement_amount,
                        "allocation net",
                    ) != pair[0] - pair[1]
                ):
                    raise SettlementReconciliationError(
                        "Existing allocation conflicts with Paystack."
                    )

            existing_order_ids = {
                allocation.order_id
                for allocation in existing
            }

            # =================================================
            # CREATE ALLOCATIONS
            # =================================================

            for order, amount, fee in allocations:

                if order.id not in existing_order_ids:

                    db.session.add(
                        TicketSettlementAllocation(
                            settlement_id=record.id,
                            order_id=order.id,
                            transaction_amount=_money(amount),
                            processing_fee=_money(fee),
                            net_settlement_amount=_money(
                                amount - fee
                            ),
                        )
                    )

                order.settlement_status = "reconciled"
                order.settlement_reconciled_at = (
                    datetime.utcnow()
                )

            # =================================================
            # FINALISE LOCAL RECONCILIATION
            # =================================================

            record.status = "reconciled"
            record.reconciled_at = datetime.utcnow()

            db.session.commit()

            report["reconciled"] += 1

        except Exception as error:

            db.session.rollback()

            report["exceptions"] += 1

            reason = (
                str(error)
                if isinstance(
                    error,
                    SettlementReconciliationError,
                )
                else "Unexpected reconciliation error."
            )

            # Do not overwrite a previously reconciled
            # settlement following a later failure.
            try:

                record = (
                    db.session.query(PaystackSettlement)
                    .filter_by(
                        paystack_settlement_id=sid_text
                    )
                    .first()
                )

                if (
                    record is not None
                    and record.status != "reconciled"
                ):
                    record.status = "exception"
                    db.session.commit()

            except Exception:
                db.session.rollback()

            report["details"].append({
                "settlement_id": sid_text,
                "reason": reason,
            })

    return report
