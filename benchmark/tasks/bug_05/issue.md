# Newly uploaded documents do not appear in search until the page is reloaded

Someone uploads a file, searches for a word that is definitely in it, and gets
nothing back. A hard refresh makes it appear. From the console:

```python
index = SearchIndex()
index.add("notes", "quarterly revenue")
index.search("revenue")          # ['notes']
index.add("deck", "revenue plan")
index.search("revenue")          # ['notes']      <- 'deck' is missing
```

Deleting a document takes effect immediately, so only the add path looks
wrong. Note that search is called several times per render and the scan budget
described in the module docstring is there to keep that render cheap — please
keep it satisfied.
