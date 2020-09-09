def semester(sem):
    assert len(sem) >= 4

    rank = int(1e6) 
    semesters = { 
        "fa": 2, 
        "sp": 1, 
        "su": 0, 
    } 
    name, year = sem[0:2], int(sem[2:4]) 
    return rank - (len(semesters) * year + semesters[name])


def roles(role):
    """Takes in two: `<sem>-<group>-<role>`. Returns ordering by `<sem>` and `<role>`.
    """
    from ..components import website
    officers = website.load_config("officers")
    officers = [x.lower().replace(" ", "-") for x in officers]

    rank = semester(role)
    rank *= len(officers)
    for idx, officer in enumerate(officers[::-1]):
        if role.endswith(officer):
            rank -= (len(officers) - idx)
            break

    return rank