from ansible.plugins.lookup import LookupBase

def count_duplicate_filenames(str1, str2):
    set1 = set(str1.split(','))
    set2 = set(str2.split(','))

    duplicates = set1 & set2

    return len(duplicates)

class LookupModule(LookupBase):
    def run(self, terms, **kwargs):
        dbis_before_gc = terms[0]
        dbis_after_gc = terms[1]

        stale_dbi_count = count_duplicate_filenames(dbis_before_gc, dbis_after_gc)

        return [stale_dbi_count]
