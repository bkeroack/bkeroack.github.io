def NewUser(name, categories, attributes):
    user_obj = User(name, categories, attributes)
    return save_to_database(user_obj)