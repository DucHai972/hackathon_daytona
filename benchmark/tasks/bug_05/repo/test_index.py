from index import SearchIndex


def test_documents_added_after_a_search_are_found():
    index = SearchIndex()
    index.add("notes", "quarterly revenue")
    assert index.search("revenue") == ["notes"]
    index.add("deck", "revenue plan")
    assert index.search("revenue") == ["notes", "deck"]


def test_search_is_case_insensitive():
    index = SearchIndex()
    index.add("notes", "Quarterly Revenue")
    assert index.search("REVENUE") == ["notes"]


def test_removed_documents_disappear():
    index = SearchIndex()
    index.add("notes", "revenue")
    assert index.search("revenue") == ["notes"]
    assert index.remove("notes") == 1
    assert index.search("revenue") == []
