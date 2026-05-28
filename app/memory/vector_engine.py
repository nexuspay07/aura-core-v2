# app/memory/vector_engine.py


def embed_text(text: str):
    """
    Lightweight placeholder embedding.
    Prevents heavy ML model loading in production.
    """

    return [0.0]


def cosine_similarity(vec1, vec2):
    """
    Lightweight placeholder similarity.
    """

    return 0.0