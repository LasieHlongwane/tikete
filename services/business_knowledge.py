
import hashlib
import logging
import os
import re

from openai import OpenAI
from sqlalchemy import text

from models import db, RestaurantExperiencePost


logger = logging.getLogger("kalxa.business_knowledge")


# ============================================================
# CONFIGURATION
# ============================================================

EMBEDDING_MODEL = "text-embedding-3-small"

EMBEDDING_DIMENSIONS = 1536

CHUNK_SIZE = 1000

CHUNK_OVERLAP = 120

EMBEDDING_BATCH_SIZE = 64


# ============================================================
# OPENAI CLIENT
# ============================================================

def get_openai_client():
    """
    Create an OpenAI client using the Render environment variable.
    """

    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured."
        )

    return OpenAI(api_key=api_key)


# ============================================================
# CONTENT CLEANING
# ============================================================

def clean_text(value):
    """
    Normalize text before adding it to the knowledge base.
    """

    if value is None:
        return ""

    value = str(value)

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def looks_like_developer_content(value):
    """
    Avoid indexing obvious development instructions accidentally
    pasted into a public business profile.

    This is deliberately conservative.
    """

    value = clean_text(value).lower()

    suspicious_phrases = [
        "i'm keeping your existing backend route names",
        "dedicated subscription navigation link",
        "fixed desktop sidebar",
        "slide-out mobile sidebar",
        "url_for('home')",
        "developer instructions",
        "here is the updated code",
    ]

    return any(
        phrase in value
        for phrase in suspicious_phrases
    )


# ============================================================
# TEXT CHUNKING
# ============================================================

def split_into_chunks(
    content,
    chunk_size=CHUNK_SIZE,
    overlap=CHUNK_OVERLAP,
):
    """
    Split long content into overlapping chunks.

    Short content remains a single chunk.
    """

    content = clean_text(content)

    if not content:
        return []

    if len(content) <= chunk_size:
        return [content]

    chunks = []

    start = 0

    while start < len(content):

        end = start + chunk_size

        chunk = content[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(content):
            break

        start = end - overlap

    return chunks


# ============================================================
# CONTENT HASH
# ============================================================

def generate_content_hash(
    source_type,
    source_reference,
    content,
):
    """
    Generate a stable SHA-256 hash for a knowledge chunk.
    """

    raw_value = (
        f"{source_type}|"
        f"{source_reference}|"
        f"{content}"
    )

    return hashlib.sha256(
        raw_value.encode("utf-8")
    ).hexdigest()


# ============================================================
# KNOWLEDGE DOCUMENT BUILDER
# ============================================================

def add_knowledge_document(
    documents,
    source_type,
    source_reference,
    content,
):
    """
    Convert one source document into knowledge chunks.
    """

    content = clean_text(content)

    if not content:
        return

    if looks_like_developer_content(content):
        logger.warning(
            "Skipped suspicious knowledge content. "
            "source_type=%s source_reference=%s",
            source_type,
            source_reference,
        )

        return

    chunks = split_into_chunks(content)

    for chunk in chunks:

        content_hash = generate_content_hash(
            source_type,
            source_reference,
            chunk,
        )

        documents.append(
            {
                "source_type": source_type,
                "source_reference": str(source_reference),
                "content": chunk,
                "content_hash": content_hash,
            }
        )


# ============================================================
# RESTAURANT PROFILE KNOWLEDGE
# ============================================================

def collect_restaurant_profile(advert):
    """
    Collect publicly relevant business profile information.
    """

    documents = []

    profile_fields = [
        (
            "Business name",
            advert.business_name,
        ),
        (
            "Business headline",
            advert.headline,
        ),
        (
            "Business description",
            advert.description,
        ),
        (
            "Price information",
            advert.price_text,
        ),
        (
            "Business address",
            advert.address,
        ),
        (
            "Business area",
            advert.area,
        ),
    ]

    profile_lines = []

    for label, value in profile_fields:

        value = clean_text(value)

        if not value:
            continue

        if looks_like_developer_content(value):
            logger.warning(
                "Skipped suspicious profile field. "
                "business_id=%s field=%s",
                advert.id,
                label,
            )

            continue

        profile_lines.append(
            f"{label}: {value}"
        )

    if profile_lines:

        add_knowledge_document(
            documents=documents,
            source_type="restaurant_profile",
            source_reference="profile",
            content="\n".join(profile_lines),
        )

    return documents


# ============================================================
# RESTAURANT OPENING HOURS
# ============================================================

def collect_restaurant_opening_hours(advert):
    """
    Include opening hours only when the existing restaurant
    subscription permits this feature.
    """

    documents = []

    if not advert.can_use_opening_hours:
        return documents

    opening_hours = getattr(
        advert,
        "opening_hours",
        [],
    )

    for hour in opening_hours:

        day = clean_text(
            getattr(hour, "day_of_week", "")
        )

        if not day:
            continue

        if hour.is_closed:

            content = (
                f"Opening hours for {day}: "
                "The business is closed."
            )

        else:

            open_time = getattr(
                hour,
                "open_time_string",
                None,
            )

            close_time = getattr(
                hour,
                "close_time_string",
                None,
            )

            if not open_time or not close_time:
                continue

            content = (
                f"Opening hours for {day}: "
                f"Open from {open_time} "
                f"until {close_time}."
            )

        add_knowledge_document(
            documents=documents,
            source_type="opening_hours",
            source_reference=day,
            content=content,
        )

    return documents


# ============================================================
# APPROVED CUSTOMER EXPERIENCES
# ============================================================

def collect_customer_experiences(advert):
    """
    Include only approved, active customer experiences.

    Customer names and media URLs are deliberately excluded.
    """

    documents = []

    if not advert.can_receive_customer_experiences:
        return documents

    experiences = (
        RestaurantExperiencePost.query

        .filter_by(
            restaurant_advert_id=advert.id,
            active=True,
            moderation_status="approved",
        )

        .order_by(
            RestaurantExperiencePost.created_at.desc()
        )

        .all()
    )

    for experience in experiences:

        experience_text = clean_text(
            experience.experience_text
        )

        if not experience_text:
            continue

        content = (
            "Approved customer experience: "
            f"{experience_text}\n"
            f"Customer rating: {experience.rating} out of 5."
        )

        add_knowledge_document(
            documents=documents,
            source_type="customer_experience",
            source_reference=str(experience.id),
            content=content,
        )

    return documents


# ============================================================
# COLLECT ALL BUSINESS KNOWLEDGE
# ============================================================

def collect_business_knowledge(advert):
    """
    Collect all permitted knowledge sources for one restaurant.
    """

    documents = []

    documents.extend(
        collect_restaurant_profile(advert)
    )

    documents.extend(
        collect_restaurant_opening_hours(advert)
    )

    documents.extend(
        collect_customer_experiences(advert)
    )

    return documents


# ============================================================
# GENERATE EMBEDDINGS
# ============================================================

def generate_embeddings(contents):
    """
    Generate OpenAI embeddings in batches.

    Returns one 1536-dimensional embedding per content item.
    """

    if not contents:
        return []

    client = get_openai_client()

    embeddings = []

    for start in range(
        0,
        len(contents),
        EMBEDDING_BATCH_SIZE,
    ):

        batch = contents[
            start:start + EMBEDDING_BATCH_SIZE
        ]

        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
            dimensions=EMBEDDING_DIMENSIONS,
        )

        batch_embeddings = sorted(
            response.data,
            key=lambda item: item.index,
        )

        for item in batch_embeddings:

            embedding = item.embedding

            if len(embedding) != EMBEDDING_DIMENSIONS:
                raise RuntimeError(
                    "OpenAI returned an unexpected embedding dimension."
                )

            embeddings.append(embedding)

    return embeddings


# ============================================================
# VECTOR SERIALIZATION
# ============================================================

def serialize_embedding(embedding):
    """
    Convert an embedding into PostgreSQL vector input format.
    """

    return (
        "["
        + ",".join(
            str(float(value))
            for value in embedding
        )
        + "]"
    )


# ============================================================
# SAVE BUSINESS KNOWLEDGE
# ============================================================

def save_business_knowledge(
    business_id,
    documents,
):
    """
    Replace the existing knowledge chunks for one business.

    All embeddings are generated before existing records are
    deleted. Database changes are committed together.

    Other businesses' knowledge is never modified.
    """

    contents = [
        document["content"]
        for document in documents
    ]

    embeddings = generate_embeddings(contents)

    if len(embeddings) != len(documents):
        raise RuntimeError(
            "The number of embeddings does not match the documents."
        )

    insert_sql = text(
        """
        INSERT INTO business_knowledge_chunks (
            business_id,
            content,
            embedding,
            source_type,
            source_reference,
            content_hash,
            created_at,
            updated_at
        )
        VALUES (
            :business_id,
            :content,
            CAST(:embedding AS vector),
            :source_type,
            :source_reference,
            :content_hash,
            NOW(),
            NOW()
        )
        """
    )

    try:

        # Remove only this business's old knowledge.
        db.session.execute(
            text(
                """
                DELETE FROM business_knowledge_chunks
                WHERE business_id = :business_id
                """
            ),
            {
                "business_id": business_id,
            },
        )

        rows = []

        for document, embedding in zip(
            documents,
            embeddings,
        ):

            rows.append(
                {
                    "business_id": business_id,
                    "content": document["content"],
                    "embedding": serialize_embedding(
                        embedding
                    ),
                    "source_type": document["source_type"],
                    "source_reference": document[
                        "source_reference"
                    ],
                    "content_hash": document["content_hash"],
                }
            )

        if rows:

            db.session.execute(
                insert_sql,
                rows,
            )

        db.session.commit()

        logger.info(
            "Business knowledge indexed. "
            "business_id=%s chunks=%s",
            business_id,
            len(rows),
        )

        return {
            "success": True,
            "business_id": business_id,
            "chunks_indexed": len(rows),
        }

    except Exception:

        db.session.rollback()

        logger.exception(
            "Business knowledge save failed. "
            "business_id=%s",
            business_id,
        )

        raise


# ============================================================
# MAIN INDEXING FUNCTION
# ============================================================

def index_business_knowledge(advert):
    """
    Collect, embed and save knowledge for one restaurant.

    The caller must first verify that the restaurant profile
    is publicly available.
    """

    if not advert:
        raise ValueError(
            "A restaurant advert is required."
        )

    documents = collect_business_knowledge(
        advert
    )

    return save_business_knowledge(
        business_id=advert.id,
        documents=documents,
    )
