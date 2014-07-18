def is_dict_like(obj):
    return hasattr(obj, '__getitem__') and hasattr(obj, '__setitem__')

def is_iterable(obj):
    return hasattr(obj, '__iter__')

def is_optional_dict(obj):
    return not obj or is_dict_like(obj)

def NewUser(name, categories, attributes=None):
    '''
    Create a new user.

    :param name: username
    :param categories: iterable with categories the user belongs to
    :param attributes: optional dictionary of attributes
    :return: dictionary containing the user object fields if successful or None
    '''
    assert name and categories
    assert isinstance(name, str)
    assert is_iterable(categories)
    assert is_optional_dict(attributes)

    user_obj = User(name, categories, attributes)
    result = save_to_database(user_obj)
    assert not result or (is_dict_like(result) and 'name' in result and 'categories' in result and 'attributes' in result)
    return result
