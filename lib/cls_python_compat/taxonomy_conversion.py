class TaxonomyConverter:

    @staticmethod
    def convert(taxonomy):
        subtypes = {}
        for key, values in taxonomy.items():
            for value in values:
                if value not in subtypes:
                    subtypes[value] = [key]
                else:
                    subtypes[value].append(key)
