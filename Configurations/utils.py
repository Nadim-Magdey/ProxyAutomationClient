def check_global(variable):
    from Configurations import globals
    return getattr(globals, variable, None) is not None

def fill_global(variable, value):
    from Configurations import globals
    setattr(globals, variable, value)
    return True

def get_global(variable):
    from Configurations import globals
    return getattr(globals, variable, None)
