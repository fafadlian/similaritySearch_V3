import joblib
import numpy as np
import pandas as pd
import faiss


def faiss_search_with_metadata(
    embedding: np.ndarray,
    index: faiss.Index,
    db_ids: np.ndarray,
    metadata: pd.DataFrame,
    top_k: int = 5,
    include_distance: bool = True,
    include_confidence: bool = True
) -> pd.DataFrame:
    """
    Perform FAISS search and return passenger metadata with additional metrics.

    Args:
        embedding (np.ndarray): (1, dim) embedding of query
        index (faiss.Index): FAISS index
        db_ids (np.ndarray): array of 'travel_doc' values aligned with index
        metadata (pd.DataFrame): full metadata used to build the index
        top_k (int): number of nearest neighbors
        include_distance (bool): add 'faiss_distance'
        include_confidence (bool): add 'confidence_score'

    Returns:
        pd.DataFrame: matched passengers + optional scores
    """
    assert embedding.shape[1] == index.d, f"Embedding dim {embedding.shape[1]} does not match FAISS index dim {index.d}"
    D, I = index.search(embedding, top_k)
    top_ids = db_ids[I[0]]

    # Build mapping for rank
    id_rank = {doc_id: rank for rank, doc_id in enumerate(top_ids)}
    matched = metadata[metadata["travel_doc"].isin(top_ids)].copy()
    matched["rank"] = matched["travel_doc"].map(id_rank)

    # Attach FAISS distance and confidence
    if include_distance:
        matched["faiss_distance"] = matched["travel_doc"].map(
            lambda doc: D[0][id_rank[doc]]
        )

    if include_confidence:
        matched["confidence_score"] = matched["faiss_distance"].map(
            lambda d: round(1 / (1 + d), 6)
        ) if "faiss_distance" in matched.columns else np.nan

    matched.sort_values("rank", inplace=True)
    matched.drop(columns=["rank"], inplace=True)

    return matched
