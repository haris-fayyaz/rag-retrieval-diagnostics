from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from app.database.repositories.interface import DocumentRepository
from app.models import AmbiguousPolicyVersionResponse, Chunk, DocumentResponse, DocumentVersionRef


@dataclass
class VersionFilterResult:
    """Result of applying version-aware filtering to a candidate chunk
    set (Task 25). Exactly one of `chunks`/`ambiguity` is meaningful -
    callers check `ambiguity is not None` first and return it as-is
    without ever touching `chunks` (which is [] in that case)."""
    chunks: List[Chunk]
    ambiguity: Optional[AmbiguousPolicyVersionResponse] = None


def apply_version_filter(
    chunks: List[Chunk],
    requested_document_ids: Optional[List[str]],
    repo: DocumentRepository,
) -> VersionFilterResult:
    """
    The single shared version-aware filtering rule (Task 25), called
    from /ask, /answer (both pipelines), and the agent's
    search_documents tool - implemented once here, not duplicated at
    each call site, per mentor guidance.

    - requested_document_ids is the CALLER'S original document_ids
      argument to get_chunks (None = unscoped/search-everything), not
      derived from the chunks themselves - this is what distinguishes
      an explicit historical lookup from a default query.
    - Explicit document_ids: no filtering, no ambiguity check at all.
      Naming specific IDs is the caller's own disambiguation.
    - Unscoped (document_ids is None): superseded documents excluded;
      unversioned (status is None) documents always pass through
      unchanged, for backward compatibility; active documents sharing a
      policy_name must resolve to one current version by effective_date
      or the whole call refuses with ambiguous_policy_version - see
      docs/version-aware-retrieval.md for the exact rule and its
      tradeoffs.
    """
    if not chunks:
        return VersionFilterResult(chunks=[], ambiguity=None)

    if requested_document_ids:
        return VersionFilterResult(chunks=chunks, ambiguity=None)

    distinct_ids = sorted({chunk.document_id for chunk in chunks}, key=int)
    versions = repo.get_document_versions(distinct_ids)
    version_by_id: Dict[str, DocumentResponse] = {v.document_id: v for v in versions}

    eligible_ids, ambiguity = _resolve_default_candidates(version_by_id)
    if ambiguity is not None:
        return VersionFilterResult(chunks=[], ambiguity=ambiguity)

    filtered = [c for c in chunks if c.document_id in eligible_ids]
    return VersionFilterResult(chunks=filtered, ambiguity=None)


def _resolve_default_candidates(
    version_by_id: Dict[str, DocumentResponse],
) -> Tuple[Set[str], Optional[AmbiguousPolicyVersionResponse]]:
    eligible: Set[str] = set()
    groups: Dict[str, List[DocumentResponse]] = {}

    for doc_id, info in version_by_id.items():
        if info.status is None:
            # Unversioned legacy document - never part of this system,
            # always eligible, never grouped.
            eligible.add(doc_id)
            continue
        if info.status != "active":
            continue  # superseded, excluded by default
        if info.policy_name is None:
            # Versioned but not tagged with a policy - nothing to
            # disambiguate against, eligible on its own.
            eligible.add(doc_id)
            continue
        groups.setdefault(info.policy_name, []).append(info)

    for docs in groups.values():
        if len(docs) == 1:
            eligible.add(docs[0].document_id)
            continue

        # 2+ active documents share a policy_name. Resolution rule
        # (documented in docs/version-aware-retrieval.md): effective_date,
        # compared as ISO-8601 strings, is the ONLY tiebreaker. No
        # fallback to comparing version strings - "2026.10" vs "2026.9"
        # sorts wrong lexicographically, and this task does not build
        # semantic-version parsing.
        if all(d.effective_date for d in docs):
            max_date = max(d.effective_date for d in docs)
            winners = [d for d in docs if d.effective_date == max_date]
            if len(winners) == 1:
                eligible.add(winners[0].document_id)
                continue

        return eligible, AmbiguousPolicyVersionResponse(
            message=(
                "Multiple active versions of this policy exist and the "
                "current version cannot be determined."
            ),
            documents=[
                DocumentVersionRef(document_id=d.document_id, version=d.version)
                for d in sorted(docs, key=lambda d: int(d.document_id))
            ],
        )

    return eligible, None