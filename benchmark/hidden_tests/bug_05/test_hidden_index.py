from index import SearchIndex


def test_added_documents_are_visible_immediately():
    index = SearchIndex()
    index.add("notes", "quarterly revenue")
    assert index.search("revenue") == ["notes"]
    index.add("deck", "revenue plan")
    assert index.search("revenue") == ["notes", "deck"]


def test_repeating_a_query_does_not_rescan():
    index = SearchIndex()
    index.add("notes", "revenue")
    index.search("revenue")
    baseline = index.scans
    for _ in range(20):
        index.search("revenue")
    assert index.scans == baseline, "cached queries must not walk the documents again"


def test_a_render_of_many_repeated_queries_stays_within_budget():
    index = SearchIndex()
    for number in range(10):
        index.add(f"doc{number}", f"body {number}")
    for _ in range(50):
        for term in ("body", "3", "missing"):
            index.search(term)
    assert index.scans <= 3, f"expected at most 3 scans, took {index.scans}"


def test_adding_invalidates_only_what_it_must():
    index = SearchIndex()
    index.add("a", "alpha")
    index.search("alpha")
    index.add("b", "beta")
    scans_before = index.scans
    assert index.search("alpha") == ["a"]
    assert index.scans == scans_before + 1
    assert index.search("alpha") == ["a"]
    assert index.scans == scans_before + 1


def test_removing_invalidates_the_cache():
    index = SearchIndex()
    index.add("a", "alpha")
    assert index.search("alpha") == ["a"]
    index.remove("a")
    assert index.search("alpha") == []


def test_removing_an_absent_document_reports_zero():
    index = SearchIndex()
    index.add("a", "alpha")
    assert index.remove("zzz") == 0
    assert index.search("alpha") == ["a"]


def test_empty_index():
    index = SearchIndex()
    assert index.search("anything") == []


def test_search_is_case_insensitive_both_ways():
    index = SearchIndex()
    index.add("a", "Quarterly REVENUE")
    assert index.search("revenue") == ["a"]
    assert index.search("QUARTERLY") == ["a"]


def test_mutating_the_result_does_not_corrupt_the_index():
    index = SearchIndex()
    index.add("a", "alpha")
    results = index.search("alpha")
    results.append("injected")
    assert index.search("alpha") == ["a"]


def test_indexes_are_independent():
    first = SearchIndex()
    second = SearchIndex()
    first.add("a", "alpha")
    assert second.search("alpha") == []
