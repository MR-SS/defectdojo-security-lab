"""Model the pinned closure-selection contract without database access."""


def closure_candidates(*, same_test, engagement_scope, product_scope, service, rows):
    """Apply the source-level filters used by DefaultImporter."""
    scope = rows
    if same_test:
        scope = [row for row in scope if row['test'] == 'current']
    elif product_scope:
        scope = [row for row in scope if row['product'] == 'product']
    else:
        scope = [row for row in scope if row['engagement'] == 'engagement']
    if service is None:
        scope = [row for row in scope if row['service'] in (None, '')]
    else:
        scope = [row for row in scope if row['service'] == service]
    return scope


def test_empty_report_is_not_a_source_level_guard():
    rows = [
        {'id': 1, 'test': 'current', 'engagement': 'engagement',
         'product': 'product', 'service': 'burp'},
        {'id': 2, 'test': 'current', 'engagement': 'engagement',
         'product': 'product', 'service': 'burp'},
        {'id': 3, 'test': 'current', 'engagement': 'engagement',
         'product': 'product', 'service': 'burp'},
        {'id': 4, 'test': 'other', 'engagement': 'engagement',
         'product': 'product', 'service': 'burp'},
    ]
    assert closure_candidates(
        same_test=True, engagement_scope=False, product_scope=False, service='burp', rows=rows,
    ) == rows[:3]
    assert closure_candidates(
        same_test=False, engagement_scope=True, product_scope=False, service='burp', rows=rows,
    ) == rows
    assert closure_candidates(
        same_test=False, engagement_scope=False, product_scope=True, service='burp', rows=rows,
    ) == rows


def test_omitted_request_service_excludes_parser_service():
    rows = [{'id': 1, 'test': 'current', 'engagement': 'engagement',
             'product': 'product', 'service': 'burp'}]
    assert closure_candidates(
        same_test=False, engagement_scope=True, product_scope=False, service=None, rows=rows,
    ) == []
