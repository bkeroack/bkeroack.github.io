def NewUser(name, categories, attributes=None):
    '''
    Create a new user.

    :param name: username
    :param categories: iterable with categories the user belongs to
    :param attributes: optional dictionary of attributes
    :return: boolean indicating database write success
    '''
    assert name and categories
    assert isinstance(name, str)
    assert hasattr(categories, '__iter__')
    assert not attributes or (hasattr(attributes, '__getitem__') and hasattr(attributes, '__setitem__'))

    user_obj = User(name, categories, attributes)
    return save_to_database(user_obj)