class TaxonomyConverter:

    @staticmethod
    def convert(taxonomy,name):
        subtypes = {}
        for key, values in taxonomy.items():
            for value in values:
                if value not in subtypes:
                    subtypes[f"{value}_{name}"] = [f"{key}_{name}"]
                else:
                    subtypes[f"{value}_{name}"].append(f"{key}_{name}")
        return subtypes
