import itertools

def generate_load_combinations(load_groups, load_factors):
    #TODO: Implement this function
    
    return combinations




if __name__ == '__main__':
    
    load_groups = {
        'Dead': {
            'Perm': ['DL', 'SDL']
        },
        'Live': {
            'Perm': ['LL'],
            'Construction': ['LL_Construction'],
            'Pattern': ['LL_Pattern']
        }
    }

    load_factors = {
        'LRFD1': {
            'Dead': 1.4
        },
        'LRFD2': {
            'Live': {
                'Perm': 1.6,
                'Construction': 1.0,
                'Pattern': 1.6
            }
        }
    }

    load_combinations = generate_load_combinations(load_groups, load_factors)
    for combination, factor in load_combinations:
        print(combination, factor)