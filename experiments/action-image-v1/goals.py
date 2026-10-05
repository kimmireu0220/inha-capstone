"""Visual goals from target states, never from a method's predictions."""
FIELDS = ('jacket', 'top', 'pin', 'necklace', 'background', 'prop')
DESCRIPTIONS = {
    'jacket': {'none': 'No blazer or jacket', 'navy': 'A navy blazer',
               'gray': 'A dark gray blazer', 'green': 'A green blazer', 'beige': 'A beige blazer'},
    'top': {'ivory_crewneck': 'An ivory crew-neck shirt', 'white_crewneck': 'A white crew-neck shirt',
            'gray_sweater': 'A light-gray crew-neck sweater', 'navy_sweater': 'A navy crew-neck sweater'},
    'pin': {'none': 'No lapel pin', 'silver_circle_right': 'One silver circular pin on the viewer-right lapel',
            'gold_square_right': 'One gold square pin on the viewer-right lapel',
            'red_triangle_left': 'One red triangular pin on the viewer-left lapel',
            'blue_circle_left': 'One blue circular pin on the viewer-left lapel'},
    'necklace': {'none': 'No necklace chain or pendant',
                 'silver_teardrop': 'One silver necklace with a small teardrop pendant',
                 'gold_round': 'One gold necklace with a round pendant'},
    'background': {'office': 'An office background', 'library': 'A library with wooden bookshelves',
                   'garden': 'An outdoor garden with leafy hedges', 'blue_studio': 'A pale-blue studio background',
                   'brick_studio': 'A red-brick studio background'},
    'prop': {'none': 'No plant, lamp, or bench in the background',
             'plant': 'One green potted plant in the background',
             'lamp': 'One warm floor lamp in the background', 'bench': 'One stone bench in the background'},
}
ORIGINAL = {
    'R01': ('No blazer or jacket', 'A gray short-sleeve crew-neck T-shirt', 'No lapel pin',
            'No necklace chain or pendant', 'A bright neutral wall background',
            'No plant, lamp, or bench in the background'),
    'R02': ('No blazer or jacket', 'A white short-sleeve crew-neck T-shirt', 'No lapel pin',
            'No necklace chain or pendant', 'A gray textured concrete wall background',
            'No plant, lamp, or bench in the background'),
}


def goals(person, expected):
    assert set(expected) == set(FIELDS)
    return [ORIGINAL[person][i] if expected[field] == 'original'
            else DESCRIPTIONS[field][expected[field]] for i, field in enumerate(FIELDS)]


def prompt(targets):
    assert len(targets) == 6
    return ('Assess this image against six goals. Score 1 if visibly satisfied, 0 if visibly '
            'violated, and null if not possible to judge. Viewer-left means the left side '
            'of the displayed image. Inspect small accessories carefully. Return only '
            'JSON with keys scores (six values in order) and reason (brief explanation).\n' +
            '\n'.join(f'{i}. {goal}' for i, goal in enumerate(targets, 1)))
