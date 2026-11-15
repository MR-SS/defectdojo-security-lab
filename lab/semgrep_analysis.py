"""Content-free identity statistics for privately held SARIF evidence."""
from collections import Counter


def identity_statistics(before, after):
    """Count collisions without emitting report content or interpreting null as an ID."""
    def stats(rows):
        if any(not row['hash'] for row in rows):
            raise ValueError('missing calculated hash')
        raw = Counter(row['raw'] for row in rows if row['raw'] is not None)
        effective = Counter(row['uid'] for row in rows if row['uid'] is not None)
        hashes = Counter(row['hash'] for row in rows)
        return dict(count=len(rows), raw_distinct=len(raw),
                    raw_collision_rows=sum(n for n in raw.values() if n > 1),
                    effective_nulls=sum(row['uid'] is None for row in rows),
                    effective_collision_rows=sum(n for n in effective.values() if n > 1),
                    hash_distinct=len(hashes),
                    hash_collision_rows=sum(n for n in hashes.values() if n > 1))

    initial, changed = stats(before), stats(after)
    old, new = ({row['hash'] for row in rows} for rows in (before, after))
    return dict(initial=initial, changed=changed, retained_hashes=len(old & new),
                removed_hashes=len(old - new), added_hashes=len(new - old),
                unambiguous_hash_control=bool(before and after) and not (
                    initial['hash_collision_rows'] or changed['hash_collision_rows']))
