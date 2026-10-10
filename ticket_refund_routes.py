# ============================================================
# KALXA TICKETING
# SUPER-ADMIN TICKET REFUND ROUTES
# ============================================================

import hmac
import secrets

from urllib.parse import urlsplit

from flask import (
    abort,
    current_app,
    jsonify,
    request,
    session,
)

from services.ticket_refunds import (
    TicketRefundError,
    initiate_ticket_refund,
    reconcile_ticket_refund,
)


# ============================================================
# REGISTER REFUND ROUTES
# ============================================================

def register_ticket_refund_routes(
    app,
    *,
    db,
    TicketOrder,
    TicketOrderItem,
    TicketRefund,
    TicketRefundItem,
    EntryPass,
    paystack_api_request,
    superadmin_guard,
):
    """
    Register protected KALXA ticket refund endpoints.

    Required:
        - Existing Flask application
        - SQLAlchemy database
        - Ticket models
        - Paystack API helper
        - Authenticated super-admin guard

    The superadmin_guard must return:
        - Administrator identity if authenticated
        - None if not authenticated

    Never trust administrator identity supplied
    through request JSON or URL parameters.
    """

    if not callable(superadmin_guard):
        raise ValueError(
            "A verified super-admin guard is required."
        )

    # ========================================================
    # SUPER-ADMIN AUTHENTICATION
    # ========================================================

    def admin_identity():

        identity = superadmin_guard()

        if not identity:
            abort(403)

        return str(identity)

    # ========================================================
    # CSRF PROTECTION
    # ========================================================

    def require_csrf():
        """
        Protect refund administration endpoints
        against cross-site request forgery.
        """

        expected = session.get(
            "kalxa_refund_csrf_token"
        )

        supplied = request.headers.get(
            "X-CSRF-Token",
            "",
        )

        if (
            not isinstance(expected, str)
            or not expected
            or not isinstance(supplied, str)
            or not supplied
            or not hmac.compare_digest(
                expected,
                supplied,
            )
        ):
            abort(
                403,
                description="Invalid refund CSRF token.",
            )

        # ====================================================
        # VERIFY REQUEST ORIGIN
        # ====================================================

        origin = request.headers.get(
            "Origin"
        )

        if origin:

            parsed = urlsplit(origin)

            if (
                parsed.scheme != "https"
                or parsed.netloc != request.host
            ):
                abort(
                    403,
                    description="Invalid refund request origin.",
                )

    # ========================================================
    # 1. GENERATE SUPER-ADMIN REFUND CSRF TOKEN
    # ========================================================

    @app.get("/admin/ticket-refunds/csrf")
    def kalxa_refund_csrf():
        """
        Return a CSRF token for authenticated
        super-admin refund operations.
        """

        admin_identity()

        token = session.get(
            "kalxa_refund_csrf_token"
        )

        if not token:

            token = secrets.token_urlsafe(32)

            session[
                "kalxa_refund_csrf_token"
            ] = token

        response = jsonify({
            "csrf_token": token,
        })

        response.headers[
            "Cache-Control"
        ] = "no-store"

        return response

    # ========================================================
    # 2. INITIATE TICKET REFUND
    # ========================================================

    @app.post("/admin/ticket-refunds")
    def kalxa_initiate_ticket_refund():
        """
        Initiate a refund for selected unused tickets.

        Only authenticated super-admins may
        initiate refunds.

        The refund service must:
            - Lock the ticket order.
            - Lock selected entry passes.
            - Verify payment.
            - Reject used tickets.
            - Reject overlapping refunds.
            - Reserve the refund in PostgreSQL.
            - Commit before contacting Paystack.
            - Avoid automatically retrying uncertain
              Paystack refund submissions.

        Commission reversal happens only after
        successful refund reconciliation.
        """

        # ====================================================
        # AUTHENTICATE SUPER-ADMIN
        # ====================================================

        admin = admin_identity()

        # ====================================================
        # VERIFY CSRF
        # ====================================================

        require_csrf()

        # ====================================================
        # REQUIRE JSON
        # ====================================================

        if not request.is_json:

            return jsonify({
                "success": False,
                "error": (
                    "Content-Type must be application/json."
                ),
            }), 415

        data = request.get_json(
            silent=True
        )

        if not isinstance(data, dict):

            return jsonify({
                "success": False,
                "error": "A valid JSON object is required.",
            }), 400

        # ====================================================
        # EXTRACT REQUEST DATA
        # ====================================================

        order_id = data.get(
            "order_id"
        )

        entry_pass_ids = data.get(
            "entry_pass_ids"
        )

        reason = data.get(
            "reason"
        )

        # ====================================================
        # VALIDATE ORDER ID
        # ====================================================

        if (
            isinstance(order_id, bool)
            or not isinstance(order_id, int)
            or order_id <= 0
        ):

            return jsonify({
                "success": False,
                "error": "A valid order_id is required.",
            }), 400

        # ====================================================
        # VALIDATE ENTRY-PASS LIST
        # ====================================================

        if (
            not isinstance(entry_pass_ids, list)
            or not entry_pass_ids
        ):

            return jsonify({
                "success": False,
                "error": (
                    "entry_pass_ids must be a non-empty "
                    "list of ticket identifiers."
                ),
            }), 400

        # ====================================================
        # LIMIT BULK REFUNDS
        # ====================================================

        MAX_REFUND_PASSES = 100

        if len(entry_pass_ids) > MAX_REFUND_PASSES:

            return jsonify({
                "success": False,
                "error": (
                    "A maximum of 100 tickets can be "
                    "selected per refund request."
                ),
            }), 400

        # ====================================================
        # VALIDATE EACH ENTRY-PASS ID
        # ====================================================

        if any(
            isinstance(pass_id, bool)
            or not isinstance(pass_id, int)
            or pass_id <= 0
            for pass_id in entry_pass_ids
        ):

            return jsonify({
                "success": False,
                "error": (
                    "Every entry_pass_id must be "
                    "a positive integer."
                ),
            }), 400

        # ====================================================
        # REJECT DUPLICATE ENTRY-PASS IDS
        # ====================================================

        if len(entry_pass_ids) != len(
            set(entry_pass_ids)
        ):

            return jsonify({
                "success": False,
                "error": (
                    "Duplicate entry-pass IDs "
                    "are not allowed."
                ),
            }), 400

        entry_pass_ids = sorted(
            entry_pass_ids
        )

        # ====================================================
        # VALIDATE REFUND REASON
        # ====================================================

        if reason is not None:

            if (
                not isinstance(reason, str)
                or len(reason) > 2000
            ):

                return jsonify({
                    "success": False,
                    "error": "Invalid refund reason.",
                }), 400

            reason = reason.strip() or None

        # ====================================================
        # INITIATE REFUND
        # ====================================================

        try:

            refund = initiate_ticket_refund(
                order_id=order_id,
                entry_pass_ids=entry_pass_ids,
                requested_by=admin,
                reason=reason,
                db=db,
                TicketOrder=TicketOrder,
                TicketRefund=TicketRefund,
                TicketRefundItem=TicketRefundItem,
                EntryPass=EntryPass,
                paystack_api_request=paystack_api_request,
            )

            if refund is None:

                raise RuntimeError(
                    "Refund service returned no record."
                )

            refund_id = refund.id

            refund_status = refund.status

            refund_reference = refund.refund_reference

            # ================================================
            # AUDIT LOG
            # ================================================

            current_app.logger.info(
                (
                    "[Ticket Refund] "
                    "Refund request recorded "
                    "refund_id=%s order_id=%s "
                    "status=%s admin=%s "
                    "pass_count=%s"
                ),
                refund_id,
                order_id,
                refund_status,
                admin,
                len(entry_pass_ids),
            )

            # ================================================
            # RESPONSE
            # ================================================

            return jsonify({
                "success": True,
                "message": (
                    "Refund request recorded. "
                    "Paystack refund completion "
                    "has not yet been confirmed."
                ),
                "refund_id": refund_id,
                "order_id": order_id,
                "status": refund_status,
                "reference": refund_reference,
                "entry_pass_ids": entry_pass_ids,
                "requires_reconciliation": True,
            }), 202

        # ====================================================
        # KNOWN REFUND ERRORS
        # ====================================================

        except TicketRefundError as exc:

            db.session.rollback()

            current_app.logger.warning(
                (
                    "[Ticket Refund] "
                    "Refund initiation rejected "
                    "order_id=%s admin=%s reason=%s"
                ),
                order_id,
                admin,
                str(exc),
            )

            return jsonify({
                "success": False,
                "error": str(exc),
            }), 409

        # ====================================================
        # UNEXPECTED ERRORS
        # ====================================================

        except Exception:

            db.session.rollback()

            current_app.logger.exception(
                (
                    "[Ticket Refund] "
                    "Refund initiation failed "
                    "order_id=%s admin=%s"
                ),
                order_id,
                admin,
            )

            return jsonify({
                "success": False,
                "error": (
                    "Refund state may be uncertain. "
                    "Investigate the existing refund "
                    "record and Paystack before retrying."
                ),
            }), 503

    # ========================================================
    # 3. RECONCILE TICKET REFUND
    # ========================================================

    @app.post(
        "/admin/ticket-refunds/<int:refund_id>/reconcile"
    )
    def kalxa_reconcile_ticket_refund(refund_id):
        """
        Independently verify a refund with Paystack.

        When Paystack confirms successful completion,
        the reconciliation service applies:

            - EntryPass.status = refunded
            - Refunded face-value accounting
            - KALXA 4% commission reversal
            - Updated refund status

        All accounting changes must occur atomically.
        """

        # ====================================================
        # AUTHENTICATE SUPER-ADMIN
        # ====================================================

        admin_identity()

        # ====================================================
        # VERIFY CSRF
        # ====================================================

        require_csrf()

        # ====================================================
        # RECONCILE
        # ====================================================

        try:

            refund = reconcile_ticket_refund(
                refund_id=refund_id,
                db=db,
                TicketOrder=TicketOrder,
                TicketOrderItem=TicketOrderItem,
                TicketRefund=TicketRefund,
                TicketRefundItem=TicketRefundItem,
                EntryPass=EntryPass,
                paystack_api_request=paystack_api_request,
            )

            current_app.logger.info(
                (
                    "[Ticket Refund] "
                    "Refund reconciliation completed "
                    "refund_id=%s status=%s"
                ),
                refund.id,
                refund.status,
            )

            return jsonify({
                "success": True,
                "refund_id": refund.id,
                "status": refund.status,
                "accounting_applied": (
                    refund.accounting_applied_at
                    is not None
                ),
            }), 200

        except TicketRefundError as exc:

            db.session.rollback()

            return jsonify({
                "success": False,
                "error": str(exc),
            }), 409

        except Exception:

            db.session.rollback()

            current_app.logger.exception(
                (
                    "[Ticket Refund] "
                    "Reconciliation failed "
                    "refund_id=%s"
                ),
                refund_id,
            )

            return jsonify({
                "success": False,
                "error": (
                    "Refund reconciliation failed. "
                    "Manual review is required."
                ),
            }), 503


# ============================================================
# 4. PAYSTACK REFUND WEBHOOK DISPATCHER
# ============================================================

def handle_ticket_refund_webhook(
    payload,
    *,
    db,
    TicketOrder,
    TicketOrderItem,
    TicketRefund,
    TicketRefundItem,
    EntryPass,
    paystack_api_request,
):
    """
    Handle Paystack ticket refund notifications.

    IMPORTANT:

    This function must be called only AFTER
    the main Paystack webhook verifies the
    HMAC-SHA512 signature.

    Never trust webhook data alone to
    update ticket refund accounting.

    Always independently verify the refund
    through Paystack before reconciliation.

    Returns:
        True  - Recognized refund event.
        False - Not a refund event.
    """

    if not isinstance(payload, dict):
        return False

    # ========================================================
    # IDENTIFY WEBHOOK EVENT
    # ========================================================

    event = payload.get(
        "event"
    )

    refund_events = {
        "refund.pending",
        "refund.processing",
        "refund.processed",
        "refund.failed",
        "refund.needs-attention",
    }

    if event not in refund_events:
        return False

    # ========================================================
    # EXTRACT REFUND DATA
    # ========================================================

    data = payload.get(
        "data"
    )

    if not isinstance(data, dict):

        current_app.logger.error(
            "[Refund Webhook] Malformed event=%s",
            event,
        )

        return True

    # ========================================================
    # EXTRACT PAYSTACK REFUND ID
    # ========================================================

    provider_id = data.get(
        "id"
    )

    if (
        isinstance(provider_id, bool)
        or not isinstance(provider_id, (str, int))
        or not str(provider_id).strip()
    ):

        current_app.logger.warning(
            (
                "[Refund Webhook] "
                "Refund event missing provider ID "
                "event=%s transaction_reference=%s"
            ),
            event,
            data.get("transaction_reference"),
        )

        # Do not guess which partial refund belongs
        # to the Paystack transaction.
        #
        # Manual or scheduled reconciliation required.

        return True

    provider_id = str(
        provider_id
    ).strip()

    # ========================================================
    # FIND LOCAL REFUND
    # ========================================================

    refund = (
        db.session.query(TicketRefund)
        .filter(
            TicketRefund.paystack_refund_id
            == provider_id
        )
        .one_or_none()
    )

    if refund is None:

        current_app.logger.warning(
            (
                "[Refund Webhook] "
                "Unknown refund provider_id=%s "
                "event=%s. Manual review required."
            ),
            provider_id,
            event,
        )

        return True

    refund_id = refund.id

    # ========================================================
    # INDEPENDENT PAYSTACK RECONCILIATION
    # ========================================================

    try:

        reconciled_refund = reconcile_ticket_refund(
            refund_id=refund_id,
            db=db,
            TicketOrder=TicketOrder,
            TicketOrderItem=TicketOrderItem,
            TicketRefund=TicketRefund,
            TicketRefundItem=TicketRefundItem,
            EntryPass=EntryPass,
            paystack_api_request=paystack_api_request,
        )

        current_app.logger.info(
            (
                "[Refund Webhook] "
                "Refund reconciled "
                "refund_id=%s event=%s status=%s"
            ),
            refund_id,
            event,
            reconciled_refund.status,
        )

    except Exception:

        db.session.rollback()

        current_app.logger.exception(
            (
                "[Refund Webhook] "
                "Reconciliation failed "
                "refund_id=%s event=%s"
            ),
            refund_id,
            event,
        )

        raise

    return True
